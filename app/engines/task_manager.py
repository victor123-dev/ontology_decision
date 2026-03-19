import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models.drive_logic import Task, TaskInstance
from app.models.agent import Agent
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.utils.logger import get_logger

import traceback

logger = get_logger(__name__)


class TaskManager:
    """任务管理器 - 负责任务的调度、执行和状态管理"""
    
    def __init__(self):
        self.is_running = False
        self.threads = []
        self.stats = {
            'tasks_created': 0,
            'tasks_assigned': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'errors': 0
        }
        
        # 任务调度日志计时器
        self.last_schedule_log = time.time()
    
    def start(self):
        """启动任务管理器"""
        self.is_running = True
        
        # 启动任务调度线程
        schedule_thread = threading.Thread(target=self._schedule_tasks)
        schedule_thread.daemon = True
        schedule_thread.start()
        self.threads.append(schedule_thread)
        
        logger.info("任务管理器启动")
    
    def stop(self):
        """停止任务管理器"""
        self.is_running = False
        for thread in self.threads:
            thread.join()
        logger.info("任务管理器停止")
        self._print_stats()
    
    def _print_stats(self):
        """打印统计信息"""
        logger.info("=" * 60)
        logger.info("任务管理器统计信息")
        logger.info("=" * 60)
        logger.info(f"创建任务数: {self.stats['tasks_created']}")
        logger.info(f"分配任务数: {self.stats['tasks_assigned']}")
        logger.info(f"完成任务数: {self.stats['tasks_completed']}")
        logger.info(f"失败任务数: {self.stats['tasks_failed']}")
        logger.info(f"错误数: {self.stats['errors']}")
        logger.info("=" * 60)
    
    def _get_db_session(self):
        """获取数据库会话"""
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def _log(self, level: str, category: str, message: str, data: Dict[str, Any] = None, trace_id: str = None):
        """记录任务日志"""
        try:
            import uuid
            db = self._get_db_session()
            try:
                from app.models.drive_log import DriveLog
                log = DriveLog(
                    level=level,
                    category=category,
                    message=message,
                    data=data,
                    trace_id=trace_id or str(uuid.uuid4())
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"记录任务日志失败: {str(e)}")
    
    def assign_and_wait_for_task(self, task: Task, event: Dict[str, Any], trace_id: str = None, timeout: int = 300) -> Dict[str, Any]:
        """
        下发任务并等待完成
        
        Args:
            task: 要执行的任务
            event: 任务事件数据
            trace_id: 追踪ID
            timeout: 超时时间（秒），默认300秒（5分钟）
            
        Returns:
            任务执行结果字典
        """
        try:
            # 1. 创建任务实例
            db = self._get_db_session()
            try:
                task_instance = TaskInstance(
                    task_id=task.id,
                    assigned_agent_id=None,
                    status='pending',
                    result={
                        'event': event,
                        'created_at': datetime.now().isoformat(),
                        'trace_id': trace_id
                    }
                )
                db.add(task_instance)
                db.commit()
                task_instance_id = task_instance.id
                self.stats['tasks_created'] += 1
            finally:
                db.close()
            
            logger.info(f"已创建同步任务实例 {task_instance_id}，等待执行完成...")
            self._log('info', 'sync_task_create', f"同步任务创建: {task.name}", 
                     {'task_name': task.name, 'task_instance_id': task_instance_id}, trace_id)
            
            # 2. 等待任务完成
            start_time = time.time()
            while time.time() - start_time < timeout:
                db = self._get_db_session()
                try:
                    updated_task = db.query(TaskInstance).filter(TaskInstance.id == task_instance_id).first()
                    
                    if updated_task and updated_task.status in ['completed', 'failed']:
                        execution_result = updated_task.result.get('execution_result', {})
                        
                        # 记录任务完成日志
                        status_text = '成功' if updated_task.status == 'completed' else '失败'
                        self._log('info', 'sync_task_complete', f"同步任务完成: {task.name} - {status_text}", 
                                 {'task_name': task.name, 'task_instance_id': task_instance_id, 'status': updated_task.status}, trace_id)
                        
                        if updated_task.status == 'completed':
                            self.stats['tasks_completed'] += 1
                        else:
                            self.stats['tasks_failed'] += 1
                        
                        return {
                            'success': updated_task.status == 'completed',
                            'result': execution_result,
                            'status': updated_task.status,
                            'task_instance_id': task_instance_id
                        }
                finally:
                    db.close()
                
                # 每秒检查一次
                time.sleep(1)
            
            # 超时处理
            logger.warning(f"任务 {task_instance_id} 执行超时 ({timeout}秒)")
            self._log('warning', 'sync_task_timeout', f"同步任务超时: {task.name}", 
                     {'task_name': task.name, 'task_instance_id': task_instance_id, 'timeout_seconds': timeout}, trace_id)
            return {
                'success': False,
                'error': f'Task timeout after {timeout} seconds',
                'status': 'timeout',
                'task_instance_id': task_instance_id
            }
            
        except Exception as e:
            logger.error(f"同步任务执行失败: {str(e)}")
            logger.error(traceback.format_exc())
            self._log('error', 'sync_task_error', f"同步任务执行失败: {task.name}", 
                     {'task_name': task.name, 'error': str(e)}, trace_id)
            self.stats['errors'] += 1
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }
    
    def _schedule_tasks(self):
        """任务调度循环 - 定期检查待处理任务并分配给合适的Agent（支持任务组调度）"""
        while self.is_running:
            try:
                db = self._get_db_session()
                try:
                    # 查询所有 pending 状态的任务实例
                    pending_tasks = db.query(TaskInstance).filter(TaskInstance.status == 'pending').all()
                    
                    if not pending_tasks:
                        time.sleep(5)
                        continue
                        
                    # 获取所有可用的Agent及其能力
                    agents = db.query(Agent).filter(Agent.status == 'active').all()
                    
                    # 按 group_id 分组任务实例
                    task_groups = self._group_tasks_by_group_id(pending_tasks)
                    
                    # 每3分钟记录一次调度日志
                    current_time = time.time()
                    if current_time - self.last_schedule_log >= 180:  # 180秒 = 3分钟
                        self._log('info', 'task_scheduling', f"任务调度引擎检查到 {len(pending_tasks)} 个待处理任务，{len(task_groups)} 个任务组", 
                                 {'pending_task_count': len(pending_tasks), 'task_group_count': len(task_groups)})
                        self.last_schedule_log = current_time
                    
                    # 调度每个任务组
                    for group_id, group_tasks in task_groups.items():
                        self._schedule_task_group(group_id, group_tasks, agents, db)
                            
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"任务调度失败: {str(e)}")
                logger.error(traceback.format_exc())
                self.stats['errors'] += 1
            
            # 每5秒检查一次
            time.sleep(5)
    
    def _group_tasks_by_group_id(self, pending_tasks):
        """按 group_id 对任务实例进行分组"""
        groups = {}
        for task_instance in pending_tasks:
            is_group_task = task_instance.result.get('is_group_task', False)
            if is_group_task:
                group_id = task_instance.result.get('group_id')
                if group_id not in groups:
                    groups[group_id] = []
                groups[group_id].append(task_instance)
            else:
                # 单个任务使用自己的ID作为组ID
                groups[f"single_{task_instance.id}"] = [task_instance]
        return groups



    def _schedule_task_group(self, group_id, group_tasks, agents, db):
        """调度任务组 - 支持多Agent"""
        # 收集任务组的所有任务和能力需求
        tasks = []
        task_capability_map = {}  # 任务ID -> 能力ID列表
        
        for task_instance in group_tasks:
            task = task_instance.task
            tasks.append(task)
            task_capability_map[task.id] = [cap.id for cap in task.capabilities]
        
        # 找到能够覆盖所有任务能力需求的Agent组合
        agent_assignment = self._find_optimal_agent_assignment(
            tasks, task_capability_map, agents
        )
        
        if agent_assignment:
            # 更新所有任务实例为 assigned 状态
            first_task_instance = group_tasks[0]
            event = first_task_instance.result.get('event', {})
            trace_id = first_task_instance.result.get('trace_id')
            
            # 为每个任务实例分配对应的Agent
            task_instance_map = {ti.task.id: ti for ti in group_tasks}
            assigned_agents = []
            
            for task_id, assigned_agent in agent_assignment.items():
                task_instance = task_instance_map[task_id]
                task_instance.assigned_agent_id = assigned_agent.id
                task_instance.status = 'assigned'
                task_instance.started_at = datetime.now()
                assigned_agents.append(assigned_agent)
            
            db.commit()
            self.stats['tasks_assigned'] += len(group_tasks)
            
            # 获取去重的Agent列表
            unique_agents = list({agent.id: agent for agent in assigned_agents}.values())
            agent_names = [agent.name for agent in unique_agents]
            logger.info(f"任务组 (ID: {group_id}) 已分配给 Agents: {agent_names}")
            
            # 在后台线程中执行整个任务组（传入多个Agent）
            execution_thread = threading.Thread(
                target=self._execute_task_group_in_background,
                args=(unique_agents, tasks, group_tasks, event, trace_id, group_id)
            )
            execution_thread.daemon = True
            execution_thread.start()
        else:
            logger.warning(f"没有找到支持任务组 (ID: {group_id}) 的Agent组合")

    def _find_optimal_agent_assignment(self, tasks: List[Task], 
                                     task_capability_map: Dict[int, List[int]], 
                                     available_agents: List[Agent]) -> Optional[Dict[int, Agent]]:
        """
        找到最优的Agent分配方案
        
        Args:
            tasks: 任务列表
            task_capability_map: 任务ID到能力ID列表的映射
            available_agents: 可用Agent列表
            
        Returns:
            任务ID到Agent的分配映射，如果无法分配则返回None
        """
        # 构建Agent能力映射
        agent_capability_map = {}
        for agent in available_agents:
            agent_capability_map[agent.id] = set([cap.id for cap in agent.capabilities])
        
        # 尝试为每个任务分配Agent
        assignment = {}
        unassigned_tasks = []
        
        for task in tasks:
            task_id = task.id
            required_capabilities = set(task_capability_map[task_id])
            
            # 找到能够满足该任务所有能力需求的Agent
            suitable_agents = []
            for agent in available_agents:
                agent_capabilities = agent_capability_map[agent.id]
                if required_capabilities.issubset(agent_capabilities):
                    suitable_agents.append(agent)
            
            if suitable_agents:
                # 选择第一个合适的Agent（可以优化为负载均衡等策略）
                assignment[task_id] = suitable_agents[0]
            else:
                unassigned_tasks.append(task)
        
        # 如果有任务无法分配，则整个任务组无法执行
        if unassigned_tasks:
            logger.warning(f"无法为以下任务找到合适的Agent: {[t.name for t in unassigned_tasks]}")
            return None
        
        return assignment

    def _execute_task_group_in_background(self, agents: List[Agent], tasks: List[Task], 
                                        task_instances: List[TaskInstance], 
                                        event: Dict[str, Any], trace_id: str, group_id: str):
        """在后台线程中执行任务组 - 支持多Agent"""
        try:
            db = self._get_db_session()
            try:
                # 检查任务实例状态
                for task_instance in task_instances:
                    if task_instance.status != 'assigned':
                        logger.warning(f"任务组 {group_id} 状态已改变，跳过执行")
                        return
            
                # 构建任务到Agent的映射
                task_instance_map = {ti.task.id: ti for ti in task_instances}
                task_agent_map = {}
                for agent in agents:
                    # 找到分配给这个Agent的任务
                    for task_instance in task_instances:
                        if task_instance.assigned_agent_id == agent.id:
                            if agent.id not in task_agent_map:
                                task_agent_map[agent.id] = []
                            task_agent_map[agent.id].append(task_instance.task)
            
                # 准备任务组事件数据
                group_event = {
                    **event,
                    'is_group_task': True,
                    'group_id': group_id,
                    'group_size': len(tasks),
                    'group_tasks': [{'name': t.name, 'id': t.id} for t in tasks],
                    'task_instances': [{'id': ti.id, 'index': i, 'assigned_agent_id': ti.assigned_agent_id} 
                                     for i, ti in enumerate(task_instances)],
                    'agent_assignments': {str(agent.id): agent.name for agent in agents}
                }
                
                # 执行任务组（传入多个Agent）
                from app.engines.agent_executor import agent_executor
                execution_result = agent_executor.execute_agent_task_group(
                    agents, tasks, group_event, trace_id
                )
                
                # 更新所有任务实例状态和结果
                success = execution_result.get('success', True)
                for i, task_instance in enumerate(task_instances):
                    task_instance.status = 'completed' if success else 'failed'
                    task_instance.result = {
                        **task_instance.result,
                        'execution_result': execution_result.get('results', [{}]*len(task_instances))[i] 
                                            if 'results' in execution_result 
                                            else execution_result,
                        'completed_at': datetime.now().isoformat()
                    }
                    task_instance.completed_at = datetime.now()
                
                db.commit()
                
                if success:
                    self.stats['tasks_completed'] += len(task_instances)
                else:
                    self.stats['tasks_failed'] += len(task_instances)
                
                status_text = '成功' if success else '失败'
                agent_names = [agent.name for agent in agents]
                logger.info(f"Agents '{agent_names}' 执行任务组 '{group_id}' {status_text}")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"后台任务组执行失败: {str(e)}")
            logger.error(traceback.format_exc())
            self.stats['errors'] += 1


# 全局任务管理器实例
task_manager = TaskManager()