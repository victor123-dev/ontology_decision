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

@router.post("/data-sensing-configs")
def create_data_sensing_config(config: dict, db: Session = Depends(get_db)):
    db_config = DataSensingConfig(
        name=config.get("name"),
        type=config.get("type"),
        model_id=config.get("model_id"),
        config=config.get("config"),
        description=config.get("description")
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.get("/data-sensing-configs")
def get_data_sensing_configs(db: Session = Depends(get_db)):
    return db.query(DataSensingConfig).all()

@router.get("/data-sensing-configs/{config_id}")
def get_data_sensing_config(config_id: int, db: Session = Depends(get_db)):
    config = db.query(DataSensingConfig).filter(DataSensingConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="DataSensingConfig not found")
    return config

@router.put("/data-sensing-configs/{config_id}")
def update_data_sensing_config(config_id: int, config: dict, db: Session = Depends(get_db)):
    db_config = db.query(DataSensingConfig).filter(DataSensingConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="DataSensingConfig not found")
    
    for key, value in config.items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config

@router.delete("/data-sensing-configs/{config_id}")
def delete_data_sensing_config(config_id: int, db: Session = Depends(get_db)):
    db_config = db.query(DataSensingConfig).filter(DataSensingConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="DataSensingConfig not found")
    
    db.delete(db_config)
    db.commit()
    return {"message": "DataSensingConfig deleted successfully"}
