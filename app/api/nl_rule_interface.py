from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.utils.llm_translator import llm_translator
from app.models.business_model import BusinessModel
from app.models.data_sensing import DataSensingConfig
from app.models.drive_logic import Task
from app.utils.shared_utils import get_db

router = APIRouter()

@router.post("/nl-rule-interface/parse-sensing-config")
def parse_natural_language_to_sensing_config(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """将自然语言解析为数据感知配置"""
    natural_language = request_data.get("natural_language", "")
    if not natural_language:
        raise HTTPException(status_code=400, detail="自然语言描述不能为空")
    
    try:
        # 获取所有业务模型
        business_models = []
        models = db.query(BusinessModel).all()
        for model in models:
            db.refresh(model)
            business_models.append({
                "id": model.id,
                "name": model.name,
                "fields": [{"field_id": f.field_id, "name": f.name, "data_type": f.data_type} for f in model.fields] if model.fields else []
            })
        
        # 调用LLM解析（已包含少样本示例和验证）
        config = llm_translator.parse_natural_language_to_sensing_config(
            natural_language, business_models
        )
        
        if not config:
            raise HTTPException(status_code=400, detail="无法解析自然语言描述，请参考示例格式")
        
        return {
            "success": True,
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@router.post("/nl-rule-interface/parse-drive-logic")
def parse_natural_language_to_drive_logic(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """将自然语言解析为驱动逻辑配置"""
    natural_language = request_data.get("natural_language", "")
    if not natural_language:
        raise HTTPException(status_code=400, detail="自然语言描述不能为空")
    
    try:
        # 获取所有任务和事件
        tasks = []
        task_list = db.query(Task).all()
        for task in task_list:
            db.refresh(task)
            tasks.append({
                "id": task.id,
                "name": task.name,
                "capability_ids": [cap.id for cap in task.capabilities] if task.capabilities else [],
                "capability_names": [cap.name for cap in task.capabilities] if task.capabilities else []
            })
        
        events = []
        event_list = db.query(DataSensingConfig).all()
        for event in event_list:
            db.refresh(event)
            events.append({
                "id": event.id,
                "name": event.name,
                "type": event.type,
                "model_id": event.model_id,
            })
        
        # 调用LLM解析（已包含少样本示例和验证）
        logic = llm_translator.parse_natural_language_to_drive_logic(
            natural_language, tasks, events
        )
        
        if not logic:
            raise HTTPException(status_code=400, detail="无法解析自然语言描述，请参考示例格式")
        
        return {
            "success": True,
            "logic": logic
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@router.post("/nl-rule-interface/explain-sensing-config")
def explain_sensing_config_in_natural_language(
    config: dict
):
    """将数据感知配置转换为自然语言描述"""
    try:
        explanation = llm_translator.convert_sensing_config_to_natural_language(config)
        return {
            "success": True,
            "explanation": explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")

@router.post("/nl-rule-interface/explain-drive-logic")
def explain_drive_logic_in_natural_language(
    logic: dict
):
    """将驱动逻辑配置转换为自然语言描述"""
    try:
        explanation = llm_translator.convert_drive_logic_to_natural_language(logic)
        return {
            "success": True,
            "explanation": explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")