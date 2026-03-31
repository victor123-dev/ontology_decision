from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.data_source import DataSource
from app.models.business_model import BusinessModel
from app.models.data_sensing import DataSensingConfig
from app.models.drive_logic import DriveLogic, Task
from app.models.agent import Agent, Capability
from app.utils.shared_utils import get_db

router = APIRouter()

@router.get("/drive-visualization/full-graph")
def get_full_drive_graph(db: Session = Depends(get_db)):
    """获取完整的驱动全景图数据"""
    
    # 获取所有业务模型（包含字段）
    business_models = db.query(BusinessModel).all()
    for model in business_models:
        db.refresh(model)  # 确保加载字段关系
    
    # 获取所有数据感知配置
    sensing_configs = db.query(DataSensingConfig).all()
    
    # 获取所有驱动逻辑（包含关联的事件和任务）
    drive_logics = db.query(DriveLogic).all()
    for logic in drive_logics:
        db.refresh(logic)  # 确保加载events和tasks关系
    
    # 获取所有任务（包含关联的能力）
    tasks = db.query(Task).all()
    for task in tasks:
        db.refresh(task)  # 确保加载capabilities关系
    
    return {
        "nodes": _build_nodes(
            business_models, sensing_configs, 
            drive_logics, tasks
        ),
        "edges": _build_edges(
            business_models, sensing_configs, 
            drive_logics, tasks
        )
    }

@router.get("/drive-visualization/model/{model_id}")
def get_model_driven_graph(model_id: str, db: Session = Depends(get_db)):
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
    
    # 获取关联的任务
    task_ids = set()
    for logic in drive_logics:
        for task in logic.tasks:
            task_ids.add(task.id)
    
    tasks = db.query(Task).filter(
        Task.id.in_(list(task_ids))
    ).all() if task_ids else []
    
    return {
        "nodes": _build_nodes(
            [business_model], 
            sensing_configs, 
            drive_logics, 
            tasks
        ),
        "edges": _build_edges(
            [business_model], 
            sensing_configs, 
            drive_logics, 
            tasks
        )
    }

def _build_nodes(business_models, sensing_configs, 
                drive_logics, tasks):
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
                "config": logic.config
            }
        })
    
    # 任务节点
    for task in tasks:
        nodes.append({
            "id": f"task_{task.id}",
            "type": "task",
            "name": task.name,
            "description": task.description or "",
            "data": {
                "id": task.id,
                "config": task.config
            }
        })
    
    return nodes

def _build_edges(business_models, sensing_configs, 
                drive_logics, tasks):
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
    
    # 驱动逻辑 -> 任务 (多对多)
    for logic in drive_logics:
        for task in logic.tasks:
            edges.append({
                "source": f"logic_{logic.id}",
                "target": f"task_{task.id}",
                "type": "logic_to_task",
                "description": f"{logic.name} → {task.name}"
            })
    
    return edges