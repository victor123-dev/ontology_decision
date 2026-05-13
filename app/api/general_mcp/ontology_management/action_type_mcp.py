"""行动类型管理模块 - Ontology Management MCP
提供 Action 的 CRUD 操作、代码验证和测试工具
集成语义一致性验证和 Agent 辅助功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from app.services.action_service import get_action_service, ActionService
from app.dao.action_dao import get_action_dao
from app.utils.shared_utils import get_db
import ast
import traceback
from .agent_helper import AgentHelper

router = APIRouter()

# ==================== Pydantic 模型定义 ====================

class ParameterDefinition(BaseModel):
    """Action参数定义"""
    name: str = Field(description="参数名称")
    type: str = Field(description="参数类型: string, integer, float, boolean, array, object")
    description: str = Field(description="参数描述")
    required: bool = Field(default=False, description="是否必填")
    default: Optional[Any] = Field(default=None, description="默认值")
    enum: Optional[List[str]] = Field(default=None, description="枚举值列表")


class CreateActionTypeParameters(BaseModel):
    """创建行动类型参数"""
    action_type_id: str = Field(description="行动类型唯一标识符，建议使用snake_case命名")
    action_type_name: str = Field(description="行动类型中文名称")
    description: str = Field(description="行动类型详细描述，包括使用场景")
    action_type: str = Field(
        description="行动类型: object(对象操作), link(关系操作), function(自定义函数)"
    )
    operation: str = Field(
        description="操作类型: create, update, delete, custom"
    )
    target_object_type_id: Optional[str] = Field(
        default=None, 
        description="目标对象类型ID（object/link类型必需）"
    )
    target_link_type_id: Optional[str] = Field(
        default=None, 
        description="目标关系类型ID（link类型必需）"
    )
    parameters: List[ParameterDefinition] = Field(
        default=[], 
        description="参数定义列表"
    )
    submission_criteria: Optional[List[Dict]] = Field(
        default=None, 
        description="提交条件列表"
    )
    function_code: Optional[str] = Field(
        default=None, 
        description="Python函数代码（function类型必需）。"
                    "代码结构: 1)引入库 2)定义函数def execute_xxx(parameters: dict) -> dict: 3)使用OntologySDK处理数据 "
                    "4)返回{'success':True/False,'message/error':'xxx','result':xxx} 5)最后调用result=execute_xxx(parameters)"
    )


class UpdateActionTypeParameters(BaseModel):
    """更新行动类型参数"""
    action_type_name: Optional[str] = Field(default=None, description="行动类型中文名称")
    description: Optional[str] = Field(default=None, description="行动类型详细描述")
    action_type: Optional[str] = Field(default=None, description="行动类型")
    operation: Optional[str] = Field(default=None, description="操作类型")
    target_object_type_id: Optional[str] = Field(default=None, description="目标对象类型ID")
    target_link_type_id: Optional[str] = Field(default=None, description="目标关系类型ID")
    parameters: Optional[List[ParameterDefinition]] = Field(default=None, description="参数定义列表")
    submission_criteria: Optional[List[Dict]] = Field(default=None, description="提交条件列表")
    function_code: Optional[str] = Field(default=None, description="Python函数代码")


class ValidateActionCodeRequest(BaseModel):
    """验证 Action 代码请求"""
    function_code: str = Field(description="Python函数代码")

class TestActionTypeRequest(BaseModel):
    """测试 Action 类型请求"""
    parameters: Dict = Field(default={}, description="测试参数")


# ==================== 验证工具函数 ====================

def _validate_python_code(code: str) -> Dict:
    """
    验证 Python 代码语法和结构
    
    Returns:
        {valid: bool, errors: List[str]}
    """
    try:
        # 尝试解析 AST
        tree = ast.parse(code)
        
        # 检查是否包含函数定义
        has_function = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                has_function = True
                break
        
        if not has_function:
            return {
                "valid": False,
                "errors": ["代码必须包含至少一个函数定义"]
            }
        
        # 检查是否有 result 赋值语句
        has_result_assignment = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "result":
                        has_result_assignment = True
                        break
        
        if not has_result_assignment:
            return {
                "valid": False,
                "errors": ["代码最后必须包含 result = execute_xxx(parameters) 赋值语句"]
            }
        
        return {"valid": True, "errors": []}
        
    except SyntaxError as e:
        return {
            "valid": False,
            "errors": [f"语法错误: {str(e)}"]
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"验证错误: {str(e)}"]
        }


# ==================== 行动类型 CRUD 工具 ====================

@router.get(
    "/list_action_types",
    operation_id="list_action_types",
    summary="列出所有行动类型",
    description="""
获取所有行动类型的列表。
支持按 action_type、operation 或 target_object_type_id 过滤。

适用于 Agent 了解当前有哪些 Action 可用。
    """,
    response_description="行动类型列表"
)
def list_action_types(
    action_type: Optional[str] = Query(None, description="按行动类型过滤: object, link, function"),
    operation: Optional[str] = Query(None, description="按操作类型过滤: create, update, delete, custom"),
    target_object_type_id: Optional[str] = Query(None, description="按目标对象类型ID过滤"),
    action_service: ActionService = Depends(get_action_service)
):
    """列出所有行动类型"""
    try:
        actions = action_service.get_actions()
        
        # 过滤
        if action_type:
            actions = [a for a in actions if a.get("action_type") == action_type]
        if operation:
            actions = [a for a in actions if a.get("operation") == operation]
        if target_object_type_id:
            actions = [a for a in actions if a.get("target_model_id") == target_object_type_id]
        
        return [
            {
                "action_type_id": action["id"],
                "action_type_name": action.get("name", "Unnamed Action"),
                "description": action.get("description", ""),
                "action_type": action.get("action_type"),
                "operation": action.get("operation"),
                "target_object_type_id": action.get("target_model_id"),
                "target_link_type_id": action.get("target_link_id"),
                "parameters_count": len(action.get("parameters", []))
            }
            for action in actions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"列出行动类型失败: {str(e)}"
        )


@router.get(
    "/get_action_type/{action_type_id}",
    operation_id="get_action_type",
    summary="获取行动类型详情",
    description="""
获取单个行动类型的完整管理视图，包括:
- 基本信息（ID、名称、描述）
- 行动类型和操作类型
- 参数定义列表
- 提交条件
- 函数代码（如果有）
- 代码分析结果（语法检查）

适用于查看行动类型的完整定义和代码。
    """,
    response_description="行动类型的完整管理信息"
)
def get_action_type(
    action_type_id: str,
    action_service: ActionService = Depends(get_action_service)
):
    """获取行动类型详情"""
    try:
        action = action_service.get_action(action_type_id)
        
        if not action:
            raise HTTPException(
                status_code=404,
                detail=f"行动类型 '{action_type_id}' 不存在"
            )
        
        # 如果有函数代码，进行语法检查
        code_analysis = None
        if action.get("function_code"):
            code_validation = _validate_python_code(action["function_code"])
            code_analysis = {
                "has_code": True,
                "code_length": len(action["function_code"]),
                "syntax_valid": code_validation["valid"],
                "syntax_errors": code_validation["errors"]
            }
        else:
            code_analysis = {
                "has_code": False,
                "code_length": 0,
                "syntax_valid": None,
                "syntax_errors": []
            }
        
        return {
            "action_type_id": action["id"],
            "action_type_name": action.get("name"),
            "description": action.get("description"),
            "action_type": action.get("action_type"),
            "operation": action.get("operation"),
            "target_object_type_id": action.get("target_model_id"),
            "target_link_type_id": action.get("target_link_id"),
            "parameters": action.get("parameters", []),
            "submission_criteria": action.get("submission_criteria", []),
            "function_code": action.get("function_code"),
            "code_analysis": code_analysis,
            "next_recommended_actions": [
                "test_action_type: 测试 Action 执行逻辑",
                "validate_action_code: 验证代码质量和安全性"
            ] if action.get("function_code") else [
                "create_action_type: 创建更多 Action",
                "list_action_types: 查看所有 Action"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取行动类型失败: {str(e)}"
        )


@router.post(
    "/create_action_type",
    operation_id="create_action_type",
    summary="创建行动类型",
    description="""
创建新的行动类型。

**支持类型**:
- **object**: 对象操作（创建/更新/删除对象数据）
- **link**: 关系操作（创建/更新/删除关系数据）
- **function**: 自定义函数（执行任意 Python 代码）

**支持功能**:
- 自动验证 Python 函数代码语法
- 详细的错误信息
- 建议在创建前使用 validate_action_code 工具

**函数代码要求**:
```python
def execute(parameters: dict, db: Session) -> dict:
    # 你的逻辑
    return {
        "success": True,
        "result": {...},
        "message": "操作成功"
    }
```
    """,
    response_description="创建的行动类型信息"
)
def create_action_type(
    parameters: CreateActionTypeParameters,
    action_service: ActionService = Depends(get_action_service)
):
    """创建行动类型"""
    try:
        # 验证 action_type
        valid_action_types = ["object", "link", "function"]
        if parameters.action_type not in valid_action_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的行动类型 '{parameters.action_type}'。必须是以下之一: {', '.join(valid_action_types)}"
            )
        
        # 验证 operation
        valid_operations = ["create", "update", "delete", "custom"]
        if parameters.operation not in valid_operations:
            raise HTTPException(
                status_code=400,
                detail=f"无效的操作类型 '{parameters.operation}'。必须是以下之一: {', '.join(valid_operations)}"
            )
        
        # 验证 function/custom 类型必须有函数代码
        if parameters.action_type in ["function", "custom"] and not parameters.function_code:
            raise HTTPException(
                status_code=400,
                detail="'function' 或 'custom' 行动类型必须提供函数代码"
            )
        
        # 验证函数代码语法
        if parameters.function_code:
            code_validation = _validate_python_code(parameters.function_code)
            if not code_validation["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Python 代码无效: {', '.join(code_validation['errors'])}"
                )
        
        # 构建 action_data
        action_data = {
            "id": parameters.action_type_id,
            "name": parameters.action_type_name,
            "description": parameters.description,
            "action_type": parameters.action_type,
            "operation": parameters.operation,
            "target_model_id": parameters.target_object_type_id,
            "target_link_id": parameters.target_link_type_id,
            "parameters": [p.dict() for p in parameters.parameters],
            "submission_criteria": parameters.submission_criteria,
            "function_code": parameters.function_code
        }
        
        # 创建 Action
        action = action_service.create_action(action_data)
        
        if not action:
            raise HTTPException(
                status_code=500,
                detail="创建行动失败"
            )
        
        return {
            "action_type_id": action["id"],
            "action_type_name": action.get("name"),
            "action_type": action.get("action_type"),
            "operation": action.get("operation"),
            "message": f"行动类型 '{parameters.action_type_id}' 创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建行动类型失败: {str(e)}"
        )


@router.put(
    "/update_action_type/{action_type_id}",
    operation_id="update_action_type",
    summary="更新行动类型",
    description="""
更新行动类型的定义。

**注意**:
- 更新会重新验证函数代码语法
- 修改参数定义不会影响已执行的历史记录
    """,
    response_description="更新后的行动类型信息"
)
def update_action_type(
    action_type_id: str,
    parameters: UpdateActionTypeParameters,
    action_service: ActionService = Depends(get_action_service)
):
    """更新行动类型"""
    try:
        # 检查 Action 是否存在
        existing_action = action_service.get_action(action_type_id)
        if not existing_action:
            raise HTTPException(
                status_code=404,
                detail=f"行动类型 '{action_type_id}' 不存在"
            )
        
        # 如果有新的函数代码，验证语法
        if parameters.function_code:
            code_validation = _validate_python_code(parameters.function_code)
            if not code_validation["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Python 代码无效: {', '.join(code_validation['errors'])}"
                )
        
        # 构建更新数据
        update_data = {}
        if parameters.action_type_name:
            update_data["name"] = parameters.action_type_name
        if parameters.description is not None:
            update_data["description"] = parameters.description
        if parameters.action_type:
            update_data["action_type"] = parameters.action_type
        if parameters.operation:
            update_data["operation"] = parameters.operation
        if parameters.target_object_type_id is not None:
            update_data["target_model_id"] = parameters.target_object_type_id
        if parameters.target_link_type_id is not None:
            update_data["target_link_id"] = parameters.target_link_type_id
        if parameters.parameters is not None:
            update_data["parameters"] = [p.dict() for p in parameters.parameters]
        if parameters.submission_criteria is not None:
            update_data["submission_criteria"] = parameters.submission_criteria
        if parameters.function_code is not None:
            update_data["function_code"] = parameters.function_code
        
        # 更新 Action
        action = action_service.update_action(action_type_id, update_data)
        
        if not action:
            raise HTTPException(
                status_code=500,
                detail="更新行动失败"
            )
        
        return {
            "action_type_id": action["id"],
            "action_type_name": action.get("name"),
            "message": f"行动类型 '{action_type_id}' 更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新行动类型失败: {str(e)}"
        )


@router.delete(
    "/delete_action_type/{action_type_id}",
    operation_id="delete_action_type",
    summary="删除行动类型",
    description="""
删除行动类型。

**注意**:
- 删除操作不可恢复
- 不会影响已执行的历史记录
    """,
    response_description="删除结果"
)
def delete_action_type(
    action_type_id: str,
    action_service: ActionService = Depends(get_action_service)
):
    """删除行动类型"""
    try:
        success = action_service.delete_action(action_type_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"行动类型 '{action_type_id}' 不存在或删除失败"
            )
        
        return {
            "message": f"行动类型 '{action_type_id}' 删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除行动类型失败: {str(e)}"
        )


# ==================== 验证和测试工具 ====================

@router.post(
    "/validate_action_code",
    operation_id="validate_action_code",
    summary="验证function_code",
    description="""
验证 function_code 的 Python 函数代码语法和结构。

**支持功能**:
- 不执行代码，仅进行静态分析
- 检查语法错误
- 检查函数签名是否正确
- 检查是否包含 result 赋值语句
- 返回详细的错误和警告信息

**代码编写规范**:
1. 引入必要的库（如 OntologySDK、ortools 等）
2. 定义执行函数: def execute_xxx(parameters: dict) -> dict:
3. 函数内部使用 OntologySDK 处理数据
4. 返回标准格式: {"success": True/False, "message/error": "xxx", "result": xxx}
5. **最后必须调用函数并赋值**: result = execute_xxx(parameters)

**成功返回格式**:
```python
{
    "success": True,
    "message": "操作成功描述",
    "result": {
        # 具体结果数据
    }
}
```

**失败返回格式**:
```python
{
    "success": False,
    "error": "错误描述"
}
```

**完整示例**（计算 CTP）:
```python
from my_ontology_sdk import OntologyClient
from datetime import datetime

def execute_calculate_ctp(parameters):
    # 1. 解析参数
    product_id = parameters.get("product_id")
    quantity = parameters.get("quantity")
    
    if not product_id:
        return {"success": False, "error": "请提供产品ID"}
    
    # 2. 初始化SDK客户端
    client = OntologyClient("http://localhost:8080", api_key="your-api-key")
    
    # 3. 使用SDK查询数据
    products = client.models.Product.find(product_id=product_id)
    if not products:
        return {"success": False, "error": f"产品 {product_id} 不存在"}
    
    # 4. 业务逻辑处理
    # ... 具体计算逻辑 ...
    
    # 5. 返回结果
    return {
        "success": True,
        "message": "CTP计算完成",
        "result": {
            "product_id": product_id,
            "estimated_delivery_date": "2024-01-15"
        }
    }

# 必须调用函数并赋值给 result
result = execute_calculate_ctp(parameters)
```

**使用场景**:
- 编写函数代码后的预检查
- 调试代码问题
- 在创建/更新行动类型前验证
    """,
    response_description="验证结果"
)
def validate_action_code(
    validation_request: ValidateActionCodeRequest
):
    """验证 Action 代码"""
    try:
        function_code = validation_request.function_code
        
        if not function_code:
            raise HTTPException(
                status_code=400,
                detail="function_code is required"
            )
        
        errors = []
        warnings = []
        suggestions = []
        
        # 1. 语法检查
        code_validation = _validate_python_code(function_code)
        if not code_validation["valid"]:
            errors.extend(code_validation["errors"])
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions
            }
        
        # 2. 检查函数签名
        try:
            tree = ast.parse(function_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 检查参数
                    args = node.args
                    arg_names = [arg.arg for arg in args.args]
                    
                    if "parameters" not in arg_names:
                        warnings.append("函数应该包含 'parameters' 参数")
                        suggestions.append("推荐签名: def execute_xxx(parameters: dict) -> dict:")
                    
                    # 检查是否包含 return 语句
                    has_return = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return):
                            has_return = True
                            break
                    
                    if not has_return:
                        warnings.append("函数应该包含 return 语句")
                        suggestions.append("返回格式: {'success': True/False, 'message/error': 'xxx', 'result': xxx}")
                    
                    break
        except Exception as e:
            warnings.append(f"无法分析函数签名: {str(e)}")
        
        # 3. 检查危险操作
        dangerous_patterns = ["import os", "import sys", "subprocess", "eval(", "exec("]
        for pattern in dangerous_patterns:
            if pattern in function_code:
                warnings.append(f"检测到潜在危险模式: '{pattern}'")
                suggestions.append("出于安全考虑，避免使用系统级操作")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate action code: {str(e)}"
        )


@router.post(
    "/test_action_type/{action_type_id}",
    operation_id="test_action_type",
    summary="测试行动类型",
    description="""
在沙箱环境中测试行动类型的执行。

**支持功能**:
- 在事务中执行，自动回滚
- 捕获执行异常
- 返回执行时间和结果
- 不会影响实际数据

**使用场景**:
- 创建/更新行动类型后的验证
- 调试行动类型逻辑
- 验证参数定义是否正确

**注意**: 
- 测试执行会在事务中完成，自动回滚
- 对于 function 类型的行动类型，会实际执行代码
- 确保测试参数符合参数定义
    """,
    response_description="测试结果"
)
def test_action_type(
    action_type_id: str,
    test_request: TestActionTypeRequest,
    action_service: ActionService = Depends(get_action_service),
    db: Session = Depends(get_db)
):
    """测试行动类型"""
    import time
    
    try:
        # 检查 Action 是否存在
        action = action_service.get_action(action_type_id)
        if not action:
            raise HTTPException(
                status_code=404,
                detail=f"Action type '{action_type_id}' not found"
            )
        
        # 获取测试参数
        test_parameters = test_request.parameters
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 在事务中执行
            result = action_service.execute_action(
                action_type_id, 
                test_parameters, 
                db
            )
            
            # 回滚事务（测试模式）
            db.rollback()
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "action_id": action_type_id,
                "execution_time": round(execution_time, 3),
                "result": result.get("result"),
                "message": result.get("message", "Test execution completed"),
                "test_mode": True
            }
            
        except Exception as exec_error:
            # 回滚事务
            db.rollback()
            execution_time = time.time() - start_time
            
            return {
                "success": False,
                "action_id": action_type_id,
                "execution_time": round(execution_time, 3),
                "error": str(exec_error),
                "traceback": traceback.format_exc(),
                "test_mode": True
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test action type: {str(e)}"
        )
