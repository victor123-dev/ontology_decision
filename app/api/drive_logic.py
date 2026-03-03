from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.drive_logic import DriveLogic, Task
from app.models.data_sensing import DataSensingConfig
from app.models.agent import Agent, Capability
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from sqlalchemy import select

router = APIRouter()

def get_db():
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/drive-logics")
def create_drive_logic(logic: dict, db: Session = Depends(get_db)):
    db_logic = DriveLogic(
        name=logic.get("name"),
        type=logic.get("type"),
        config=logic.get("config", {}),
        description=logic.get("description")
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
    
    # 关联任务
    task_ids = logic.get("task_ids", [])
    if task_ids:
        tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
        db_logic.tasks = tasks
        db.commit()
        db.refresh(db_logic)
    
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
            "events": [{"id": e.id, "name": e.name, "type": e.type} for e in logic.events],
            "tasks": [{"id": t.id, "name": t.name, "capability_type": t.capability_type} for t in logic.tasks],
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
        "events": [{"id": e.id, "name": e.name, "type": e.type} for e in logic.events],
        "tasks": [{"id": t.id, "name": t.name, "capability_type": t.capability_type} for t in logic.tasks],
        "created_at": logic.created_at,
        "updated_at": logic.updated_at
    }

@router.put("/drive-logics/{logic_id}")
def update_drive_logic(logic_id: int, logic: dict, db: Session = Depends(get_db)):
    db_logic = db.query(DriveLogic).filter(DriveLogic.id == logic_id).first()
    if not db_logic:
        raise HTTPException(status_code=404, detail="DriveLogic not found")
    
    if "name" in logic:
        db_logic.name = logic["name"]
    if "type" in logic:
        db_logic.type = logic["type"]
    if "config" in logic:
        db_logic.config = logic["config"]
    if "description" in logic:
        db_logic.description = logic["description"]
    
    if "event_ids" in logic:
        event_ids = logic["event_ids"]
        if event_ids:
            events = db.query(DataSensingConfig).filter(DataSensingConfig.id.in_(event_ids)).all()
            db_logic.events = events
        else:
            db_logic.events = []
    
    if "task_ids" in logic:
        task_ids = logic["task_ids"]
        if task_ids:
            tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
            db_logic.tasks = tasks
        else:
            db_logic.tasks = []
    
    db.commit()
    db.refresh(db_logic)
    return db_logic

@router.delete("/drive-logics/{logic_id}")
def delete_drive_logic(logic_id: int, db: Session = Depends(get_db)):
    db_logic = db.query(DriveLogic).filter(DriveLogic.id == logic_id).first()
    if not db_logic:
        raise HTTPException(status_code=404, detail="DriveLogic not found")
    
    db.delete(db_logic)
    db.commit()
    return {"message": "DriveLogic deleted successfully"}

@router.post("/tasks")
def create_task(task: dict, db: Session = Depends(get_db)):
    db_task = Task(
        name=task.get("name"),
        capability_type=task.get("capability_type"),
        config=task.get("config"),
        description=task.get("description"),
        status="pending"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    result = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "name": task.name,
            "capability_type": task.capability_type,
            "config": task.config,
            "description": task.description,
            "status": task.status,
            "assigned_agent_id": task.assigned_agent_id,
            "result": task.result,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        if task.assigned_agent:
            task_dict["assigned_agent"] = {"id": task.assigned_agent.id, "name": task.assigned_agent.name}
        result.append(task_dict)
    return result

@router.put("/tasks/{task_id}")
def update_task(task_id: int, task: dict, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if "name" in task:
        db_task.name = task["name"]
    if "capability_type" in task:
        db_task.capability_type = task["capability_type"]
    if "config" in task:
        db_task.config = task["config"]
    if "description" in task:
        db_task.description = task["description"]
    if "status" in task:
        db_task.status = task["status"]
    if "result" in task:
        db_task.result = task["result"]
    if "assigned_agent_id" in task:
        if task["assigned_agent_id"]:
            agent = db.query(Agent).filter(Agent.id == task["assigned_agent_id"]).first()
            if agent:
                db_task.assigned_agent = agent
        else:
            db_task.assigned_agent_id = None
    
    db.commit()
    db.refresh(db_task)
    return db_task

@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted successfully"}
