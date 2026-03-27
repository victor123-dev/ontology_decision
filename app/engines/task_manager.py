import threading
import time
from typing import Dict, Any
from datetime import datetime
from app.models.drive_logic import Task, TaskInstance
from app.models.agent import Agent
from app.utils.logger import get_logger
from .agent_assigner import AgentAssigner
from app.utils.shared_utils import get_db_session, log_event_with_parent

import traceback

logger = get_logger(__name__)


class TaskManager:
    """任务管理器 - 负责任务的调度、执行和状态管理"""
    
    def __init__(self):
        self.is_running = False
        self.threads = []
        self.agent_assigner = AgentAssigner()
        self.stats = {
            'tasks_created': 0,
            'tasks_assigned': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'errors': 0
        }
    
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
    

    
    def assign_and_wait_for_task(self, task: Task, event: Dict[str, Any], source_name: str, trace_id: str = None, parent_id: str = None, timeout: int = 300) -> Dict[str, Any]:
        """
        下发任务并等待完成
        
        Args:
            task: 要执行的任务
            event: 任务事件数据
            source_name: 任务来源名称
            trace_id: 追踪ID
            parent_id: 父日志ID
            timeout: 超时时间（秒），默认300秒（5分钟）
            
        Returns:
            任务执行结果字典
        """
        try:
            # 1. 创建任务实例
            db = get_db_session()
            try:
                task_instance = TaskInstance(
                    task_id=task.id,
                    assigned_agent_id=None,
                    status='pending',
                    result={
                        'event': event,
                        'created_at': datetime.now().isoformat(),
                        'trace_id': trace_id,
                        'is_group_task': False
                    }
                )
                db.add(task_instance)
                db.commit()
                task_instance_id = task_instance.id
                self.stats['tasks_created'] += 1
            finally:
                db.close()
            
            logger.info(f"已创建任务实例 {task_instance_id}，等待执行完成...")
            log_id = log_event_with_parent('info', 'agent_task', f"来自{source_name}创建任务: {task.name}已创建，等待调度", 
                     {'task_name': task.name, 'source_name': source_name, 'task_instance_id': task_instance_id}, trace_id, parent_id)
            # 更新 TaskInstance 的 result 字段，添加 log_id
            if log_id:
                task_instance.result['creation_log_id'] = log_id
                db.commit()

            # 2. 等待任务完成
            start_time = time.time()
            while time.time() - start_time < timeout:
                db = get_db_session()
                try:
                    updated_task = db.query(TaskInstance).filter(TaskInstance.id == task_instance_id).first()
                    
                    if updated_task and updated_task.status in ['completed', 'failed']:
                        execution_result = updated_task.result.get('execution_result', {})
                        
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
            return {
                'success': False,
                'error': f'Task timeout after {timeout} seconds',
                'status': 'timeout',
                'task_instance_id': task_instance_id
            }
            
        except Exception as e:
            logger.error(f"同步任务执行失败: {str(e)}")
            logger.error(traceback.format_exc())
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
                db = get_db_session()
                try:
                    # 查询所有 pending 状态的任务实例
                    pending_tasks = db.query(TaskInstance).filter(TaskInstance.status == 'pending').all()
                    
                    if not pending_tasks:
                        time.sleep(5)
                        continue
                        
                    # 获取所有可用的Agent及其能力
                    agents = db.query(Agent).filter(Agent.status == 'active').all()
                    
                    # 按 group_id 分组任务实例
                    task_groups = self.agent_assigner.group_tasks_by_group_id(pending_tasks)
                    
                    # 调度每个任务组
                    for group_id, group_tasks in task_groups.items():
                        self.agent_assigner.schedule_task_group(group_id, group_tasks, agents, db)
                            
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"任务调度失败: {str(e)}")
                logger.error(traceback.format_exc())
                self.stats['errors'] += 1
            
            # 每5秒检查一次
            time.sleep(5)
    

# 全局任务管理器实例
task_manager = TaskManager()