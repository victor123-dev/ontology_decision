from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.drive_logic import DriveLogic
from app.models.data_sensing import DataSensingConfig
from app.utils.shared_utils import get_db
from app.utils.background_task_processor import background_task_processor
from app.utils.natural_language_generator import generate_natural_language_description_for_drive_logic

router = APIRouter()

@router.post("/drive-logics")
def create_drive_logic(logic: dict, db: Session = Depends(get_db)):
    db_logic = DriveLogic(
        name=logic.get("name"),
        type=logic.get("type"),
        config=logic.get("config", {}),
        description=logic.get("description"),
        natural_language_description=None  # 初始化为空
    )
    db.add(db_logic)
    db.commit()
    db.refresh(db_logic)
    
    # 关联事件
    event_ids = logic.get("event_ids", [])
    if event_ids:
        events = db.query(DataSensingConfig).filter(DataSensingConfig.id.in_(event_ids)).all()
        db_logic.events = events
        db.commit()
        db.refresh(db_logic)
    
    # 关联行动
    action_ids = logic.get("action_ids", [])
    if action_ids:
        db_logic.action_ids = action_ids
        db.commit()
        db.refresh(db_logic)
    
    # 触发异步任务生成自然语言描述
    background_task_processor.submit_task(
        generate_natural_language_description_for_drive_logic, 
        db_logic.id
    )
    
    return db_logic

@router.get("/drive-logics")
def get_drive_logics(db: Session = Depends(get_db)):
    logics = db.query(DriveLogic).all()
    result = []
    for logic in logics:
        result.append({
            "id": logic.id,
            "name": logic.name,
            "type": logic.type,
            "config": logic.config,
            "description": logic.description,
            "natural_language_description": logic.natural_language_description,
            "events": [{"id": e.id, "name": e.name, "type": e.type} for e in logic.events],
            "action_ids": logic.action_ids or [],
            "created_at": logic.created_at,
            "updated_at": logic.updated_at
        })
    return result

@router.get("/drive-logics/{logic_id}")
def get_drive_logic(logic_id: int, db: Session = Depends(get_db)):
    logic = db.query(DriveLogic).filter(DriveLogic.id == logic_id).first()
    if not logic:
        raise HTTPException(status_code=404, detail="DriveLogic not found")
    
    return {
            "id": logic.id,
            "name": logic.name,
            "type": logic.type,
            "config": logic.config,
            "description": logic.description,
            "natural_language_description": logic.natural_language_description,
            "events": [{"id": e.id, "name": e.name, "type": e.type} for e in logic.events],
            "action_ids": logic.action_ids or [],
            "created_at": logic.created_at,
            "updated_at": logic.updated_at
        }

@router.put("/drive-logics/{logic_id}")
def update_drive_logic(logic_id: int, logic: dict, db: Session = Depends(get_db)):
    db_logic = db.query(DriveLogic).filter(DriveLogic.id == logic_id).first()
    if not db_logic:
        raise HTTPException(status_code=404, detail="DriveLogic not found")
    
    # 检查是否有实质性变化，需要重新生成描述
    should_regenerate_description = False
    
    if "name" in logic and db_logic.name != logic["name"]:
        db_logic.name = logic["name"]
        should_regenerate_description = True
    elif "name" in logic:
        db_logic.name = logic["name"]
        
    if "type" in logic and db_logic.type != logic["type"]:
        db_logic.type = logic["type"]
        should_regenerate_description = True
    elif "type" in logic:
        db_logic.type = logic["type"]
        
    if "config" in logic and db_logic.config != logic["config"]:
        db_logic.config = logic["config"]
        should_regenerate_description = True
    elif "config" in logic:
        db_logic.config = logic["config"]
        
    if "description" in logic and db_logic.description != logic["description"]:
        db_logic.description = logic["description"]
        should_regenerate_description = True
    elif "description" in logic:
        db_logic.description = logic["description"]
    
    # 检查事件关联是否变化
    if "event_ids" in logic:
        old_event_ids = [e.id for e in db_logic.events]
        new_event_ids = logic["event_ids"] or []
        if set(old_event_ids) != set(new_event_ids):
            should_regenerate_description = True
            
        if new_event_ids:
            events = db.query(DataSensingConfig).filter(DataSensingConfig.id.in_(new_event_ids)).all()
            db_logic.events = events
        else:
            db_logic.events = []
    
    # 检查行动关联是否变化
    if "action_ids" in logic:
        old_action_ids = db_logic.action_ids or []
        new_action_ids = logic["action_ids"] or []
        if set(old_action_ids) != set(new_action_ids):
            should_regenerate_description = True
            
        db_logic.action_ids = new_action_ids
    
    db.commit()
    db.refresh(db_logic)
    
    # 如果需要重新生成描述，触发异步任务
    if should_regenerate_description:
        background_task_processor.submit_task(
            generate_natural_language_description_for_drive_logic, 
            db_logic.id
        )
    
    return db_logic

@router.delete("/drive-logics/{logic_id}")
def delete_drive_logic(logic_id: int, db: Session = Depends(get_db)):
    db_logic = db.query(DriveLogic).filter(DriveLogic.id == logic_id).first()
    if not db_logic:
        raise HTTPException(status_code=404, detail="DriveLogic not found")
    
    db.delete(db_logic)
    db.commit()
    return {"message": "DriveLogic deleted successfully"}