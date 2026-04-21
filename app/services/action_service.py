from typing import Dict, Any, Optional, List
from app.dao.action_dao import get_action_dao, ActionDAO
from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger
from sqlalchemy.orm import Session
from app.models.business_model import BusinessModel, BusinessModelField
from app.models.business_model_link import BusinessModelLink
from app.utils.shared_utils import get_db

logger = get_logger(__name__)


class ActionService:
    def __init__(self):
        self.action_dao: ActionDAO = get_action_dao()
    
    def create_action(self, action_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.action_dao.create_action(action_data)
    
    def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        return self.action_dao.get_action_by_id(action_id)
    
    def get_actions(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.action_dao.get_actions(filters)
    
    def get_actions_by_model(self, business_model_id: str) -> List[Dict[str, Any]]:
        return self.action_dao.get_actions_by_model(business_model_id)
    
    def update_action(self, action_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.action_dao.update_action(action_id, update_data)
    
    def delete_action(self, action_id: str) -> bool:
        return self.action_dao.delete_action(action_id)
    
    def validate_parameters(self, action: Dict[str, Any], parameters: Dict[str, Any]) -> tuple[bool, List[str]]:
        errors = []
        action_params = action.get("parameters", [])
        
        for param in action_params:
            param_name = param.get("name")
            param_required = param.get("required", False)
            param_type = param.get("type", "string")
            param_default = param.get("default_value")
            
            if param_required and param_name not in parameters:
                errors.append(f"Required parameter '{param_name}' is missing")
                continue
            
            if param_name in parameters:
                value = parameters[param_name]
                if not self._validate_type(value, param_type):
                    errors.append(f"Parameter '{param_name}' should be of type {param_type}")
        
        return len(errors) == 0, errors
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        type_map = {
            "string": str,
            "text": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "object": dict,
            "array": list,
            "date": str,      # 日期类型作为字符串处理
            "datetime": str   # 日期时间类型作为字符串处理
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True
        
        return isinstance(value, expected_python_type)
    
    def execute_action(self, action_id: str, parameters: Dict[str, Any], db: Session) -> Dict[str, Any]:
        action = self.get_action(action_id)
        if not action:
            raise ValueError(f"Action not found: {action_id}")
        
        is_valid, errors = self.validate_parameters(action, parameters)
        if not is_valid:
            raise ValueError(f"Parameter validation failed: {', '.join(errors)}")
        
        submission_criteria = action.get("submission_criteria", [])
        for criterion in submission_criteria:
            if not self._evaluate_criterion(criterion, parameters):
                raise ValueError(f"Submission criterion failed: {criterion.get('description', 'Unknown condition')}")
        
        action_type = action.get("action_type")
        action_operation = action.get("operation")
        
        if action_type == "object":
            return self._execute_object_action(action, action_operation, parameters, db)
        elif action_type == "link":
            return self._execute_link_action(action, action_operation, parameters, db)
        elif action_type == "function":
            return self._execute_function_action(action, parameters, db)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def _evaluate_criterion(self, criterion: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        criterion_type = criterion.get("type")
        if criterion_type == "field_validation":
            field_name = criterion.get("field_name")
            field_value = parameters.get(field_name)
            validation_rule = criterion.get("rule")
            
            if validation_rule == "not_empty":
                return field_value is not None and str(field_value).strip() != ""
            elif validation_rule == "email":
                import re
                if field_value is None:
                    return False
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                return re.match(email_pattern, str(field_value)) is not None
            elif validation_rule == "phone":
                import re
                if field_value is None:
                    return False
                # 支持中国大陆手机号格式
                phone_pattern = r'^1[3-9]\d{9}$'
                return re.match(phone_pattern, str(field_value)) is not None
            elif validation_rule == "min_length":
                min_len = criterion.get("min_length", 0)
                if field_value is None:
                    return False
                return len(str(field_value)) >= min_len
            elif validation_rule == "max_length":
                max_len = criterion.get("max_length", float('inf'))
                if field_value is None:
                    return False
                return len(str(field_value)) <= max_len
            elif validation_rule == "positive":
                return isinstance(field_value, (int, float)) and field_value > 0
        
        elif criterion_type == "custom_condition":
            # 自定义条件将在方案2中实现
            custom_expression = criterion.get("expression", "")
            if not custom_expression:
                return True
            
            # 这里将实现安全的自定义条件执行（方案2）
            return self._evaluate_custom_condition(custom_expression, parameters)
        
        return True
    
    def _evaluate_custom_condition(self, expression: str, parameters: Dict[str, Any]) -> bool:
        """
        安全地评估自定义条件表达式
        支持简单的JavaScript-like表达式，但实际在Python中执行
        """
        try:
            # 创建安全的执行环境
            safe_globals = {
                "__builtins__": {
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "max": max,
                    "min": min,
                    "abs": abs,
                    "sum": sum,
                    "all": all,
                    "any": any,
                }
            }
            
            # 将parameters中的键作为局部变量
            safe_locals = {}
            for key, value in parameters.items():
                # 只允许字母、数字、下划线的变量名
                if key.replace('_', '').replace('-', '').isalnum():
                    safe_locals[key] = value
            
            # 执行表达式
            result = eval(expression, safe_globals, safe_locals)
            return bool(result)
        except Exception as e:
            logger.error(f"Custom condition evaluation failed: {e}")
            return False  # 如果评估失败，返回False以确保安全
    
    def _execute_object_action(self, action: Dict[str, Any], operation: str, parameters: Dict[str, Any], db: Session) -> Dict[str, Any]:
        target_model_id = action.get("target_model_id")
        business_model = db.query(BusinessModel).filter(BusinessModel.id == target_model_id).first()
        
        if not business_model:
            raise ValueError(f"Business model not found: {target_model_id}")
        
        data_source_id = business_model.data_source_id
        table_name = business_model.id
        
        if operation == "create_object":
            result = data_source_manager.execute_insert(
                data_source_id=data_source_id,
                table_name=table_name,
                data=parameters
            )
            return {"success": result, "message": "Object created successfully"}
        
        elif operation == "update_object":
            result = data_source_manager.execute_update(
                data_source_id=data_source_id,
                table_name=table_name,
                data=parameters,
                primary_key=business_model.primary_key_id,
                primary_value=parameters[business_model.primary_key_id]
            )
            return {"success": result, "message": "Object updated successfully"}
        
        elif operation == "delete_object":
            result = data_source_manager.execute_delete(
                data_source_id=data_source_id,
                table_name=table_name,
                primary_key=business_model.primary_key_id,
                primary_value=parameters[business_model.primary_key_id]
            )
            return {"success": result, "message": "Object deleted successfully"}
        
        else:
            raise ValueError(f"Unknown object operation: {operation}")
    
    def _execute_link_action(self, action: Dict[str, Any], operation: str, parameters: Dict[str, Any], db: Session) -> Dict[str, Any]:
        link_id = action.get("target_link_id")
        link = db.query(BusinessModelLink).filter(BusinessModelLink.id == link_id).first()
        
        if not link:
            raise ValueError(f"Link not found: {link_id}")
        
        source_model = db.query(BusinessModel).filter(BusinessModel.id == link.source_model).first()
        target_model = db.query(BusinessModel).filter(BusinessModel.id == link.target_model).first()
        
        if not source_model or not target_model:
            raise ValueError("Source or target model not found for link")
        
        if link.cardinality == "many-to-many" and link.intermediate_model:
            table_name = link.intermediate_model
            data_source_id = source_model.data_source_id
            
            if operation == "create_link":
                result = data_source_manager.execute_insert(
                    data_source_id=data_source_id,
                    table_name=table_name,
                    data=parameters
                )
                return {"success": result, "message": "Link created successfully"}
            
            elif operation == "delete_link":
                result = data_source_manager.execute_delete(
                    data_source_id=data_source_id,
                    table_name=table_name,
                    primary_key=link.intermediate_model,
                    primary_value=parameters[link.intermediate_model]
                )
                return {"success": result, "message": "Link deleted successfully"}
        
        raise ValueError(f"Link operation not implemented: {operation} for cardinality {link.cardinality}")
    
    def _execute_function_action(self, action: Dict[str, Any], parameters: Dict[str, Any], db: Session) -> Dict[str, Any]:
        function_code = action.get("function_code", "")
        
        try:
            import ast
            # 只保留对危险函数调用的基本检查
            tree = ast.parse(function_code)
            for node in ast.walk(tree):
                # 禁止危险函数调用
                if isinstance(node, ast.Call) and hasattr(node.func, 'id') and node.func.id in ['eval', 'exec', 'open']:
                    raise ValueError(f"Disallowed function call: {node.func.id}")
            
            local_vars = {
                "parameters": parameters,
            }
            exec(function_code, local_vars)
            
            function_result = local_vars.get("result")
            
            # 安全地提取各个字段，构建标准化响应
            if isinstance(function_result, dict):
                success = function_result.get("success", True)
                result_data = function_result.get("result", function_result)
                message = function_result.get("message")
                error = function_result.get("error")
            else:
                # 如果 function_result 不是字典，视为成功的结果数据
                success = True
                result_data = function_result
                message = "Function executed successfully"
                error = None
            
            # 构建最终响应
            response = {"success": success}
            if success:
                response["result"] = result_data
                if message:
                    response["message"] = message
            else:
                if error:
                    response["error"] = error
                elif message:
                    response["error"] = message
                else:
                    response["error"] = "Function execution failed"
            
            return response
        
        except Exception as e:
            logger.error(f"Function execution error: {e}")
            return {"success": False, "error": str(e)}


def get_action_service() -> ActionService:
    return ActionService()
