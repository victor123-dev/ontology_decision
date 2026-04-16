"""
MCP工具模块 - Action执行功能
提供对本体Action的执行能力，每个Action对应一个MCP工具
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, create_model
from typing import Any, Dict, List, Optional, Union
from app.dao.action_dao import get_action_dao
from app.services.action_service import get_action_service
from app.utils.shared_utils import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _create_action_parameter_model(action_id: str, parameters: List[Dict[str, Any]]) -> type:
    """根据Action参数动态创建Pydantic模型"""
    if not parameters:
        return None
    
    fields = {}
    for param in parameters:
        param_name = param.get('name', param.get('id', ''))
        if not param_name:
            continue
            
        param_type = param.get('type', 'string')
        param_description = param.get('description', '')
        param_required = param.get('required', False)
        
        # 映射类型到Python类型
        if param_type == 'integer':
            python_type = int
        elif param_type == 'number':
            python_type = float
        elif param_type == 'boolean':
            python_type = bool
        else:
            python_type = str
            
        # 处理可选参数
        if param_required:
            fields[param_name] = (python_type, Field(..., description=param_description))
        else:
            fields[param_name] = (Optional[python_type], Field(None, description=param_description))
    
    if not fields:
        return None
        
    model_name = f"{action_id.replace('-', '_').replace(' ', '_')}Parameters"
    return create_model(model_name, **fields)


def _execute_action_tool(action_data: Dict[str, Any], parameters: Dict[str, Any] = None, db=None) -> Dict[str, Any]:
    """
    执行指定的Action
    
    Args:
        action_data: Action的完整数据
        parameters: 执行Action所需的参数
        db: 数据库会话
        
    Returns:
        Action执行结果
    """
    try:
        action_id = action_data.get('id')
        action_name = action_data.get('name', action_id)
        
        # 获取Action服务并执行Action
        action_service = get_action_service()
        result = action_service.execute_action(action_id, parameters or {}, db)
        
        return {
            "success": True,
            "message": f"Action '{action_name}' executed successfully",
            "result": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute action '{action_name}': {str(e)}"
        )


# 动态注册所有Action作为MCP工具
def register_action_tools():
    """注册所有可用的Action作为MCP工具"""
    logger.info("开始注册Action MCP工具...")
    action_dao = get_action_dao()
    actions = action_dao.get_actions()
    
    logger.info(f"从数据库获取到 {len(actions)} 个Action")
    
    # 调试：打印所有获取到的Action ID和名称
    for i, action in enumerate(actions):
        action_id = action.get('id', 'N/A')
        action_name = action.get('name', 'N/A')
        api_name = action.get('api_name', 'N/A')
        logger.info(f"Action {i+1}: id={action_id}, name={action_name}, api_name={api_name}")
    
    registered_count = 0
    for action in actions:
        action_id = action.get('id')
        if not action_id:
            logger.warning(f"跳过没有ID的Action: {action}")
            continue
            
        action_name = action.get('name', action_id)
        api_name = action.get('api_name', action_id)
        description = action.get('description', f'Execute action: {action_name}')
        parameters = action.get('parameters', [])
        
        logger.info(f"正在处理Action: id={action_id}, name={action_name}, api_name={api_name}")
        
        # 创建参数模型
        param_model = _create_action_parameter_model(action_id, parameters)
        if param_model:
            logger.info(f"  - 创建了参数模型: {param_model.__name__}")
        else:
            logger.info(f"  - 无参数模型（无参数或参数无效）")
        
        # 创建工具函数
        def create_tool_func(action_data):
            def tool_func(
                params: param_model = None if param_model is None else Depends(),
                db=Depends(get_db)
            ):
                param_dict = params.dict() if params else {}
                return _execute_action_tool(action_data, param_dict, db)
            return tool_func
        
        tool_func = create_tool_func(action)
        
        # 设置函数元数据
        tool_func.__name__ = f"execute_{api_name}"
        tool_func.__doc__ = description
        
        # 添加路由
        route_path = f"/actions/{action_id}/execute"
        operation_id = f"execute_{api_name}"
        
        if param_model is None:
            router.post(
                route_path,
                operation_id=operation_id,
                summary=action_name,
                description=description,
                response_description="Action execution result"
            )(tool_func)
        else:
            router.post(
                route_path,
                operation_id=operation_id,
                summary=action_name,
                description=description,
                response_description="Action execution result"
            )(tool_func)
        
        logger.info(f"✓ 成功注册MCP工具: {operation_id} -> {route_path}")
        registered_count += 1
    
    logger.info(f"Action MCP工具注册完成，共注册 {registered_count} 个工具")


# 注册所有Action工具
register_action_tools()