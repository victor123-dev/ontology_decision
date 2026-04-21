from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.data_source import DataSource
from app.models.business_model import BusinessModel
from app.models.data_sensing import DataSensingConfig
from app.models.drive_logic import DriveLogic
from app.utils.shared_utils import get_db
from app.services.action_service import get_action_service, ActionService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/drive-visualization/full-graph")
def get_full_drive_graph(db: Session = Depends(get_db), action_service: ActionService = Depends(get_action_service)):
    """获取完整的驱动全景图数据"""
    
    # 获取所有业务模型（包含字段）
    business_models = db.query(BusinessModel).all()
    for model in business_models:
        db.refresh(model)  # 确保加载字段关系
    
    # 获取所有数据感知配置
    sensing_configs = db.query(DataSensingConfig).all()
    
    # 获取所有驱动逻辑（包含关联的事件）
    drive_logics = db.query(DriveLogic).all()
    for logic in drive_logics:
        db.refresh(logic)  # 确保加载events关系
    actions = action_service.get_actions()
    logger.info(f"Total actions: {actions}")
    
    return {
        "nodes": _build_nodes(
            business_models, sensing_configs, 
            drive_logics, actions
        ),
        "edges": _build_edges(
            business_models, sensing_configs, 
            drive_logics, actions
        )
    }

@router.get("/drive-visualization/model/{model_id}")
def get_model_driven_graph(model_id: str, db: Session = Depends(get_db), action_service: ActionService = Depends(get_action_service)):
    """获取指定业务模型的驱动链路图"""
    # 获取指定业务模型
    business_model = db.query(BusinessModel).filter(
        BusinessModel.id == model_id
    ).first()
    if not business_model:
        raise HTTPException(status_code=404, detail="Business model not found")
    
    # 获取关联的数据感知配置
    sensing_configs = db.query(DataSensingConfig).filter(
        DataSensingConfig.model_id == model_id
    ).all()
    
    # 获取关联的驱动逻辑
    drive_logic_ids = set()
    for config in sensing_configs:
        for logic in config.logics:
            drive_logic_ids.add(logic.id)
    
    drive_logics = db.query(DriveLogic).filter(
        DriveLogic.id.in_(list(drive_logic_ids))
    ).all() if drive_logic_ids else []
    
    # 获取关联的行动
    action_ids = set()
    for logic in drive_logics:
        if logic.action_ids:
            for action_id in logic.action_ids:
                action_ids.add(action_id)
    
    actions = action_service.get_actions({"id": {"$:in": list(action_ids)}}) if action_ids else []
    
    return {
        "nodes": _build_nodes(
            [business_model], 
            sensing_configs, 
            drive_logics,
            actions
        ),
        "edges": _build_edges(
            [business_model], 
            sensing_configs, 
            drive_logics,
            actions
        )
    }

def _build_nodes(business_models, sensing_configs, 
                drive_logics, actions):
    """构建节点列表"""
    nodes = []
    
    # 业务模型节点
    for bm in business_models:
        nodes.append({
            "id": f"bm_{bm.id}",
            "type": "business_model",
            "name": bm.name,
            "description": bm.description or "",
            "data": {
                "id": bm.id,
                "primary_key_id": bm.primary_key_id,
                "field_count": len(bm.fields) if bm.fields else 0
            }
        })
    
    # 数据感知配置节点
    for config in sensing_configs:
        nodes.append({
            "id": f"sensing_{config.id}",
            "type": "sensing_config",
            "name": config.name,
            "description": config.description or "",
            "data": {
                "id": config.id,
                "type": config.type,
                "status": config.status,
                "config": config.config
            }
        })
    
    # 驱动逻辑节点
    for logic in drive_logics:
        nodes.append({
            "id": f"logic_{logic.id}",
            "type": "drive_logic",
            "name": logic.name,
            "description": logic.description or "",
            "data": {
                "id": logic.id,
                "type": logic.type,
                "config": logic.config,
                "action_ids": logic.action_ids or []
            }
        })
    # 行动节点
    for action in actions:
        nodes.append({
            "id": f"action_{action.get('id')}",
            "type": "action",
            "name": action.get('name'),
            "description": action.get('description') or "",
            "data": {
                "id": action.get('id'),
                "type": action.get('action_type')
            }
        })
    
    return nodes

def _build_edges(business_models, sensing_configs, 
                drive_logics, actions):
    """构建边列表"""
    edges = []
    
    # 业务模型 -> 数据感知配置
    for config in sensing_configs:
        if config.model_id:
            # 查找对应的业务模型名称
            model_name = ""
            for bm in business_models:
                if bm.id == config.model_id:
                    model_name = bm.name
                    break
            
            edges.append({
                "source": f"bm_{config.model_id}",
                "target": f"sensing_{config.id}",
                "type": "model_to_sensing",
                "description": f"{model_name} → {config.name}"
            })
    
    # 数据感知配置 -> 驱动逻辑 (多对多)
    for config in sensing_configs:
        for logic in config.logics:
            edges.append({
                "source": f"sensing_{config.id}",
                "target": f"logic_{logic.id}",
                "type": "sensing_to_logic",
                "description": f"{config.name} → {logic.name}"
            })
    
    # 创建 action_id 到 action 对象的映射
    action_map = {action.get('id'): action for action in actions}
    
    # 驱动逻辑 -> 行动 (多对多)
    for logic in drive_logics:
        for action_id in logic.action_ids or []:
            action = action_map.get(action_id)
            if action:
                edges.append({
                    "source": f"logic_{logic.id}",
                    "target": f"action_{action_id}",
                    "type": "logic_to_action",
                    "description": f"{logic.name} → {action.get('name')}"
                })
    
    return edges