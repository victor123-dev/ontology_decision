"""
MCP工具模块 - 本体相关功能
提供对本体（ontology）的相关的操作能力，包括元数据查询
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session, joinedload
from app.models.business_model import BusinessModel
from app.models.business_model_link import BusinessModelLink
from app.utils.shared_utils import get_db
from app.dao.action_dao import get_action_dao

router = APIRouter()

@router.get(
    "/get_ontology_context", 
    operation_id="get_ontology_context",
    summary="获取本体上下文",
    description="""
    获取当前本体的精选上下文，以Markdown格式返回，便于Agent理解和使用。
    返回的内容包含三个主要部分：
    - 对象类型 (Objects): 所有业务模型的详细信息，包括字段定义
    - 关系类型 (Links): 所有业务模型关系的详细信息  
    - 动作类型 (Actions): 所有可执行动作的详细信息
    """,
    response_description="包含本体上下文的Markdown格式字符串"
)
def get_ontology_context(db: Session = Depends(get_db)):
    """
    获取当前本体的精选上下文，以Agent友好的Markdown格式返回
    
    Returns:
        Markdown格式的本体上下文字符串
    """
    try:
        # 构建Markdown内容
        markdown_parts = []
        markdown_parts.append("## 本体上下文\n")
        
        # 获取所有业务模型（对象）并预加载字段
        business_models = db.query(BusinessModel).options(
            joinedload(BusinessModel.fields)
        ).all()
        
        if business_models:
            markdown_parts.append("### 对象类型 (Objects)\n")
            for model in business_models:
                markdown_parts.append(f"#### {model.id}")
                markdown_parts.append(f"- **类型标识 (object_type_id)**: {model.id}")
                markdown_parts.append(f"- **类型名称 (object_type_name)**: {model.name}")
                markdown_parts.append(f"- **主键字段**: {model.primary_key_id or 'id'}")
                if model.description:
                    markdown_parts.append(f"- **描述**: {model.description}")
                else:
                    markdown_parts.append("- **描述**: 无")
                
                if model.fields:
                    markdown_parts.append("- **字段**:")
                    for field in sorted(model.fields, key=lambda x: x.field_id):
                        field_desc = f"{field.name} ({field.data_type})"
                        is_primary = " [主键]" if field.field_id == (model.primary_key_id ) else ""
                        markdown_parts.append(f"  - {field.field_id}: {field_desc}{is_primary}")
                else:
                    markdown_parts.append("- **字段**: 无")
                markdown_parts.append("")  # 空行分隔
        
        # 获取所有业务模型关系（链接）
        model_links = db.query(BusinessModelLink).all()
        if model_links:
            markdown_parts.append("### 关系类型 (Links)\n")
            for link in model_links:
                markdown_parts.append(f"#### {link.id}")
                markdown_parts.append(f"- **关系标识 (link_type_id)**: {link.id}")
                if link.description:
                    markdown_parts.append(f"- **描述**: {link.description}")
                else:
                    markdown_parts.append("- **描述**: 无")
                
                # 获取源模型和目标模型名称
                source_model = db.query(BusinessModel).filter(BusinessModel.id == link.source_model).first()
                target_model = db.query(BusinessModel).filter(BusinessModel.id == link.target_model).first()
                
                source_name = source_model.name if source_model else link.source_model
                target_name = target_model.name if target_model else link.target_model
                
                markdown_parts.append(f"- **源模型 (source)**: {link.source_model} ({source_name})")
                markdown_parts.append(f"- **目标模型 (target)**: {link.target_model} ({target_name})")
                
                # 基数映射
                cardinality_map = {
                    "one-to-one": "一对一",
                    "one-to-many": "一对多", 
                    "many-to-one": "多对一",
                    "many-to-many": "多对多"
                }
                cardinality_desc = cardinality_map.get(link.cardinality, link.cardinality)
                markdown_parts.append(f"- **基数**: {cardinality_desc}")
                
                # 添加查询示例
                markdown_parts.append("- **查询示例**:")
                markdown_parts.append(f"  - 正向查询: `query_objects_by_link(object_type_id: \"{link.source_model}\", object_ids: [...], link_type_id: \"{link.id}\")`")
                markdown_parts.append(f"  - 反向查询: `query_objects_by_link(object_type_id: \"{link.target_model}\", object_ids: [...], link_type_id: \"{link.id}\")`")
                markdown_parts.append("")  # 空行分隔
        
        # 获取所有行动
        action_dao = get_action_dao()
        actions = action_dao.get_actions()
        if actions:
            markdown_parts.append("### 动作类型 (Actions)\n")
            for action in actions:
                action_name = action.get("name", "Unnamed Action")
                markdown_parts.append(f"#### {action['id']}")
                markdown_parts.append(f"- **动作标识 (action_type_id)**: {action['id']}")
                markdown_parts.append(f"- **动作名称**: {action_name}")
                
                if action.get("description"):
                    markdown_parts.append(f"- **描述**: {action['description']}")
                else:
                    markdown_parts.append("- **描述**: 无")
                
                action_type_map = {
                    "object": "对象操作",
                    "link": "关系操作", 
                    "function": "自定义函数"
                }
                action_type_desc = action_type_map.get(action.get("action_type"), action.get("action_type", "未知"))
                markdown_parts.append(f"- **动作类型**: {action_type_desc}")
                
                if action.get("target_model_id"):
                    markdown_parts.append(f"- **目标模型**: {action['target_model_id']}")
                if action.get("target_link_id"):
                    markdown_parts.append(f"- **目标关系**: {action['target_link_id']}")
                
                # 操作类型
                operation_map = {
                    "create": "创建",
                    "update": "更新",
                    "delete": "删除", 
                    "custom": "自定义"
                }
                if action.get("operation"):
                    operation_desc = operation_map.get(action["operation"], action["operation"])
                    markdown_parts.append(f"- **操作**: {operation_desc}")
                
                markdown_parts.append("")  # 空行分隔
        
        # 移除最后一个空行（如果存在）
        if markdown_parts and markdown_parts[-1] == "":
            markdown_parts.pop()
            
        return "\n".join(markdown_parts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ontology context: {str(e)}")

@router.get(
    "/search_ontology", 
    operation_id="search_ontology",
    summary="搜索本体实体",
    description="""
    在本体中搜索与给定查询相关的本体实体（对象、关系、行动）。
    支持模糊匹配，会在实体的ID、名称、描述等字段中进行搜索。
    """,
    response_description="匹配的本体实体列表"
)
def search_ontology(
    query: str = Query(..., description="搜索关键词，用于在本体中查找相关实体"),
    db: Session = Depends(get_db)
):
    """
    在本体中搜索与给定查询相关的本体实体（对象、关系、行动）
    
    Args:
        query: 搜索关键词
        
    Returns:
        匹配的对象、关系、行动列表
    """
    try:
        results = {"objects": [], "links": [], "actions": []}
        query_lower = query.lower()
        
        # 搜索业务模型（对象）并预加载字段
        business_models = db.query(BusinessModel).options(
            joinedload(BusinessModel.fields)
        ).all()
        for model in business_models:
            model_text = f"{model.id} {model.name} {model.description or ''}".lower()
            if query_lower in model_text:
                results["objects"].append({
                    "id": model.id,
                    "name": model.name,
                    "description": model.description or "",
                    "type": "object"
                })
        
        # 搜索业务模型关系（链接）
        model_links = db.query(BusinessModelLink).all()
        for link in model_links:
            link_text = f"{link.id} {link.name} {link.description or ''}".lower()
            if query_lower in link_text:
                results["links"].append({
                    "id": link.id,
                    "name": link.name,
                    "description": link.description or "",
                    "type": "link"
                })
        
        # 搜索行动
        action_dao = get_action_dao()
        actions = action_dao.get_actions()
        for action in actions:
            action_text = f"{action.get('id', '')} {action.get('name', '')} {action.get('description', '')}".lower()
            if query_lower in action_text:
                results["actions"].append({
                    "id": action["id"],
                    "name": action.get("name", "Unnamed Action"),
                    "description": action.get("description", ""),
                    "type": "action"
                })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search ontology: {str(e)}")

@router.get(
    "/view_object_type/{object_type_id}", 
    operation_id="view_object_type",
    summary="查看对象类型详情",
    description="""
查看对象类型的详细信息，包括字段定义、主键字段、关联关系等。

**返回内容**:
- object_type_id: 对象类型的唯一标识符
- object_type_name: 对象类型的可读名称
- primary_key_id: 主键字段名
- fields: 所有字段定义
- links: 关联的关系类型
- actions: 可执行的动作类型
""",
    response_description="对象类型的完整详细信息"
)
def view_object_type(
    object_type_id: str = Path(..., description="对象类型ID（业务模型ID）"),
    db: Session = Depends(get_db)
):
    """
    在本体中查看现有对象类型的详细信息，包括其属性、关联链接类型和动作类型
    
    Args:
        object_type_id: 对象类型ID（业务模型ID）
        
    Returns:
        对象类型的完整详细信息
    """
    try:
        # 获取业务模型
        business_model = db.query(BusinessModel).filter(BusinessModel.id == object_type_id).first()
        if not business_model:
            raise HTTPException(status_code=404, detail=f"Object type {object_type_id} not found")
        
        _ = business_model.fields  # 确保加载字段
        
        # 获取关联的链接类型
        source_links = db.query(BusinessModelLink).filter(
            BusinessModelLink.source_model == object_type_id
        ).all()
        target_links = db.query(BusinessModelLink).filter(
            BusinessModelLink.target_model == object_type_id
        ).all()
        all_links = source_links + target_links
        
        links_info = []
        for link in all_links:
            links_info.append({
                "link_type_id": link.id,
                "link_type_name": link.name,
                "description": link.description or "",
                "direction": "source" if link.source_model == object_type_id else "target",
                "cardinality": link.cardinality,
                "other_model": link.target_model if link.source_model == object_type_id else link.source_model
            })
        
        # 获取关联的动作类型
        action_dao = get_action_dao()
        object_actions = action_dao.get_actions_by_model(object_type_id)
        
        actions_info = []
        for action in object_actions:
            actions_info.append({
                "action_type_id": action["action_id"],
                "action_type_name": action.get("name", "Unnamed Action"),
                "description": action.get("description", ""),
                "action_type": action.get("action_type"),
                "operation": action.get("operation"),
                "parameters": action.get("parameters", [])
            })
        
        return {
            "object_type": {
                "object_type_id": business_model.id,
                "object_type_name": business_model.name,
                "description": business_model.description or "",
                "primary_key_id": business_model.primary_key_id,
                # "api_name": business_model.api_name 模型的api_name好像没太大用对于MCP服务来说，所以这里不返回
            },
            "fields": [
                {
                    "field_id": field.field_id,
                    "name": field.name,
                    "description": field.description or "",
                    "data_type": field.data_type
                }
                for field in business_model.fields
            ] if business_model.fields else [],
            "links": links_info,
            "actions": actions_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to view object type: {str(e)}")

@router.get(
    "/view_link_type/{link_type_id}", 
    operation_id="view_link_type",
    summary="查看链接类型详情",
    description="""
    查看本体中已有的链接类型的详细信息。
    返回完整的链接元数据，包括源模型、目标模型、基数类型。
    """,
    response_description="链接类型的完整详细信息"
)
def view_link_type(
    link_type_id: str = Path(..., description="链接类型ID"),
    db: Session = Depends(get_db)
):
    """
    查看本体中已有的链接类型的详细信息
    
    Args:
        link_type_id: 链接类型ID
        
    Returns:
        链接类型的完整详细信息
    """
    try:
        link = db.query(BusinessModelLink).filter(BusinessModelLink.id == link_type_id).first()
        if not link:
            raise HTTPException(status_code=404, detail=f"Link type {link_type_id} not found")
        
        # 获取源模型和目标模型信息
        source_model = db.query(BusinessModel).filter(BusinessModel.id == link.source_model).first()
        target_model = db.query(BusinessModel).filter(BusinessModel.id == link.target_model).first()
        
        result = {
            "link_type": {
                "link_type_id": link.id,
                "link_type_name": link.name,
                "description": link.description or "",
                "cardinality": link.cardinality,
                "source": {
                    "object_type_id": link.source_model,
                    "object_type_name": source_model.name if source_model else None
                },
                "target": {
                    "object_type_id": link.target_model,
                    "object_type_name": target_model.name if target_model else None
                },
                "source_key": link.source_key,
                "target_key": link.target_key
            }
        }
        
        # 如果是多对多关系，包含中间表信息，但是这里不返回，因为对于查询方来说，中间表的信息是不相关的
        # if link.cardinality == "many-to-many" and link.intermediate_model:
        #     intermediate_model = db.query(BusinessModel).filter(
        #         BusinessModel.id == link.intermediate_model
        #     ).first()
        #     result["link_type"]["intermediate_model"] = {
        #         "id": link.intermediate_model,
        #         "name": intermediate_model.name if intermediate_model else None
        #     }
        #     result["link_type"]["intermediate_source_key"] = link.intermediate_source_key
        #     result["link_type"]["intermediate_target_key"] = link.intermediate_target_key
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to view link type: {str(e)}")

@router.get(
    "/view_action_type/{action_type_id}", 
    operation_id="view_action_type",
    summary="查看动作类型详情",
    description="""
    查看本体中已有的动作类型的详细信息，包括其参数、逻辑规则和依赖对象类型。
    返回完整的动作元数据，包括参数定义、提交条件、函数代码等详细信息。
    """,
    response_description="动作类型的完整详细信息"
)
def view_action_type(
    action_type_id: str = Path(..., description="动作类型ID"),
):
    """
    本体中查看已有的动作类型的详细信息，包括其参数、逻辑规则和依赖对象类型
    
    Args:
        action_type_id: 动作类型ID
        
    Returns:
        动作类型的完整详细信息
    """
    try:
        action_dao = get_action_dao()
        action = action_dao.get_action_by_id(action_type_id)
        if not action:
            raise HTTPException(status_code=404, detail=f"Action type {action_type_id} not found")
        
        return {
            "action_type": {
                "action_type_id": action["id"],
                "action_type_name": action.get("name"),
                "description": action.get("description"),
                "action_type": action.get("action_type"),  # object, link, function
                "operation": action.get("operation"),      # create, update, delete, custom
                "target_object_type_id": action.get("target_model_id"),
                "target_link_type_id": action.get("target_link_id"),
                "parameters": action.get("parameters", []),
                "submission_criteria": action.get("submission_criteria", []),
                "function_code": action.get("function_code")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to view action type: {str(e)}")