from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.drive_logic import DriveLogic, Task
from app.utils.db_client import Base, create_engine, sessionmaker

router = APIRouter()

# 数据库会话依赖
def get_db():
    engine = create_engine("sqlite:///data.db")
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
        config=logic.get("config"),
        description=logic.get("description")
    )
    db.add(db_logic)
    db.commit()
    db.refresh(db_logic)
    return db_logic

@router.get("/drive-logics")
def get_drive_logics(db: Session = Depends(get_db)):
    return db.query(DriveLogic).all()

@router.get("/drive-logics/{logic_id}")
def get_drive_logic(logic_id: int, db: Session = Depends(get_db)):
    logic = db.query(DriveLogic).filter(DriveLogic.id == logic_id).first()
    if not logic:
        raise HTTPException(status_code=404, detail="DriveLogic not found")
    return logic

@router.put("/drive-logics/{logic_id}")
def update_drive_logic(logic_id: int, logic: dict, db: Session = Depends(get_db)):
    db_logic = db.query(DriveLogic).filter(DriveLogic.id == logic_id).first()
    if not db_logic:
        raise HTTPException(status_code=404, detail="DriveLogic not found")
    
    for key, value in logic.items():
        setattr(db_logic, key, value)
    
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
        type=task.get("type"),
        config=task.get("config"),
        description=task.get("description")
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()
