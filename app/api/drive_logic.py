from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.drive_logic import DriveLogic, Task, TaskInstance
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
        description=task.get("description")
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
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
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

# TaskInstance相关端点
@router.get("/task-instances")
def get_task_instances(db: Session = Depends(get_db)):
    instances = db.query(TaskInstance).all()
    result = []
    for instance in instances:
        instance_dict = {
            "id": instance.id,
            "task_id": instance.task_id,
            "task_name": instance.task.name if instance.task else None,
            "status": instance.status,
            "result": instance.result,
            "assigned_agent_id": instance.assigned_agent_id,
            "assigned_agent_name": instance.assigned_agent.name if instance.assigned_agent else None,
            "started_at": instance.started_at,
            "completed_at": instance.completed_at
        }
        result.append(instance_dict)
    return result

@router.get("/task-instances/{instance_id}")
def get_task_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = db.query(TaskInstance).filter(TaskInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="TaskInstance not found")
    
    return {
        "id": instance.id,
        "task_id": instance.task_id,
        "task_name": instance.task.name if instance.task else None,
        "status": instance.status,
        "result": instance.result,
        "assigned_agent_id": instance.assigned_agent_id,
        "assigned_agent_name": instance.assigned_agent.name if instance.assigned_agent else None,
        "started_at": instance.started_at,
        "completed_at": instance.completed_at
    }

@router.get("/tasks/{task_id}/instances")
def get_task_instances_by_task(task_id: int, db: Session = Depends(get_db)):
    instances = db.query(TaskInstance).filter(TaskInstance.task_id == task_id).all()
    result = []
    for instance in instances:
        instance_dict = {
            "id": instance.id,
            "task_id": instance.task_id,
            "status": instance.status,
            "result": instance.result,
            "assigned_agent_id": instance.assigned_agent_id,
            "assigned_agent_name": instance.assigned_agent.name if instance.assigned_agent else None,
            "started_at": instance.started_at,
            "completed_at": instance.completed_at
        }
        result.append(instance_dict)
    return result
