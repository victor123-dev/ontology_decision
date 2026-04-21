"""逻辑执行器 - 处理驱动逻辑的匹配和执行"""
import copy
from typing import Dict, Any, List
from datetime import datetime
from app.models.drive_logic import DriveLogic
from app.utils.logger import get_logger
from app.utils.data_source_accessor import DataSourceAccessor
from app.utils.function_registry import prepare_function_environment, extract_function_names
from app.services.action_service import get_action_service
import traceback
from app.utils.shared_utils import log_event_with_parent

logger = get_logger(__name__)


class LogicExecutor:
    """逻辑执行器"""
    
    def __init__(self):
        self.action_service = get_action_service()
    
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
            trigger_actions = False
            
            if logic_type == 'script' and config.get('script_content'):
                result = self._run_preprocess_script(config.get('script_content'), event)
                # 检查脚本返回值
                if isinstance(result, tuple) and len(result) == 2:
                    # 脚本返回 (bool, dict) 形式
                    trigger_actions = result[0]
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
                    trigger_actions = eval(pre_condition, safe_globals, local_vars)

                    logger.info(f"First Order 条件评估结果: {trigger_actions}")

                except Exception as e:
                    logger.error(f"评估前置条件失败: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 只有当条件满足时才触发行动
            if trigger_actions:
                # 关联的行动
                action_ids = logic.action_ids or []
                if action_ids:
                    # 创建事件数据的深拷贝，避免影响其他逻辑的执行
                    event_copy = copy.deepcopy(event)
                    # 更新事件数据为处理后的数据
                    event_copy['data'] = processed_data
                    event_copy['record_data'] = record_data
                    self._execute_actions(action_ids, event_copy, db, trace_id, logic_log_id)
                else:
                    logger.warning(f"驱动逻辑 {logic.name} 没有关联行动")
                    log_event_with_parent('warning', 'drive_logic', f"驱动逻辑 {logic.name} 没有关联行动", {'logic_name': logic.name}, trace_id, logic_log_id)
            else:
                logger.info(f"驱动逻辑 {logic.name} 条件不满足，跳过行动触发")
                log_event_with_parent('info', 'drive_logic', f"驱动逻辑 {logic.name} 条件不满足，跳过行动触发", {'logic_name': logic.name}, trace_id, logic_log_id)
            
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
    
    def _execute_actions(self, action_ids: List[str], event: Dict[str, Any], db, trace_id: str = None, parent_log_id: int = None):
        """执行关联的行动"""
        try:
            for action_id in action_ids:
                try:
                    # 从事件数据中提取参数
                    parameters = self._extract_action_parameters(action_id, event)
                    
                    # 执行行动
                    result = self.action_service.execute_action(action_id, parameters, db)
                    
                    logger.info(f"行动 '{action_id}' 执行完成，结果: {result}")
                    if result.get('success', False):
                        log_event_with_parent('info', 'drive_logic', f"行动 '{action_id}' 执行成功", 
                                 {'action_id': action_id, 'success': True, 'result': result}, trace_id, parent_log_id)
                    else:
                        logger.error(f"行动 '{action_id}' 执行失败，结果: {result}")
                        log_event_with_parent('error', 'drive_logic', f"行动 '{action_id}' 执行失败", 
                                 {'action_id': action_id, 'success': False, 'result': result}, trace_id, parent_log_id)
                    
                except Exception as e:
                    logger.error(f"执行行动 '{action_id}' 失败: {str(e)}")
                    log_event_with_parent('error', 'drive_logic', f"执行行动 '{action_id}' 失败", 
                             {'action_id': action_id, 'error': str(e)}, trace_id, parent_log_id)
                    
        except Exception as e:
            logger.error(f"执行行动组失败: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _extract_action_parameters(self, action_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """从事件数据中提取行动参数"""
        # 这里可以根据具体的行动定义来提取参数
        # 目前简单地返回事件中的record_data作为参数
        record_data = event.get('record_data', {})
        
        # 如果record_data为空，尝试从event.data中获取
        if not record_data:
            record_data = event.get('data', {}).get('affected_records', [{}])[0].get('record', {})
        
        return record_data