"""逻辑执行器 - 处理驱动逻辑的匹配和执行"""
import copy
from typing import Dict, Any, List
from datetime import datetime
from app.models.drive_logic import DriveLogic, Task, TaskInstance
from app.utils.logger import get_logger
from app.utils.data_source_accessor import DataSourceAccessor
from app.utils.function_registry import prepare_function_environment, extract_function_names
import traceback
from app.utils.shared_utils import log_event_with_parent

logger = get_logger(__name__)


class LogicExecutor:
    """逻辑执行器"""
    
    def __init__(self):
        pass
    
    def execute_logic(self, logic: DriveLogic, event: Dict[str, Any], db, trace_id: str = None, parent_log_id: int = None):
        """执行驱动逻辑（增强版）"""
        try:
            config = logic.config or {}
            logic_type = logic.type
            
            logger.info(f"执行驱动逻辑: {logic.name} (类型: {logic_type})")
            
            # 记录驱动逻辑执行日志
            logic_log_id = log_event_with_parent(
                'info', 'drive_logic', 
                f"执行驱动逻辑: {logic.name}", 
                {'logic_name': logic.name, 'logic_type': logic_type}, 
                trace_id, parent_log_id
            )
            
            # 预处理
            # TODO DEMO这里只处理了第一个受影响的记录，一阶函数遇到批量数组应如何处理？循环？需思考
            processed_data = event.get('data', {})
            record_data = event.get('data', {}).get('affected_records', {})[0].get('record', {})
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
                    local_vars = prepare_function_environment(pre_condition, record_data, event)

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
                    # 创建事件数据的深拷贝，避免影响其他逻辑的执行
                    event_copy = copy.deepcopy(event)
                    # 更新事件数据为处理后的数据
                    event_copy['data'] = processed_data
                    event_copy['record_data'] = record_data
                    self._assign_tasks(tasks, event_copy, db, trace_id, logic_log_id)
                else:
                    logger.warning(f"驱动逻辑 {logic.name} 没有关联任务")
                    log_event_with_parent('warning', 'drive_logic', f"驱动逻辑 {logic.name} 没有关联任务", {'logic_name': logic.name}, trace_id, logic_log_id)
            else:
                logger.info(f"驱动逻辑 {logic.name} 条件不满足，跳过任务触发")
                log_event_with_parent('info', 'drive_logic', f"驱动逻辑 {logic.name} 条件不满足，跳过任务触发", {'logic_name': logic.name}, trace_id, logic_log_id)
            
        except Exception as e:
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
                'event': copy.deepcopy(event),
                'data_source': DataSourceAccessor()
            }
            exec(script_content, safe_globals, local_vars)
            
            return local_vars.get('result', event.get('data', {}))
        except Exception as e:
            logger.error(f"预处理脚本执行失败: {str(e)}")
            return event.get('data', {})
    
    def _assign_tasks(self, tasks: List[Task], event: Dict[str, Any], db, trace_id: str = None, parent_log_id: int = None):
        """分配任务给Agent - 只创建任务实例，不立即执行(支持任务组)"""
        try:
            if len(tasks) <= 1:
                # 单个任务：保持原有逻辑
                if tasks:  # 确保 tasks 不为空
                    task = tasks[0]
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
                    
                    logger.info(f"任务 '{task.name}' 已创建，等待调度")
                    log_id = log_event_with_parent('info', 'drive_logic', f"任务 '{task.name}' 已创建，等待调度", {'task_name': task.name}, trace_id, parent_log_id)
                    # 更新 TaskInstance 的 result 字段，添加 log_id
                    if log_id:
                        task_instance.result['creation_log_id'] = log_id
                        db.commit()
            else:
                # 多个任务：创建任务组标识
                import uuid
                group_id = str(uuid.uuid4())
                
                # 先创建所有任务实例，保存引用以便后续更新
                task_instances = []
                for i, task in enumerate(tasks):
                    task_instance = TaskInstance(
                        task_id=task.id,
                        assigned_agent_id=None,
                        status='pending',
                        result={
                            'event': event,
                            'created_at': datetime.now().isoformat(),
                            'trace_id': trace_id,
                            'is_group_task': True,
                            'group_id': group_id,
                            'group_size': len(tasks),
                            'group_index': i,
                            'group_tasks': [t.name for t in tasks]
                        }
                    )
                    db.add(task_instance)
                    task_instances.append(task_instance)
                
                # 在单个事务中提交所有任务实例
                db.commit()
                
                # 合并所有任务名称和信息到单条日志
                task_names = [task.name for task in tasks]
                task_info_list = []
                for i, task in enumerate(tasks):
                    task_info_list.append({
                        'task_name': task.name,
                        'task_id': task.id,
                        'group_index': i
                    })
                
                logger.info(f"任务组 ({group_id}) 包含 {len(tasks)} 个任务已创建，等待调度: {', '.join(task_names)}")
                log_id = log_event_with_parent('info', 'drive_logic', f"任务组包含任务: [{', '.join(task_names)}] 已创建", 
                         {'task_names': task_names, 'group_id': group_id, 'tasks': task_info_list}, trace_id, parent_log_id)
                # 更新所有 TaskInstance 的 result 字段，添加 log_id
                if log_id:
                    for task_instance in task_instances:
                        task_instance.result['creation_log_id'] = log_id
                    db.commit()
                
        except Exception as e:
            # 如果发生异常，回滚整个事务
            db.rollback()
            logger.error(f"创建任务实例失败: {str(e)}")
            logger.error(traceback.format_exc())