from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.drive_log import DriveLog
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

@router.post("/drive-logs")
def create_drive_log(log: dict, db: Session = Depends(get_db)):
    db_log = DriveLog(
        level=log.get("level"),
        category=log.get("category"),
        message=log.get("message"),
        data=log.get("data")
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/drive-logs")
def get_drive_logs(
    level: str = None,
    category: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(DriveLog)
    
    if level:
        query = query.filter(DriveLog.level == level)
    if category:
        query = query.filter(DriveLog.category == category)
    
    return query.order_by(DriveLog.created_at.desc()).limit(limit).all()

@router.get("/drive-logs/{log_id}")
def get_drive_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(DriveLog).filter(DriveLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="DriveLog not found")
    return log
