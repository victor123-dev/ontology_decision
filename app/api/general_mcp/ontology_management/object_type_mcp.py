"""对象类型管理模块 - Ontology Management MCP
提供 BusinessModel 和 BusinessModelField 的完整 CRUD 操作
支持批量操作和事务性保证
集成语义一致性验证和 Agent 辅助功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from app.models.business_model import BusinessModel, BusinessModelField
from app.models.business_model_link import BusinessModelLink
from app.utils.shared_utils import get_db
from .semantic_validator import SemanticValidator
from .agent_helper import AgentHelper

router = APIRouter()

# ==================== Pydantic 模型定义 ====================

class FieldDefinition(BaseModel):
    """字段定义模型"""
    field_id: str = Field(description="字段唯一标识符，建议使用snake_case命名")
    name: str = Field(description="字段中文名称")
    description: Optional[str] = Field(default=None, description="字段描述")
    data_type: str = Field(
        description="字段数据类型: string, text, integer, float, boolean, object, array, date, datetime"
    )
    required: bool = Field(default=False, description="是否必填")
    is_enum: bool = Field(default=False, description="是否为枚举类型")
    enum_values: Optional[List[str]] = Field(
        default=None, 
        description="枚举值列表（仅当is_enum=True时有效）"
    )


class CreateObjectTypeParameters(BaseModel):
    """创建对象类型参数"""
    object_type_id: str = Field(description="对象类型唯一标识符，建议使用snake_case命名")
    object_type_name: str = Field(description="对象类型中文名称")
    description: Optional[str] = Field(default=None, description="对象类型描述")
    primary_key_id: str = Field(description="主键字段ID，必须在fields中定义")
    data_source_id: Optional[str] = Field(default=None, description="数据源ID")
    fields: List[FieldDefinition] = Field(
        default=[],
        description="字段列表。建议至少包含主键字段和其他必要字段"
    )


class UpdateObjectTypeParameters(BaseModel):
    """更新对象类型参数"""
    object_type_name: Optional[str] = Field(default=None, description="对象类型中文名称")
    description: Optional[str] = Field(default=None, description="对象类型描述")
    primary_key_id: Optional[str] = Field(default=None, description="主键字段ID")
    fields_to_add: Optional[List[FieldDefinition]] = Field(
        default=None, 
        description="新增字段列表"
    )
    fields_to_update: Optional[Dict[str, FieldDefinition]] = Field(
        default=None, 
        description="更新字段字典，key为field_id"
    )
    fields_to_delete: Optional[List[str]] = Field(
        default=None, 
        description="删除字段ID列表"
    )


# ==================== 允许的字段类型 ====================

ALLOWED_DATA_TYPES = {
    'string', 'text', 'integer', 'float', 
    'boolean', 'object', 'array', 'date', 'datetime'
}


def _validate_data_type(data_type: str):
    """校验字段类型是否在允许的范围内"""
    if data_type and data_type.lower() not in ALLOWED_DATA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的字段类型: '{data_type}'。允许的类型为: {', '.join(sorted(ALLOWED_DATA_TYPES))}"
        )


def _generate_recommended_actions(
    model: BusinessModel,
    links: List[Dict],
    semantic_validation: Dict
) -> List[str]:
    """
    生成推荐的下一步操作
    
    Args:
        model: 业务模型对象
        links: 关联关系列表
        semantic_validation: 语义验证结果
        
    Returns:
        推荐操作列表
    """
    actions = []
    
    # 如果没有关系，建议创建
    if len(links) == 0:
        actions.append("create_link_type: 建立与其他对象的关系以提升连通性")
    
    # 如果字段较少，建议添加
    if len(model.fields or []) < 3:
        actions.append("update_object_type: 添加更多字段以完善数据模型")
    
    # 如果语义验证有问题，建议修复
    if semantic_validation.get("issues"):
        issue_count = len(semantic_validation["issues"])
        actions.append(f"update_object_type: 修复语义验证发现的 {issue_count} 个问题")
    
    # 如果合规分数较低，建议优化
    if semantic_validation.get("compliance_score", 100) < 70:
        actions.append("update_object_type: 优化命名规范和字段定义以提高合规分数")
    
    # 如果没有问题，给予肯定
    if not actions:
        actions.append("本体结构良好，可考虑创建实例数据或为此对象创建 Action")
    
    return actions


# ==================== 对象类型 CRUD 工具 ====================

@router.get(
    "/list_object_types",
    operation_id="list_object_types",
    summary="列出所有对象类型",
    description="""
获取所有对象类型的列表，包含基本信息和统计信息。
支持按数据源过滤。

适用于了解当前有哪些对象类型可用。
    """,
    response_description="对象类型列表"
)
def list_object_types(
    data_source_id: Optional[str] = Query(
        None, 
        description="按数据源ID过滤"
    ),
    db: Session = Depends(get_db)
):
    """列出所有对象类型"""
    try:
        query = db.query(BusinessModel)
        if data_source_id:
            query = query.filter(BusinessModel.data_source_id == data_source_id)
        
        models = query.all()
        
        return [
            {
                "object_type_id": model.id,
                "object_type_name": model.name,
                "description": model.description or "",
                "primary_key_id": model.primary_key_id,
                "data_source_id": model.data_source_id,
                "fields_count": len(model.fields) if model.fields else 0
            }
            for model in models
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"列出对象类型失败: {str(e)}"
        )


@router.get(
    "/get_object_type/{object_type_id}",
    operation_id="get_object_type",
    summary="获取对象类型详情",
    description="""
获取单个对象类型的完整管理视图，包括:
- 基本信息（ID、名称、描述）
- 完整字段列表（含类型、是否必填、枚举值）
- 关联的关系类型（作为源或目标）
- 关联的行动类型
- 依赖分析（删除前需要检查的内容）

适用于 Agent 查看对象类型的完整结构，评估是否可以删除或需要修改。
    """,
    response_description="对象类型的完整管理信息"
)
def get_object_type(
    object_type_id: str,
    db: Session = Depends(get_db)
):
    """获取对象类型详情（管理视图）"""
    try:
        # 获取业务模型
        business_model = db.query(BusinessModel).options(
            joinedload(BusinessModel.fields)
        ).filter(BusinessModel.id == object_type_id).first()
        
        if not business_model:
            raise HTTPException(
                status_code=404,
                detail=f"对象类型 '{object_type_id}' 不存在"
            )
        
        # 获取关联的关系类型
        source_links = db.query(BusinessModelLink).filter(
            BusinessModelLink.source_model == object_type_id
        ).all()
        target_links = db.query(BusinessModelLink).filter(
            BusinessModelLink.target_model == object_type_id
        ).all()
        
        links_info = []
        for link in source_links + target_links:
            links_info.append({
                "link_type_id": link.id,
                "link_type_name": link.name,
                "description": link.description or "",
                "direction": "source" if link.source_model == object_type_id else "target",
                "cardinality": link.cardinality,
                "other_object_type_id": link.target_model if link.source_model == object_type_id else link.source_model
            })
        
        # 构建响应
        # 语义验证
        semantic_validation = SemanticValidator.validate_object_type_semantics(db, object_type_id)
        
        # 生成推荐的下一步操作
        next_recommended_actions = _generate_recommended_actions(
            business_model, links_info, semantic_validation
        )
        
        return {
            "object_type_id": business_model.id,
            "object_type_name": business_model.name,
            "description": business_model.description or "",
            "primary_key_id": business_model.primary_key_id,
            "data_source_id": business_model.data_source_id,
            "fields": [
                {
                    "field_id": field.field_id,
                    "name": field.name,
                    "description": field.description or "",
                    "data_type": field.data_type,
                    "required": field.required,
                    "is_enum": field.is_enum,
                    "enum_values": field.enum_values
                }
                for field in (business_model.fields or [])
            ],
            "links": links_info,
            "management_info": {
                "fields_count": len(business_model.fields) if business_model.fields else 0,
                "links_count": len(links_info),
                "can_delete": len(links_info) == 0,
                "warnings": [
                    f"该对象类型有 {len(links_info)} 个关联关系类型，删除前需要先处理这些关系类型"
                ] if links_info else []
            },
            "semantic_validation": semantic_validation,
            "next_recommended_actions": next_recommended_actions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取对象类型失败: {str(e)}"
        )


@router.post(
    "/create_object_type",
    operation_id="create_object_type",
    summary="创建对象类型",
    description="""
创建新的对象类型，支持一次性创建所有字段。

**支持功能**:
- 支持在创建对象类型时同时定义所有字段
- 自动验证字段类型和主键约束
- 事务性保证：如果任何字段创建失败，整个操作回滚

**使用场景**:
- 根据业务需求创建新的本体模型
- 批量导入本体结构
    """,
    response_description="创建的对象类型信息"
)
def create_object_type(
    parameters: CreateObjectTypeParameters,
    db: Session = Depends(get_db)
):
    """创建对象类型（支持批量字段）"""
    try:
        # 检查 ID 是否已存在
        existing = db.query(BusinessModel).filter(
            BusinessModel.id == parameters.object_type_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"对象类型 ID '{parameters.object_type_id}' 已存在"
            )
        
        # 验证主键字段是否在 fields 中
        if parameters.fields:
            field_ids = [f.field_id for f in parameters.fields]
            if parameters.primary_key_id not in field_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"主键字段 '{parameters.primary_key_id}' 必须在 fields 中定义"
                )
        
        # 创建业务模型
        business_model = BusinessModel(
            id=parameters.object_type_id,
            name=parameters.object_type_name,
            description=parameters.description,
            primary_key_id=parameters.primary_key_id,
            data_source_id=parameters.data_source_id
        )
        db.add(business_model)
        
        # 创建字段
        if parameters.fields:
            for field_def in parameters.fields:
                # 验证字段类型
                _validate_data_type(field_def.data_type)
                
                # 检查字段 ID 是否重复
                if field_def.field_id in [f.field_id for f in parameters.fields if f != field_def]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"字段列表中存在重复的字段 ID '{field_def.field_id}'"
                    )
                
                field = BusinessModelField(
                    model_id=parameters.object_type_id,
                    field_id=field_def.field_id,
                    name=field_def.name,
                    description=field_def.description or "",
                    data_type=field_def.data_type,
                    required=field_def.required,
                    is_enum=field_def.is_enum,
                    enum_values=field_def.enum_values if field_def.is_enum else None
                )
                db.add(field)
        
        # 提交事务
        db.commit()
        db.refresh(business_model)
        
        return {
            "object_type_id": business_model.id,
            "object_type_name": business_model.name,
            "description": business_model.description,
            "primary_key_id": business_model.primary_key_id,
            "data_source_id": business_model.data_source_id,
            "fields_count": len(parameters.fields),
            "message": f"对象类型 '{parameters.object_type_id}' 创建成功，包含 {len(parameters.fields)} 个字段"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"创建对象类型失败: {str(e)}"
        )


@router.put(
    "/update_object_type/{object_type_id}",
    operation_id="update_object_type",
    summary="更新对象类型",
    description="""
更新对象类型的基本信息和字段。

**支持功能**:
- 支持同时更新对象类型信息和增删改字段
- 事务性保证：所有操作在同一事务中完成
- 验证字段类型和主键约束

**使用场景**:
- 添加新字段到现有模型
- 修改字段定义（类型、描述、枚举值）
- 删除不再需要的字段
- 修改主键字段
    """,
    response_description="更新后的对象类型信息"
)
def update_object_type(
    object_type_id: str,
    parameters: UpdateObjectTypeParameters,
    db: Session = Depends(get_db)
):
    """更新对象类型（支持字段增删改）"""
    try:
        # 获取业务模型
        business_model = db.query(BusinessModel).options(
            joinedload(BusinessModel.fields)
        ).filter(BusinessModel.id == object_type_id).first()
        
        if not business_model:
            raise HTTPException(
                status_code=404,
                detail=f"对象类型 '{object_type_id}' 不存在"
            )
        
        # 更新基本信息
        if parameters.object_type_name:
            business_model.name = parameters.object_type_name
        if parameters.description is not None:
            business_model.description = parameters.description
        if parameters.primary_key_id:
            business_model.primary_key_id = parameters.primary_key_id
        
        # 新增字段
        if parameters.fields_to_add:
            existing_field_ids = {f.field_id for f in business_model.fields} if business_model.fields else set()
            
            for field_def in parameters.fields_to_add:
                if field_def.field_id in existing_field_ids:
                    raise HTTPException(
                        status_code=400,
                        detail=f"字段 '{field_def.field_id}' 已存在"
                    )
                
                _validate_data_type(field_def.data_type)
                
                field = BusinessModelField(
                    model_id=object_type_id,
                    field_id=field_def.field_id,
                    name=field_def.name,
                    description=field_def.description or "",
                    data_type=field_def.data_type,
                    required=field_def.required,
                    is_enum=field_def.is_enum,
                    enum_values=field_def.enum_values if field_def.is_enum else None
                )
                db.add(field)
        
        # 更新字段
        if parameters.fields_to_update:
            for field_id, field_def in parameters.fields_to_update.items():
                field = db.query(BusinessModelField).filter(
                    BusinessModelField.model_id == object_type_id,
                    BusinessModelField.field_id == field_id
                ).first()
                
                if not field:
                    raise HTTPException(
                        status_code=404,
                        detail=f"字段 '{field_id}' 不存在"
                    )
                
                _validate_data_type(field_def.data_type)
                
                if field_def.name:
                    field.name = field_def.name
                if field_def.description is not None:
                    field.description = field_def.description
                field.data_type = field_def.data_type
                if field_def.required is not None:
                    field.required = field_def.required
                if field_def.is_enum is not None:
                    field.is_enum = field_def.is_enum
                    if field_def.is_enum and field_def.enum_values:
                        field.enum_values = field_def.enum_values
                    else:
                        field.enum_values = None
        
        # 删除字段
        if parameters.fields_to_delete:
            # 检查是否要删除主键字段
            if business_model.primary_key_id in parameters.fields_to_delete:
                raise HTTPException(
                    status_code=400,
                    detail=f"不能删除主键字段 '{business_model.primary_key_id}'"
                )
            
            for field_id in parameters.fields_to_delete:
                field = db.query(BusinessModelField).filter(
                    BusinessModelField.model_id == object_type_id,
                    BusinessModelField.field_id == field_id
                ).first()
                
                if not field:
                    raise HTTPException(
                        status_code=404,
                        detail=f"字段 '{field_id}' 不存在"
                    )
                
                db.delete(field)
        
        # 提交事务
        db.commit()
        db.refresh(business_model)
        
        return {
            "object_type_id": business_model.id,
            "object_type_name": business_model.name,
            "description": business_model.description,
            "primary_key_id": business_model.primary_key_id,
            "fields_count": len(business_model.fields) if business_model.fields else 0,
            "message": f"对象类型 '{object_type_id}' 更新成功"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"更新对象类型失败: {str(e)}"
        )


@router.delete(
    "/delete_object_type/{object_type_id}",
    operation_id="delete_object_type",
    summary="删除对象类型",
    description="""
删除对象类型及其所有字段。

**注意**:
- 如果该对象有关联的关系类型，需要先删除这些关系
- 删除操作不可恢复，请谨慎操作

适用于清理不再需要的本体模型。
    """,
    response_description="删除结果"
)
def delete_object_type(
    object_type_id: str,
    db: Session = Depends(get_db)
):
    """删除对象类型"""
    try:
        # 获取业务模型
        business_model = db.query(BusinessModel).filter(
            BusinessModel.id == object_type_id
        ).first()
        
        if not business_model:
            raise HTTPException(
                status_code=404,
                detail=f"对象类型 '{object_type_id}' 不存在"
            )
        
        # 检查是否有关联关系
        dependent_links = db.query(BusinessModelLink).filter(
            (BusinessModelLink.source_model == object_type_id) |
            (BusinessModelLink.target_model == object_type_id)
        ).count()
        
        if dependent_links > 0:
            raise HTTPException(
                status_code=400,
                detail=f"无法删除对象类型 '{object_type_id}': 存在 {dependent_links} 个关联的关系类型，请先删除这些关系类型"
            )
        
        # 删除模型（会级联删除字段）
        db.delete(business_model)
        db.commit()
        
        return {
            "message": f"对象类型 '{object_type_id}' 删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除对象类型失败: {str(e)}"
        )


# ==================== 字段管理工具 ====================

@router.post(
    "/create_object_field/{object_type_id}",
    operation_id="create_object_field",
    summary="创建对象字段",
    description="""
为现有对象类型添加单个字段。

**注意**: 推荐使用 create_object_type 或 update_object_type 批量操作字段，
此工具仅用于单独添加单个字段的场景。
    """,
    response_description="创建的字段信息"
)
def create_object_field(
    object_type_id: str,
    field_def: FieldDefinition,
    db: Session = Depends(get_db)
):
    """创建单个对象字段"""
    try:
        # 检查模型是否存在
        business_model = db.query(BusinessModel).filter(
            BusinessModel.id == object_type_id
        ).first()
        if not business_model:
            raise HTTPException(
                status_code=404,
                detail=f"对象类型 '{object_type_id}' 不存在"
            )
        
        # 检查字段 ID 是否已存在
        existing_field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == object_type_id,
            BusinessModelField.field_id == field_def.field_id
        ).first()
        if existing_field:
            raise HTTPException(
                status_code=400,
                detail=f"字段 '{field_def.field_id}' 已存在"
            )
        
        # 验证字段类型
        _validate_data_type(field_def.data_type)
        
        # 创建字段
        field = BusinessModelField(
            model_id=object_type_id,
            field_id=field_def.field_id,
            name=field_def.name,
            description=field_def.description or "",
            data_type=field_def.data_type,
            required=field_def.required,
            is_enum=field_def.is_enum,
            enum_values=field_def.enum_values if field_def.is_enum else None
        )
        db.add(field)
        db.commit()
        db.refresh(field)
        
        return {
            "field_id": field.field_id,
            "name": field.name,
            "data_type": field.data_type,
            "message": f"字段 '{field_def.field_id}' 创建成功"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"创建字段失败: {str(e)}"
        )


@router.put(
    "/update_object_field/{object_type_id}/{field_id}",
    operation_id="update_object_field",
    summary="更新对象字段",
    description="""
更新对象类型中的单个字段定义。

**注意**: 推荐使用 update_object_type 批量更新字段。
    """,
    response_description="更新后的字段信息"
)
def update_object_field(
    object_type_id: str,
    field_id: str,
    field_def: FieldDefinition,
    db: Session = Depends(get_db)
):
    """更新单个对象字段"""
    try:
        # 检查模型和字段是否存在
        business_model = db.query(BusinessModel).filter(
            BusinessModel.id == object_type_id
        ).first()
        if not business_model:
            raise HTTPException(
                status_code=404,
                detail=f"Object type '{object_type_id}' not found"
            )
        
        field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == object_type_id,
            BusinessModelField.field_id == field_id
        ).first()
        if not field:
            raise HTTPException(
                status_code=404,
                detail=f"Field '{field_id}' not found"
            )
        
        # 验证字段类型
        _validate_data_type(field_def.data_type)
        
        # 更新字段
        field.name = field_def.name
        field.description = field_def.description or ""
        field.data_type = field_def.data_type
        field.required = field_def.required
        field.is_enum = field_def.is_enum
        field.enum_values = field_def.enum_values if field_def.is_enum else None
        
        db.commit()
        db.refresh(field)
        
        return {
            "field_id": field.field_id,
            "name": field.name,
            "data_type": field.data_type,
            "message": f"字段 '{field_id}' 更新成功"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"更新字段失败: {str(e)}"
        )


@router.delete(
    "/delete_object_field/{object_type_id}/{field_id}",
    operation_id="delete_object_field",
    summary="删除对象字段",
    description="""
删除对象类型中的单个字段。

**注意**:
- 不能删除主键字段
- 删除操作不可恢复

推荐使用 update_object_type 批量删除字段。
    """,
    response_description="删除结果"
)
def delete_object_field(
    object_type_id: str,
    field_id: str,
    db: Session = Depends(get_db)
):
    """删除单个对象字段"""
    try:
        # 检查模型和字段是否存在
        business_model = db.query(BusinessModel).filter(
            BusinessModel.id == object_type_id
        ).first()
        if not business_model:
            raise HTTPException(
                status_code=404,
                detail=f"Object type '{object_type_id}' not found"
            )
        
        # 检查是否为主键字段
        if business_model.primary_key_id == field_id:
            raise HTTPException(
                status_code=400,
                detail=f"不能删除主键字段 '{field_id}'"
            )
        
        field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == object_type_id,
            BusinessModelField.field_id == field_id
        ).first()
        if not field:
            raise HTTPException(
                status_code=404,
                detail=f"字段 '{field_id}' 不存在"
            )
        
        # 删除字段
        db.delete(field)
        db.commit()
        
        return {
            "message": f"字段 '{field_id}' 删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除字段失败: {str(e)}"
        )


@router.post(
    "/batch_update_fields/{object_type_id}",
    operation_id="batch_update_fields",
    summary="批量更新字段",
    description="""
批量更新对象类型的字段（增删改一次完成）。

**支持功能**:
- 一次调用完成多个字段的增删改
- 事务性保证：所有操作在同一事务中完成
- 自动验证所有字段类型

**使用场景**:
- 根据业务变更批量调整模型结构
- 导入新的字段定义
- 清理不需要的字段
    """,
    response_description="批量更新结果"
)
def batch_update_fields(
    object_type_id: str,
    operations: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """批量更新字段"""
    try:
        # 获取模型
        business_model = db.query(BusinessModel).filter(
            BusinessModel.id == object_type_id
        ).first()
        if not business_model:
            raise HTTPException(
                status_code=404,
                detail=f"Object type '{object_type_id}' not found"
            )
        
        results = {"added": [], "updated": [], "deleted": []}
        
        # 新增字段
        if "add" in operations and operations["add"]:
            for field_def_dict in operations["add"]:
                field_def = FieldDefinition(**field_def_dict)
                
                # 检查字段是否已存在
                existing = db.query(BusinessModelField).filter(
                    BusinessModelField.model_id == object_type_id,
                    BusinessModelField.field_id == field_def.field_id
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field '{field_def.field_id}' already exists"
                    )
                
                _validate_data_type(field_def.data_type)
                
                field = BusinessModelField(
                    model_id=object_type_id,
                    field_id=field_def.field_id,
                    name=field_def.name,
                    description=field_def.description or "",
                    data_type=field_def.data_type,
                    required=field_def.required,
                    is_enum=field_def.is_enum,
                    enum_values=field_def.enum_values if field_def.is_enum else None
                )
                db.add(field)
                results["added"].append(field_def.field_id)
        
        # 更新字段
        if "update" in operations and operations["update"]:
            for field_id, field_def_dict in operations["update"].items():
                field_def = FieldDefinition(**field_def_dict)
                
                field = db.query(BusinessModelField).filter(
                    BusinessModelField.model_id == object_type_id,
                    BusinessModelField.field_id == field_id
                ).first()
                if not field:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Field '{field_id}' not found"
                    )
                
                _validate_data_type(field_def.data_type)
                
                field.name = field_def.name
                field.description = field_def.description or ""
                field.data_type = field_def.data_type
                field.required = field_def.required
                field.is_enum = field_def.is_enum
                field.enum_values = field_def.enum_values if field_def.is_enum else None
                
                results["updated"].append(field_id)
        
        # 删除字段
        if "delete" in operations and operations["delete"]:
            for field_id in operations["delete"]:
                # 检查是否为主键
                if business_model.primary_key_id == field_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete primary key field '{field_id}'"
                    )
                
                field = db.query(BusinessModelField).filter(
                    BusinessModelField.model_id == object_type_id,
                    BusinessModelField.field_id == field_id
                ).first()
                if not field:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Field '{field_id}' not found"
                    )
                
                db.delete(field)
                results["deleted"].append(field_id)
        
        # 提交事务
        db.commit()
        
        return {
            "message": f"批量更新完成: 新增 {len(results['added'])} 个字段，更新 {len(results['updated'])} 个字段，删除 {len(results['deleted'])} 个字段",
            "results": results
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"批量更新字段失败: {str(e)}"
        )
