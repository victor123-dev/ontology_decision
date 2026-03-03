from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.data_sensing import DataSensingConfig
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings

router = APIRouter()

# 数据库会话依赖
def get_db():
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/test-execution/simulate-event")
def simulate_event(
    event_data: dict,
    db: Session = Depends(get_db)
):
    """
    模拟事件触发
    event_data: {
        "config_id": 1,  # 数据感知配置ID
        "data": {...}     # 事件数据
    }
    """
    config_id = event_data.get("config_id")
    event_data = event_data.get("data")
    
    # 验证配置是否存在
    config = db.query(DataSensingConfig).filter(DataSensingConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="DataSensingConfig not found")
    
    # 模拟事件处理逻辑
    # 这里可以触发数据驱动引擎的处理流程
    
    return {
        "message": "Event simulated successfully",
        "config": config.name,
        "data": event_data
    }
