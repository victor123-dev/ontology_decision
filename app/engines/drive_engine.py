import threading
import time
from typing import Dict, Any, List
from datetime import datetime
from app.models.drive_logic import DriveLogic, Task, TaskInstance
from app.models.drive_log import DriveLog
from app.models.agent import Agent
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.utils.logger import get_logger
from app.utils.data_source_accessor import DataSourceAccessor
from app.utils.function_registry import prepare_function_environment, extract_function_names
from app.engines.agent_executor import agent_executor
from app.engines.task_manager import task_manager
import traceback

logger = get_logger(__name__)


class DriveEngine:
    """数据驱动引擎 - 完整实现"""
    
    def __init__(self):
        self.is_running = False
        self.threads = []
        self.event_queue = []
        self.event_lock = threading.Lock()
        
        self.stats = {
            'events_received': 0,
            'logics_matched': 0,
            'tasks_created': 0,
            'errors': 0
        }
    
    def start(self):
        """启动驱动引擎"""
        self.is_running = True
        
        process_thread = threading.Thread(target=self._process_events)
        process_thread.daemon = True
        process_thread.start()
        self.threads.append(process_thread)
        
        logger.info("数据驱动引擎启动")
    
    def stop(self):
        """停止驱动引擎"""
        self.is_running = False
        for thread in self.threads:
            thread.join()
        logger.info("数据驱动引擎停止")
        self._print_stats()
    
    def _print_stats(self):
        """打印统计信息"""
        logger.info("=" * 60)
        logger.info("数据驱动引擎统计信息")
        logger.info("=" * 60)
        logger.info(f"接收事件数: {self.stats['events_received']}")
        logger.info(f"匹配逻辑数: {self.stats['logics_matched']}")
        logger.info(f"创建任务数: {self.stats['tasks_created']}")
        logger.info(f"错误数: {self.stats['errors']}")
        logger.info("=" * 60)

    def _log(self, level: str, category: str, message: str, data: Dict[str, Any] = None, trace_id: str = None):
        """记录驱动日志"""
        try:
            import uuid
            db = self._get_db_session()
            try:
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
            logger.error(f"记录驱动日志失败: {str(e)}")
    
    def _get_db_session(self):
        """获取数据库会话"""
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def handle_event(self, event: Dict[str, Any]):
        """处理事件"""
        self.stats['events_received'] += 1
        
        with self.event_lock:
            self.event_queue.append(event)
        
        trace_id = event.get('trace_id')
        logger.info(f"接收事件: {event['type']}, 模型: {event.get('model_id')}")
        self._log('info', 'drive_logic', f"接收事件: {event['type']}", event, trace_id)
    
    def _process_events(self):
        """处理事件队列"""
        while self.is_running:
            if self.event_queue:
                with self.event_lock:
                    event = self.event_queue.pop(0)
                self._process_event(event)
            time.sleep(0.1)
    
    def _process_event(self, event: Dict[str, Any]):
        """处理单个事件"""
        try:
            event_type = event.get('type')
            event_data = event.get('data', {})
            config_id = event_data.get('config_id')
            
            db = self._get_db_session()
            try:
                logics = db.query(DriveLogic).all()
                
                matched_logics = []
                for logic in logics:
                    event_ids = [e.id for e in logic.events]
                    if config_id in event_ids:
                        matched_logics.append(logic)
                
                if not matched_logics:
                    for logic in logics:
                        if not logic.events:
                            matched_logics.append(logic)
                
                trace_id = event.get('trace_id')
                logger.info(f"事件 {event['type']} 匹配到 {len(matched_logics)} 条驱动逻辑")
                self.stats['logics_matched'] += len(matched_logics)
                self._log('info', 'drive_logic', f"事件 {event['type']} 匹配到 {len(matched_logics)} 条驱动逻辑", {'event_type': event['type'], 'matched_count': len(matched_logics)}, trace_id)
                
                for logic in matched_logics:
                    self._execute_logic(logic, event, db, trace_id)
                    
            finally:
                db.close()
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"处理事件出错: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _execute_logic(self, logic: DriveLogic, event: Dict[str, Any], db, trace_id: str = None):
        """执行驱动逻辑"""
        try:
            config = logic.config or {}
            logic_type = logic.type
            
            logger.info(f"执行驱动逻辑: {logic.name} (类型: {logic_type})")
            self._log('info', 'drive_logic', f"执行驱动逻辑: {logic.name}", {'logic_name': logic.name, 'logic_type': logic_type}, trace_id)
            
            # 预处理
            # TODO DEMO这里只处理了第一个受影响的记录，一阶函数遇到批量数组应如何处理？循环？需思考
            processed_data = event.get('data', {}).get('affected_records', {})[0].get('record', {})
            trigger_tasks = False
            
            if logic_type == 'script' and config.get('script_content'):
                result = self._run_preprocess_script(config.get('script_content'), event)
                # 检查脚本返回值
                if isinstance(result, tuple) and len(result) == 2:
                    # 脚本返回 (bool, dict) 形式
                    trigger_tasks = result[0]
                    processed_data = result[1]
            elif logic_type == 'first_order' and config.get('pre_condition'):
                # 处理一阶函数的前置条件 - 支持函数调用
                pre_condition = config.get('pre_condition')
                try:
                    logger.debug(f"评估 First Order 条件: {pre_condition}")

                    # 从表达式提取函数名并准备执行环境
                    local_vars = prepare_function_environment(pre_condition, processed_data, event)

                    # 记录提取到的函数
                    func_names = extract_function_names(pre_condition)
                    if func_names:
                        logger.info(f"First Order 表达式使用函数: {func_names}")

                    # 安全的全局环境
                    safe_globals = {'__builtins__': {}}

                    # 评估前置条件
                    trigger_tasks = eval(pre_condition, safe_globals, local_vars)

                    logger.info(f"First Order 条件评估结果: {trigger_tasks}")

                except Exception as e:
                    logger.error(f"评估前置条件失败: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 只有当条件满足时才触发任务
            if trigger_tasks:
                # 关联的任务
                tasks = logic.tasks
                if tasks:
                    # 更新事件数据为处理后的数据
                    event['data'] = processed_data
                    self._assign_tasks(tasks, event, db, trace_id)
                    self._log('info', 'drive_logic', f"驱动逻辑 {logic.name} 触发 {len(tasks)} 个任务", {'logic_name': logic.name, 'task_count': len(tasks)}, trace_id)
                else:
                    logger.warning(f"驱动逻辑 {logic.name} 没有关联任务")
                    self._log('warning', 'drive_logic', f"驱动逻辑 {logic.name} 没有关联任务", {'logic_name': logic.name}, trace_id)
            else:
                logger.info(f"驱动逻辑 {logic.name} 条件不满足，跳过任务触发")
                self._log('info', 'drive_logic', f"驱动逻辑 {logic.name} 条件不满足，跳过任务触发", {'logic_name': logic.name}, trace_id)
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"执行驱动逻辑失败: {logic.name}, 错误: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _run_preprocess_script(self, script_content: str, event: Dict[str, Any]):
        """运行预处理脚本"""
        try:
            safe_globals = {
                '__builtins__': {
                    'print': print, 'str': str, 'int': int, 'float': float,
                    'bool': bool, 'list': list, 'dict': dict, 'len': len,
                    'range': range, 'enumerate': enumerate, 'zip': zip,
                    'map': map, 'filter': filter, 'sorted': sorted,
                    'min': min, 'max': max, 'sum': sum, 'abs': abs, 'round': round,
                    'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
                }
            }
            
            local_vars = {
                'event': event.copy(),
                'data_source': DataSourceAccessor()
            }
            exec(script_content, safe_globals, local_vars)
            
            return local_vars.get('result', event.get('data', {}))
        except Exception as e:
            logger.error(f"预处理脚本执行失败: {str(e)}")
            return event.get('data', {})
    
    def _assign_tasks(self, tasks: List[Task], event: Dict[str, Any], db, trace_id: str = None):
        """分配任务给Agent - 只创建任务实例，不立即执行"""
        try:
            for task in tasks:
                # 创建任务实例，初始状态为 pending
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

                logger.info(f"任务 '{task.name}' 已创建，等待调度")
                self.stats['tasks_created'] += 1
                self._log('info', 'agent_task', f"任务 '{task.name}' 已创建，等待调度", {'task_name': task.name}, trace_id)
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"创建任务实例失败: {str(e)}")
            logger.error(traceback.format_exc())

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
                
                status_text = '成功' if execution_result.get('success', True) else '失败'
                logger.info(f"Agent '{agent.name}' 执行任务 '{task.name}' {status_text}")
                self._log('info', 'agent_execution', f"Agent '{agent.name}' 执行任务 '{task.name}' {status_text}", 
                         {'agent_name': agent.name, 'task_name': task.name, 'status': task_instance.status}, trace_id)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"后台任务执行失败: {str(e)}")
            logger.error(traceback.format_exc())
            # 更新任务实例为失败状态
            try:
                db = self._get_db_session()
                task_instance = db.query(TaskInstance).filter(TaskInstance.id == task_instance.id).first()
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

drive_engine = DriveEngine()
