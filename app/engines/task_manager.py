import threading
import time
from typing import Dict, Any, List
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
        """任务调度循环 - 定期检查待处理任务并分配给合适的Agent"""
        while self.is_running:
            try:
                db = self._get_db_session()
                try:
                    # 查询所有 pending 状态的任务实例
                    pending_tasks = db.query(TaskInstance).filter(TaskInstance.status == 'pending').all()
                    
                    if pending_tasks:
                        # 获取所有可用的Agent及其能力
                        agents = db.query(Agent).filter(Agent.status == 'active').all()
                        
                        # 每3分钟记录一次调度日志
                        current_time = time.time()
                        if current_time - self.last_schedule_log >= 180:  # 180秒 = 3分钟
                            self._log('info', 'task_scheduling', f"任务调度引擎检查到 {len(pending_tasks)} 个待处理任务", 
                                     {'pending_task_count': len(pending_tasks)})
                            self.last_schedule_log = current_time
                        
                        for task_instance in pending_tasks:
                            task = task_instance.task
                            matched_agent = None
                            
                            # 根据任务的多个能力ID匹配Agent
                            task_capability_ids = [cap.id for cap in task.capabilities]
                            for agent in agents:
                                agent_capability_ids = [cap.id for cap in agent.capabilities]
                                # 检查Agent是否支持任务的所有能力
                                if all(cap_id in agent_capability_ids for cap_id in task_capability_ids):
                                    matched_agent = agent
                                    break
                            
                            if matched_agent:
                                # 从任务实例中获取事件数据和trace_id
                                event = task_instance.result.get('event', {})
                                trace_id = task_instance.result.get('trace_id')
                                
                                # 更新任务实例为 assigned 状态
                                task_instance.assigned_agent_id = matched_agent.id
                                task_instance.status = 'assigned'
                                task_instance.started_at = datetime.now()
                                db.commit()
                                self.stats['tasks_assigned'] += 1
                                
                                logger.info(f"任务 '{task.name}' 已分配给 Agent: {matched_agent.name}")
                                self._log('info', 'agent_task', f"任务 '{task.name}' 已分配给 Agent: {matched_agent.name}", 
                                         {'task_name': task.name, 'agent_name': matched_agent.name}, trace_id)
                                
                                # 在新线程中执行任务，避免阻塞调度循环
                                execution_thread = threading.Thread(
                                    target=self._execute_task_in_background,
                                    args=(matched_agent, task, task_instance.id, event, trace_id)
                                )
                                execution_thread.daemon = True
                                execution_thread.start()
                            else:
                                logger.warning(f"没有找到支持能力ID {task_capability_ids} 的Agent，任务 '{task.name}' 继续等待")
                                
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"任务调度失败: {str(e)}")
                logger.error(traceback.format_exc())
                self.stats['errors'] += 1
            
            # 每5秒检查一次
            time.sleep(5)
    
    def _execute_task_in_background(self, agent: Agent, task: Task, task_instance_id: int, event: Dict[str, Any], trace_id: str):
        """在后台线程中执行任务"""
        try:
            # 创建新的数据库会话用于更新任务状态
            db = self._get_db_session()
            try:
                # 获取任务实例
                task_instance = db.query(TaskInstance).filter(TaskInstance.id == task_instance_id).first()
                if not task_instance or task_instance.status != 'assigned':
                    logger.warning(f"任务 {task_instance_id} 状态已改变，跳过执行")
                    return
                
                # 执行Agent任务
                from app.engines.agent_executor import agent_executor
                execution_result = agent_executor.execute_agent_task(agent, task, event, trace_id)
                
                # 更新任务实例状态和结果
                task_instance.status = 'completed' if execution_result.get('success', True) else 'failed'
                task_instance.result = {
                    **task_instance.result,
                    'execution_result': execution_result,
                    'completed_at': datetime.now().isoformat()
                }
                task_instance.completed_at = datetime.now()
                db.commit()
                
                if execution_result.get('success', True):
                    self.stats['tasks_completed'] += 1
                else:
                    self.stats['tasks_failed'] += 1
                
                status_text = '成功' if execution_result.get('success', True) else '失败'
                logger.info(f"Agent '{agent.name}' 执行任务 '{task.name}' {status_text}")
                self._log('info', 'agent_execution', f"Agent '{agent.name}' 执行任务 '{task.name}' {status_text}", 
                         {'agent_name': agent.name, 'task_name': task.name, 'status': task_instance.status}, trace_id)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"后台任务执行失败: {str(e)}")
            logger.error(traceback.format_exc())
            self.stats['errors'] += 1
            # 更新任务实例为失败状态
            try:
                db = self._get_db_session()
                task_instance = db.query(TaskInstance).filter(TaskInstance.id == task_instance_id).first()
                if task_instance:
                    task_instance.status = 'failed'
                    task_instance.result = {
                        **task_instance.result,
                        'error': str(e),
                        'completed_at': datetime.now().isoformat()
                    }
                    task_instance.completed_at = datetime.now()
                    db.commit()
            except:
                pass
            finally:
                db.close()


# 全局任务管理器实例
task_manager = TaskManager()