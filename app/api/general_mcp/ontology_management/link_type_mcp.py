"""关系类型管理模块 - Ontology Management MCP
提供 BusinessModelLink 的 CRUD 操作和验证工具
集成语义一致性验证和 Agent 辅助功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.business_model_link import BusinessModelLink
from app.models.business_model import BusinessModel, BusinessModelField
from app.utils.shared_utils import get_db
from .semantic_validator import SemanticValidator
from .agent_helper import AgentHelper

router = APIRouter()

# ==================== Pydantic 模型定义 ====================

class CreateLinkTypeParameters(BaseModel):
    """创建关系类型参数"""
    link_type_id: str = Field(description="关系类型唯一标识符")
    link_type_name: str = Field(description="关系类型中文名称")
    description: Optional[str] = Field(default=None, description="关系描述")
    source_object_type_id: str = Field(description="源对象类型ID")
    source_key: str = Field(description="源对象字段ID")
    target_object_type_id: str = Field(description="目标对象类型ID")
    target_key: str = Field(description="目标对象字段ID")
    cardinality: str = Field(
        description="基数类型: one-to-one, one-to-many, many-to-one, many-to-many"
    )
    intermediate_object_type_id: Optional[str] = Field(
        default=None, 
        description="中间对象类型ID（仅many-to-many需要）"
    )
    intermediate_source_key: Optional[str] = Field(
        default=None, 
        description="中间表指向源的字段（仅many-to-many需要）"
    )
    intermediate_target_key: Optional[str] = Field(
        default=None, 
        description="中间表指向目标的字段（仅many-to-many需要）"
    )


class UpdateLinkTypeParameters(BaseModel):
    """更新关系类型参数"""
    link_type_name: Optional[str] = Field(default=None, description="关系类型中文名称")
    description: Optional[str] = Field(default=None, description="关系描述")
    source_object_type_id: Optional[str] = Field(default=None, description="源对象类型ID")
    source_key: Optional[str] = Field(default=None, description="源对象字段ID")
    target_object_type_id: Optional[str] = Field(default=None, description="目标对象类型ID")
    target_key: Optional[str] = Field(default=None, description="目标对象字段ID")
    cardinality: Optional[str] = Field(default=None, description="基数类型")
    intermediate_object_type_id: Optional[str] = Field(default=None, description="中间对象类型ID")
    intermediate_source_key: Optional[str] = Field(default=None, description="中间表指向源的字段")
    intermediate_target_key: Optional[str] = Field(default=None, description="中间表指向目标的字段")


# ==================== 验证工具函数 ====================

def _validate_link_constraints(
    db: Session,
    source_model_id: str,
    source_key: str,
    target_model_id: str,
    target_key: str,
    cardinality: str,
    intermediate_model_id: Optional[str] = None,
    intermediate_source_key: Optional[str] = None,
    intermediate_target_key: Optional[str] = None
):
    """验证关系约束"""
    # 验证源模型和目标模型是否存在
    source_model = db.query(BusinessModel).filter(
        BusinessModel.id == source_model_id
    ).first()
    if not source_model:
        raise HTTPException(
            status_code=404,
            detail=f"源对象类型 '{source_model_id}' 不存在"
        )
    
    target_model = db.query(BusinessModel).filter(
        BusinessModel.id == target_model_id
    ).first()
    if not target_model:
        raise HTTPException(
            status_code=404,
            detail=f"目标对象类型 '{target_model_id}' 不存在"
        )
    
    # 验证源字段和目标字段是否存在
    source_field = db.query(BusinessModelField).filter(
        BusinessModelField.model_id == source_model_id,
        BusinessModelField.field_id == source_key
    ).first()
    if not source_field:
        raise HTTPException(
            status_code=404,
            detail=f"源对象类型 '{source_model_id}' 中不存在字段 '{source_key}'"
        )
    
    target_field = db.query(BusinessModelField).filter(
        BusinessModelField.model_id == target_model_id,
        BusinessModelField.field_id == target_key
    ).first()
    if not target_field:
        raise HTTPException(
            status_code=404,
            detail=f"目标对象类型 '{target_model_id}' 中不存在字段 '{target_key}'"
        )
    
    # 验证基数
    valid_cardinalities = ["one-to-one", "one-to-many", "many-to-one", "many-to-many"]
    if cardinality not in valid_cardinalities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cardinality '{cardinality}'. Must be one of: {', '.join(valid_cardinalities)}"
        )
    
    # 验证主键约束
    if cardinality == "one-to-many":
        if source_model.primary_key_id != source_key:
            raise HTTPException(
                status_code=400,
                detail="For one-to-many relationship, the 'one' side (source) must use primary key"
            )
    elif cardinality == "many-to-one":
        if target_model.primary_key_id != target_key:
            raise HTTPException(
                status_code=400,
                detail="For many-to-one relationship, the 'one' side (target) must use primary key"
            )
    elif cardinality == "one-to-one":
        if (source_model.primary_key_id != source_key and 
            target_model.primary_key_id != target_key):
            raise HTTPException(
                status_code=400,
                detail="For one-to-one relationship, at least one side must use primary key"
            )
    elif cardinality == "many-to-many":
        if not intermediate_model_id or not intermediate_source_key or not intermediate_target_key:
            raise HTTPException(
                status_code=400,
                detail="For many-to-many relationship, intermediate model and keys are required"
            )
        
        # 验证中间模型
        intermediate_model = db.query(BusinessModel).filter(
            BusinessModel.id == intermediate_model_id
        ).first()
        if not intermediate_model:
            raise HTTPException(
                status_code=404,
                detail=f"中间对象类型 '{intermediate_model_id}' 不存在"
            )
        
        # 验证中间表字段
        intermediate_source_field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == intermediate_model_id,
            BusinessModelField.field_id == intermediate_source_key
        ).first()
        if not intermediate_source_field:
            raise HTTPException(
                status_code=404,
                detail=f"中间对象类型中不存在字段 '{intermediate_source_key}'"
            )
        
        intermediate_target_field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == intermediate_model_id,
            BusinessModelField.field_id == intermediate_target_key
        ).first()
        if not intermediate_target_field:
            raise HTTPException(
                status_code=404,
                detail=f"中间对象类型中不存在字段 '{intermediate_target_key}'"
            )
        
        # 验证中间表字段引用主键
        if source_model.primary_key_id != source_key:
            raise HTTPException(
                status_code=400,
                detail="For many-to-many relationship, source key must be the primary key of source model"
            )
        if target_model.primary_key_id != target_key:
            raise HTTPException(
                status_code=400,
                detail="For many-to-many relationship, target key must be the primary key of target model"
            )


# ==================== 关系类型 CRUD 工具 ====================

@router.get(
    "/list_link_types",
    operation_id="list_link_types",
    summary="列出所有关系类型",
    description="""
获取所有关系类型的列表。
支持按源对象类型或目标对象类型过滤。

适用于了解当前有哪些关系可用。
    """,
    response_description="关系类型列表"
)
def list_link_types(
    source_object_type_id: Optional[str] = Query(None, description="按源对象类型ID过滤"),
    target_object_type_id: Optional[str] = Query(None, description="按目标对象类型ID过滤"),
    db: Session = Depends(get_db)
):
    """列出所有关系类型"""
    try:
        query = db.query(BusinessModelLink)
        
        if source_object_type_id:
            query = query.filter(BusinessModelLink.source_model == source_object_type_id)
        if target_object_type_id:
            query = query.filter(BusinessModelLink.target_model == target_object_type_id)
        
        links = query.all()
        
        return [
            {
                "link_type_id": link.id,
                "link_type_name": link.name,
                "description": link.description or "",
                "source_object_type_id": link.source_model,
                "target_object_type_id": link.target_model,
                "cardinality": link.cardinality,
                "source_key": link.source_key,
                "target_key": link.target_key
            }
            for link in links
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"列出关系类型失败: {str(e)}"
        )


@router.get(
    "/get_link_type/{link_type_id}",
    operation_id="get_link_type",
    summary="获取关系类型详情",
    description="""
获取单个关系类型的完整管理视图，包括:
- 基本信息（ID、名称、描述）
- 源对象类型和目标对象类型信息
- 基数类型
- 中间对象类型信息（many-to-many）
- 完整性检查结果

适用于查看关系类型的完整结构。
    """,
    response_description="关系类型的完整管理信息"
)
def get_link_type(
    link_type_id: str,
    db: Session = Depends(get_db)
):
    """获取关系类型详情"""
    try:
        link = db.query(BusinessModelLink).filter(
            BusinessModelLink.id == link_type_id
        ).first()
        
        if not link:
            raise HTTPException(
                status_code=404,
                detail=f"关系类型 '{link_type_id}' 不存在"
            )
        
        # 获取源模型和目标模型
        source_model = db.query(BusinessModel).filter(
            BusinessModel.id == link.source_model
        ).first()
        target_model = db.query(BusinessModel).filter(
            BusinessModel.id == link.target_model
        ).first()
        
        result = {
            "link_type_id": link.id,
            "link_type_name": link.name,
            "description": link.description or "",
            "source_object_type_id": link.source_model,
            "source_object_type_name": source_model.name if source_model else None,
            "source_key": link.source_key,
            "target_object_type_id": link.target_model,
            "target_object_type_name": target_model.name if target_model else None,
            "target_key": link.target_key,
            "cardinality": link.cardinality,
            "management_info": {
                "is_valid": True,
                "warnings": []
            }
        }
        
        # many-to-many 添加中间表信息
        if link.cardinality == "many-to-many" and link.intermediate_model:
            intermediate_model = db.query(BusinessModel).filter(
                BusinessModel.id == link.intermediate_model
            ).first()
            result["intermediate_object_type_id"] = link.intermediate_model
            result["intermediate_object_type_name"] = intermediate_model.name if intermediate_model else None
            result["intermediate_source_key"] = link.intermediate_source_key
            result["intermediate_target_key"] = link.intermediate_target_key
        
        # 语义验证
        semantic_validation = SemanticValidator.validate_link_type_semantics(db, link_type_id)
        result["semantic_validation"] = semantic_validation
        
        # 推荐操作
        if semantic_validation.get("valid", False):
            result["next_recommended_actions"] = [
                "get_link_type: 验证关系配置",
                "create_action_type: 为此关系创建操作Action"
            ]
        else:
            result["next_recommended_actions"] = [
                "update_link_type: 修复语义验证发现的问题"
            ]
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取关系类型失败: {str(e)}"
        )


@router.post(
    "/create_link_type",
    operation_id="create_link_type",
    summary="创建关系类型",
    description="""
创建新的关系类型。

**验证规则**:
- 源/目标对象类型必须存在
- 源/目标对象类型字段必须存在
- 基数约束（主键检查）
- many-to-many 需要中间对象类型信息

**支持功能**:
- 详细的错误信息，帮助用户理解问题
- 建议在创建前使用 validate_link_type_compatibility 工具
    """,
    response_description="创建的关系类型信息"
)
def create_link_type(
    parameters: CreateLinkTypeParameters,
    db: Session = Depends(get_db)
):
    """创建关系类型"""
    try:
        # 检查 ID 是否已存在
        existing = db.query(BusinessModelLink).filter(
            BusinessModelLink.id == parameters.link_type_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"关系类型 ID '{parameters.link_type_id}' 已存在"
            )
        
        # 验证约束
        _validate_link_constraints(
            db,
            parameters.source_object_type_id,
            parameters.source_key,
            parameters.target_object_type_id,
            parameters.target_key,
            parameters.cardinality,
            parameters.intermediate_object_type_id,
            parameters.intermediate_source_key,
            parameters.intermediate_target_key
        )
        
        # 创建关系
        link = BusinessModelLink(
            id=parameters.link_type_id,
            name=parameters.link_type_name,
            description=parameters.description,
            source_model=parameters.source_object_type_id,
            source_key=parameters.source_key,
            target_model=parameters.target_object_type_id,
            target_key=parameters.target_key,
            cardinality=parameters.cardinality,
            intermediate_model=parameters.intermediate_object_type_id,
            intermediate_source_key=parameters.intermediate_source_key,
            intermediate_target_key=parameters.intermediate_target_key
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        
        return {
            "link_type_id": link.id,
            "link_type_name": link.name,
            "source_object_type_id": link.source_model,
            "target_object_type_id": link.target_model,
            "cardinality": link.cardinality,
            "message": f"关系类型 '{parameters.link_type_id}' 创建成功"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"创建关系类型失败: {str(e)}"
        )


@router.put(
    "/update_link_type/{link_type_id}",
    operation_id="update_link_type",
    summary="更新关系类型",
    description="""
更新关系类型的定义。

**注意**:
- 更新会重新验证所有约束
- 如果修改了源/目标对象类型或字段，需要确保新值有效
    """,
    response_description="更新后的关系类型信息"
)
def update_link_type(
    link_type_id: str,
    parameters: UpdateLinkTypeParameters,
    db: Session = Depends(get_db)
):
    """更新关系类型"""
    try:
        link = db.query(BusinessModelLink).filter(
            BusinessModelLink.id == link_type_id
        ).first()
        
        if not link:
            raise HTTPException(
                status_code=404,
                detail=f"关系类型 '{link_type_id}' 不存在"
            )
        
        # 获取更新后的值
        source_model = parameters.source_object_type_id or link.source_model
        source_key = parameters.source_key or link.source_key
        target_model = parameters.target_object_type_id or link.target_model
        target_key = parameters.target_key or link.target_key
        cardinality = parameters.cardinality or link.cardinality
        intermediate_model = parameters.intermediate_object_type_id or link.intermediate_model
        intermediate_source_key = parameters.intermediate_source_key or link.intermediate_source_key
        intermediate_target_key = parameters.intermediate_target_key or link.intermediate_target_key
        
        # 验证约束
        _validate_link_constraints(
            db,
            source_model,
            source_key,
            target_model,
            target_key,
            cardinality,
            intermediate_model,
            intermediate_source_key,
            intermediate_target_key
        )
        
        # 更新字段
        if parameters.link_type_name:
            link.name = parameters.link_type_name
        if parameters.description is not None:
            link.description = parameters.description
        if parameters.source_object_type_id:
            link.source_model = parameters.source_object_type_id
        if parameters.source_key:
            link.source_key = parameters.source_key
        if parameters.target_object_type_id:
            link.target_model = parameters.target_object_type_id
        if parameters.target_key:
            link.target_key = parameters.target_key
        if parameters.cardinality:
            link.cardinality = parameters.cardinality
        if parameters.intermediate_object_type_id:
            link.intermediate_model = parameters.intermediate_object_type_id
        if parameters.intermediate_source_key:
            link.intermediate_source_key = parameters.intermediate_source_key
        if parameters.intermediate_target_key:
            link.intermediate_target_key = parameters.intermediate_target_key
        
        db.commit()
        db.refresh(link)
        
        return {
            "link_type_id": link.id,
            "link_type_name": link.name,
            "message": f"关系类型 '{link_type_id}' 更新成功"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"更新关系类型失败: {str(e)}"
        )


@router.delete(
    "/delete_link_type/{link_type_id}",
    operation_id="delete_link_type",
    summary="删除关系类型",
    description="""
删除关系类型。

**注意**:
- 删除操作不可恢复
- 不会影响源对象类型和目标对象类型
    """,
    response_description="删除结果"
)
def delete_link_type(
    link_type_id: str,
    db: Session = Depends(get_db)
):
    """删除关系类型"""
    try:
        link = db.query(BusinessModelLink).filter(
            BusinessModelLink.id == link_type_id
        ).first()
        
        if not link:
            raise HTTPException(
                status_code=404,
                detail=f"关系类型 '{link_type_id}' 不存在"
            )
        
        db.delete(link)
        db.commit()
        
        return {
            "message": f"关系类型 '{link_type_id}' 删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除关系类型失败: {str(e)}"
        )


@router.post(
    "/validate_link_type_compatibility",
    operation_id="validate_link_type_compatibility",
    summary="验证关系类型兼容性",
    description="""
在创建关系类型前验证源/目标对象类型和字段的兼容性。

**支持功能**:
- 不创建实际关系，仅验证
- 返回详细的错误列表和建议
- 帮助在创建前发现问题

**使用场景**:
- 准备创建关系类型前预检查
- 调试关系类型配置问题
    """,
    response_description="验证结果"
)
def validate_link_type_compatibility(
    validation_request: Dict,
    db: Session = Depends(get_db)
):
    """验证关系兼容性"""
    try:
        source_object_type_id = validation_request.get("source_object_type_id")
        source_key = validation_request.get("source_key")
        target_object_type_id = validation_request.get("target_object_type_id")
        target_key = validation_request.get("target_key")
        cardinality = validation_request.get("cardinality")
        intermediate_object_type_id = validation_request.get("intermediate_object_type_id")
        intermediate_source_key = validation_request.get("intermediate_source_key")
        intermediate_target_key = validation_request.get("intermediate_target_key")
        
        errors = []
        warnings = []
        suggestions = []
        
        # 验证必填字段
        if not all([source_object_type_id, source_key, target_object_type_id, target_key, cardinality]):
            errors.append("Missing required fields: source_object_type_id, source_key, target_object_type_id, target_key, cardinality")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions
            }
        
        try:
            # 尝试验证约束
            _validate_link_constraints(
                db,
                source_object_type_id,
                source_key,
                target_object_type_id,
                target_key,
                cardinality,
                intermediate_object_type_id,
                intermediate_source_key,
                intermediate_target_key
            )
            
            # 检查是否已存在相同关系
            existing = db.query(BusinessModelLink).filter(
                BusinessModelLink.source_model == source_object_type_id,
                BusinessModelLink.target_model == target_object_type_id,
                BusinessModelLink.source_key == source_key,
                BusinessModelLink.target_key == target_key
            ).first()
            
            if existing:
                warnings.append(f"A similar link already exists: '{existing.id}'")
                suggestions.append("Consider using the existing link or choose a different ID")
            
            return {
                "valid": True,
                "errors": [],
                "warnings": warnings,
                "suggestions": suggestions
            }
            
        except HTTPException as e:
            errors.append(str(e.detail))
            
            # 提供建议
            if "not found" in str(e.detail).lower():
                suggestions.append("Create the missing model or field first")
            elif "primary key" in str(e.detail).lower():
                suggestions.append("Ensure the 'one' side uses the primary key field")
            elif "intermediate" in str(e.detail).lower():
                suggestions.append("For many-to-many, provide intermediate_model, intermediate_source_key, and intermediate_target_key")
            
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate link compatibility: {str(e)}"
        )
