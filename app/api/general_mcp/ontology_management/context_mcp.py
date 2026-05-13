"""上下文获取模块 - Ontology Management MCP
提供本体全局上下文、结构分析和搜索功能
与 ontology_type_mcp.py 中的查询工具完全独立，面向管理场景
集成语义一致性验证和 Agent 辅助功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Dict, List, Optional
from app.models.business_model import BusinessModel
from app.models.business_model_link import BusinessModelLink
from app.utils.shared_utils import get_db
from app.dao.action_dao import get_action_dao
from pydantic import BaseModel, Field
from .semantic_validator import SemanticValidator
from .agent_helper import AgentHelper

router = APIRouter()


class OntologyManagementContext(BaseModel):
    """本体管理上下文响应模型"""
    summary: Dict = Field(description="本体统计摘要")
    objects: List[Dict] = Field(description="对象类型列表")
    links: List[Dict] = Field(description="关系类型列表")
    actions: List[Dict] = Field(description="行动类型列表")
    completeness_score: float = Field(description="本体完整性评分 (0-100)")
    
    # Agent 友好字段
    semantic_validation: Optional[Dict] = Field(default=None, description="跨元素语义验证结果")
    recommended_workflow: Optional[List[Dict]] = Field(default=None, description="推荐的工作流程")
    natural_language_summary: Optional[str] = Field(default=None, description="自然语言摘要")
    potential_issues: Optional[List[Dict]] = Field(default=None, description="潜在问题预警")


@router.get(
    "/get_ontology_management_context",
    operation_id="get_ontology_management_context",
    summary="获取本体管理上下文",
    description="""
获取本体的完整管理上下文，以 JSON 格式返回结构分析结果。
与查询用的 get_ontology_context 不同，此工具面向本体管理场景，返回:
- 本体统计摘要（对象类型数量、关系类型数量、行动类型数量）
- 所有对象类型的完整信息（含字段列表）
- 所有关系类型的完整信息（含源/目标模型）
- 所有行动类型的完整信息（含参数定义）
- 本体完整性评分（基于模型间关联度计算）

适用于 Agent 评估当前本体状态、发现缺失模型、规划本体扩展。
    """,
    response_model=OntologyManagementContext,
    response_description="本体管理上下文的完整 JSON 结构"
)
def get_ontology_management_context(db: Session = Depends(get_db)):
    """
    获取本体的完整管理上下文（JSON 格式）
    
    Returns:
        包含统计信息、对象、关系、行动的完整结构
    """
    try:
        # 获取所有业务模型（对象）并预加载字段
        business_models = db.query(BusinessModel).options(
            joinedload(BusinessModel.fields)
        ).all()
        
        objects_info = []
        for model in business_models:
            objects_info.append({
                "object_type_id": model.id,
                "object_type_name": model.name,
                "description": model.description or "",
                "primary_key_id": model.primary_key_id,
                "data_source_id": model.data_source_id,
                "fields_count": len(model.fields) if model.fields else 0,
                "fields": [
                    {
                        "field_id": field.field_id,
                        "name": field.name,
                        "data_type": field.data_type,
                        "required": field.required,
                        "is_enum": field.is_enum,
                        "enum_values": field.enum_values
                    }
                    for field in (model.fields or [])
                ]
            })
        
        # 获取所有业务模型关系（链接）
        model_links = db.query(BusinessModelLink).all()
        
        links_info = []
        for link in model_links:
            # 获取源模型和目标模型名称
            source_model = db.query(BusinessModel).filter(
                BusinessModel.id == link.source_model
            ).first()
            target_model = db.query(BusinessModel).filter(
                BusinessModel.id == link.target_model
            ).first()
            
            links_info.append({
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
                "intermediate_object_type_id": link.intermediate_model
            })
        
        # 获取所有行动
        action_dao = get_action_dao()
        actions = action_dao.get_actions()
        
        actions_info = []
        for action in actions:
            actions_info.append({
                "action_type_id": action["id"],
                "action_type_name": action.get("name", "Unnamed Action"),
                "description": action.get("description", ""),
                "action_type": action.get("action_type"),
                "operation": action.get("operation"),
                "target_object_type_id": action.get("target_model_id"),
                "target_link_type_id": action.get("target_link_id"),
                "parameters_count": len(action.get("parameters", [])),
                "parameters": action.get("parameters", [])
            })
        
        # 计算完整性评分
        completeness_score = _calculate_completeness_score(
            objects_info, links_info, actions_info
        )
        
        # 构建统计摘要
        summary = {
            "total_object_types": len(objects_info),
            "total_link_types": len(links_info),
            "total_action_types": len(actions_info),
            "object_types_with_action_types": len(set(
                action["target_object_type_id"] 
                for action in actions_info 
                if action.get("target_object_type_id")
            )),
            "object_types_without_link_types": len([
                obj["object_type_id"] for obj in objects_info
                if not any(
                    link["source_object_type_id"] == obj["object_type_id"] or 
                    link["target_object_type_id"] == obj["object_type_id"]
                    for link in links_info
                )
            ])
        }
        
        # 语义一致性验证
        semantic_validation = SemanticValidator.cross_validate_consistency(db)
        
        # 生成推荐工作流
        recommended_workflow = AgentHelper.generate_recommended_workflow(
            objects_info, links_info, actions_info
        )
        
        # 生成自然语言摘要
        context_data = {
            "summary": summary,
            "completeness_score": completeness_score
        }
        natural_language_summary = AgentHelper.generate_natural_language_summary(context_data)
        
        # 潜在问题预警
        potential_issues = semantic_validation.get("issues", []) + semantic_validation.get("warnings", [])
        
        return OntologyManagementContext(
            summary=summary,
            objects=objects_info,
            links=links_info,
            actions=actions_info,
            completeness_score=completeness_score,
            semantic_validation=semantic_validation,
            recommended_workflow=recommended_workflow,
            natural_language_summary=natural_language_summary,
            potential_issues=potential_issues
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get ontology management context: {str(e)}"
        )


def _calculate_completeness_score(
    objects: List[Dict], 
    links: List[Dict], 
    actions: List[Dict]
) -> float:
    """
    计算本体完整性评分 (0-100)
    
    评分维度:
    1. 对象字段完整度 (40%): 平均每个对象的字段数
    2. 关系覆盖度 (30%): 有关系的对象占比
    3. Action 覆盖度 (30%): 有 Action 的对象占比
    """
    if not objects:
        return 0.0
    
    # 1. 对象字段完整度 (理想: 平均 5+ 字段)
    avg_fields = sum(obj["fields_count"] for obj in objects) / len(objects)
    fields_score = min(avg_fields / 5.0, 1.0) * 40
    
    # 2. 关系覆盖度
    objects_with_links = set()
    for link in links:
        objects_with_links.add(link["source_object_type_id"])
        objects_with_links.add(link["target_object_type_id"])
    
    link_coverage = len(objects_with_links) / len(objects)
    link_score = link_coverage * 30
    
    # 3. Action 覆盖度
    objects_with_actions = set(
        action["target_object_type_id"] 
        for action in actions 
        if action.get("target_object_type_id")
    )
    action_coverage = len(objects_with_actions) / len(objects)
    action_score = action_coverage * 30
    
    return round(fields_score + link_score + action_score, 2)


@router.get(
    "/search_ontology_for_management",
    operation_id="search_ontology_for_management",
    summary="搜索本体元素（管理用）",
    description="""
在本体中搜索可管理的本体元素（对象类型、关系类型、行动类型）。
支持模糊匹配，会在元素的 ID、名称、描述中进行搜索。

与查询用的 search_ontology 不同，此工具返回:
- 针对对象类型、关系类型、行动类型可执行的操作列表（create/update/delete）
- 元素的依赖关系（删除前需要检查的内容）
- 完整性建议（如缺少字段、缺少关系等）

适用于 Agent 查找需要修改或删除的本体元素。
    """,
    response_description="匹配的本体元素列表及管理建议"
)
def search_ontology_for_management(
    query: str = Query(..., description="搜索关键词"),
    element_type: Optional[str] = Query(
        None, 
        description="元素类型过滤: objectType, linkType, actionType。为空则搜索所有类型"
    ),
    db: Session = Depends(get_db)
):
    """
    搜索本体元素（管理场景专用）
    
    Args:
        query: 搜索关键词
        element_type: 元素类型过滤 (objectType/linkType/actionType)
        
    Returns:
        匹配的元素列表及管理建议
    """
    try:
        results = {"object_types": [], "link_types": [], "action_types": []}
        query_lower = query.lower()
        
        # 搜索业务模型（对象）
        if not element_type or element_type == "objectType":
            business_models = db.query(BusinessModel).options(
                joinedload(BusinessModel.fields)
            ).all()
            
            for model in business_models:
                model_text = f"{model.id} {model.name} {model.description or ''}".lower()
                if query_lower in model_text:
                    # 统计依赖关系
                    dependent_links = db.query(BusinessModelLink).filter(
                        (BusinessModelLink.source_model == model.id) |
                        (BusinessModelLink.target_model == model.id)
                    ).count()
                    
                    results["object_types"].append({
                        "object_type_id": model.id,
                        "object_type_name": model.name,
                        "description": model.description or "",
                        "type": "object",
                        "fields_count": len(model.fields) if model.fields else 0,
                        "dependent_links": dependent_links,
                        "management_actions": ["view", "update", "delete"],
                        "warnings": [
                            f"删除前需要处理 {dependent_links} 个关联关系"
                        ] if dependent_links > 0 else []
                    })
        
        # 搜索业务模型关系（链接）
        if not element_type or element_type == "linkType":
            model_links = db.query(BusinessModelLink).all()
            for link in model_links:
                link_text = f"{link.id} {link.name} {link.description or ''}".lower()
                if query_lower in link_text:
                    results["link_types"].append({
                        "link_type_id": link.id,
                        "link_type_name": link.name,
                        "description": link.description or "",
                        "type": "link",
                        "source_object_type_id": link.source_model,
                        "target_object_type_id": link.target_model,
                        "cardinality": link.cardinality,
                        "management_actions": ["view", "update", "delete"]
                    })
        
        # 搜索行动
        if not element_type or element_type == "actionType":
            action_dao = get_action_dao()
            actions = action_dao.get_actions()
            for action in actions:
                action_text = f"{action.get('id', '')} {action.get('name', '')} {action.get('description', '')}".lower()
                if query_lower in action_text:
                    results["action_types"].append({
                        "action_type_id": action["id"],
                        "action_type_name": action.get("name", "Unnamed Action"),
                        "description": action.get("description", ""),
                        "type": "action",
                        "action_type": action.get("action_type"),
                        "operation": action.get("operation"),
                        "target_object_type_id": action.get("target_model_id"),
                        "management_actions": ["view", "update", "delete", "test"]
                    })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to search ontology for management: {str(e)}"
        )
