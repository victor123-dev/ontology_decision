from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.data_sensing import DataSensingConfig
from app.utils.shared_utils import get_db
from app.engines.drive_engine import drive_engine
import time
import uuid

router = APIRouter()

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
    event_payload = event_data.get("data", {})
    
    # 验证配置是否存在
    config = db.query(DataSensingConfig).filter(DataSensingConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="DataSensingConfig not found")
    
    # 构建完整的事件对象
    trace_id = str(uuid.uuid4())
    event = {
        "type": config.name,  # 使用配置名称作为事件类型
        "model_id": config.model_id,  # 从配置中获取模型ID
        "data": {
            "config_id": config_id,
            "config_name": config.name,
            "affected_records": [{"record": event_payload}]
        },
        "timestamp": time.time(),
        "trace_id": trace_id
    }
    
    # 触发数据驱动引擎的处理流程
    drive_engine.handle_event(event)
    
    return {
        "message": "Event simulated successfully",
        "config": config.name,
        "data": event_payload,
        "trace_id": trace_id
    }
