from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.utils.shared_utils import get_db
from app.models.data_sensing import DataSensingConfig
from app.engines.data_sensing_engine import data_sensing_engine
from app.utils.background_task_processor import background_task_processor
from app.utils.natural_language_generator import generate_natural_language_description_for_sensing_config

router = APIRouter()

@router.post("/data-sensing-configs")
def create_data_sensing_config(config: dict, db: Session = Depends(get_db)):
    db_config = DataSensingConfig(
        name=config.get("name"),
        type=config.get("type"),
        model_id=config.get("model_id"),
        config=config.get("config"),
        description=config.get("description"),
        natural_language_description=None,  # 初始化为空
        status=config.get("status", True)
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    # 通知引擎添加调度任务
    try:
        data_sensing_engine.add_config(db_config)
    except Exception as e:
        # 记录错误但不影响API返回
        import logging
        logging.getLogger(__name__).error(f"添加调度任务失败: {e}")
    
    # 触发异步任务生成自然语言描述
    background_task_processor.submit_task(
        generate_natural_language_description_for_sensing_config, 
        db_config.id
    )
    
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
    
    # 如果配置有实质性变化，重置自然语言描述
    should_regenerate_description = False
    for key, value in config.items():
        if key in ['name', 'type', 'model_id', 'config', 'description'] and getattr(db_config, key) != value:
            should_regenerate_description = True
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    
    # 通知引擎更新调度任务
    try:
        data_sensing_engine.update_config(db_config)
    except Exception as e:
        # 记录错误但不影响API返回
        import logging
        logging.getLogger(__name__).error(f"更新调度任务失败: {e}")
    
    # 如果需要重新生成描述，触发异步任务
    if should_regenerate_description:
        background_task_processor.submit_task(
            generate_natural_language_description_for_sensing_config, 
            db_config.id
        )
    
    return db_config

@router.delete("/data-sensing-configs/{config_id}")
def delete_data_sensing_config(config_id: int, db: Session = Depends(get_db)):
    db_config = db.query(DataSensingConfig).filter(DataSensingConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="DataSensingConfig not found")
    
    db.delete(db_config)
    db.commit()
    
    # 通知引擎移除调度任务
    try:
        data_sensing_engine.remove_config(config_id)
    except Exception as e:
        # 记录错误但不影响API返回
        import logging
        logging.getLogger(__name__).error(f"移除调度任务失败: {e}")
    
    return {"message": "DataSensingConfig deleted successfully"}
