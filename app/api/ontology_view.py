from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.business_model import BusinessModel
from app.models.business_model_link import BusinessModelLink
from app.utils.shared_utils import get_db
from app.dao.action_dao import get_action_dao

router = APIRouter()

@router.get("/ontology-view/graph")
def get_ontology_graph(db: Session = Depends(get_db)):
    """获取本体视图的图数据"""
    
    # 获取所有业务模型（包含字段）
    business_models = db.query(BusinessModel).all()
    for model in business_models:
        _ = model.fields  # 确保加载字段关系
    
    # 获取所有业务模型关系
    model_links = db.query(BusinessModelLink).all()
    
    # 获取所有行动
    action_dao = get_action_dao()
    actions = action_dao.get_actions()
    
    # 创建业务模型ID集合，用于验证边的引用
    model_ids = {model.id for model in business_models}
    
    # 过滤掉引用不存在节点的边
    valid_links = []
    for link in model_links:
        # 检查源模型和目标模型是否存在
        if link.source_model not in model_ids or link.target_model not in model_ids:
            continue
        
        # 对于多对多关系，还需要检查中间模型是否存在
        if link.cardinality == 'many-to-many' and link.intermediate_model:
            if link.intermediate_model not in model_ids:
                continue
        
        valid_links.append(link)
    
    return {
        "nodes": _build_nodes(business_models, actions),
        "edges": _build_edges(valid_links, actions)
    }

def _build_nodes(business_models, actions):
    """构建业务模型和行动节点列表"""
    nodes = []
    
    # 添加业务模型节点
    for bm in business_models:
        nodes.append({
            "id": bm.id,
            "type": "business_model",
            "name": bm.name,
            "description": bm.description or "",
            "data": {
                "id": bm.id,
                "name": bm.name,
                "description": bm.description,
                "data_source_id": bm.data_source_id,
                "primary_key_id": bm.primary_key_id,
                "field_count": len(bm.fields) if bm.fields else 0,
                "fields": [
                    {
                        "field_id": field.field_id,
                        "name": field.name,
                        "description": field.description,
                        "data_type": field.data_type
                    }
                    for field in bm.fields
                ] if bm.fields else []
            }
        })
    
    # 添加行动节点
    for action in actions:
        nodes.append({
            "id": action["id"],
            "type": "action",
            "name": action.get("name", "Unnamed Action"),
            "description": action.get("description", ""),
            "data": {
                "id": action["id"],
                "name": action.get("name"),
                "description": action.get("description"),
                "action_type": action.get("action_type"),
                "operation": action.get("operation"),
                "target_model_id": action.get("target_model_id"),
                "target_link_id": action.get("target_link_id"),
                "parameters": action.get("parameters"),
                "submission_criteria": action.get("submission_criteria"),
                "function_code": action.get("function_code")
            }
        })
    
    return nodes

def _build_edges(model_links, actions):
    """构建模型关系边列表和行动-模型关系边"""
    edges = []
    
    # 添加模型关系边
    for link in model_links:
        edges.append({
            "id": link.id,
            "source": link.source_model,
            "target": link.target_model,
            "name": link.name or f"{link.source_model} -> {link.target_model}",
            "description": link.description or "",
            "data": {
                "id": link.id,
                "name": link.name,
                "description": link.description,
                "source_model": link.source_model,
                "source_key": link.source_key,
                "target_model": link.target_model,
                "target_key": link.target_key,
                "cardinality": link.cardinality,
                "intermediate_model": link.intermediate_model,
                "intermediate_source_key": link.intermediate_source_key,
                "intermediate_target_key": link.intermediate_target_key
            }
        })
    
    # 添加行动-模型关系边
    for action in actions:
        action_id = action["id"]
        target_model_id = action.get("target_model_id")
        
        if target_model_id:
            edges.append({
                "id": f"action_{action_id}_to_{target_model_id}",
                "source": action_id,
                "target": target_model_id,
                "name": "作用于",
                "description": f"{action.get('name', 'Action')} 作用于 {target_model_id}",
                "data": {
                    "type": "action_to_model",
                    "action_id": action_id,
                    "model_id": target_model_id
                }
            })
    
    return edges