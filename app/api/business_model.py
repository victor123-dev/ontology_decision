from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.business_model import BusinessModel, BusinessModelField
from app.models.data_source import DataSource
from app.utils.llm_translator import LLMTranslator
from app.utils.shared_utils import get_db

router = APIRouter()

@router.post("/business-models")
def create_business_model(business_model: dict, db: Session = Depends(get_db)):
    db_business_model = BusinessModel(
        id=business_model.get("id"),
        name=business_model.get("name"),
        description=business_model.get("description"),
        primary_key_id=business_model.get("primary_key_id"),
        data_source_id=business_model.get("data_source_id")
    )
    db.add(db_business_model)
    db.commit()
    db.refresh(db_business_model)
    return db_business_model

@router.get("/business-models")
def get_business_models(db: Session = Depends(get_db)):
    models = db.query(BusinessModel).all()
    # 确保加载字段信息
    for model in models:
        _ = model.fields
    return models

@router.get("/business-models/{model_id}")
def get_business_model(model_id: str, db: Session = Depends(get_db)):
    business_model = db.query(BusinessModel).filter(BusinessModel.id == model_id).first()
    if not business_model:
        raise HTTPException(status_code=404, detail="BusinessModel not found")
    # 确保加载字段信息
    _ = business_model.fields
    return business_model

@router.put("/business-models/{model_id}")
def update_business_model(model_id: str, business_model: dict, db: Session = Depends(get_db)):
    db_business_model = db.query(BusinessModel).filter(BusinessModel.id == model_id).first()
    if not db_business_model:
        raise HTTPException(status_code=404, detail="BusinessModel not found")
    
    for key, value in business_model.items():
        setattr(db_business_model, key, value)
    
    db.commit()
    db.refresh(db_business_model)
    return db_business_model

@router.delete("/business-models/{model_id}")
def delete_business_model(model_id: str, db: Session = Depends(get_db)):
    db_business_model = db.query(BusinessModel).filter(BusinessModel.id == model_id).first()
    if not db_business_model:
        raise HTTPException(status_code=404, detail="BusinessModel not found")
    
    db.delete(db_business_model)
    db.commit()
    return {"message": "BusinessModel deleted successfully"}

@router.put("/business-models/{model_id}/fields/{field_id}")
def update_business_model_field(model_id: str, field_id: str, field_data: dict, db: Session = Depends(get_db)):
    # 检查模型是否存在
    business_model = db.query(BusinessModel).filter(BusinessModel.id == model_id).first()
    if not business_model:
        raise HTTPException(status_code=404, detail="BusinessModel not found")
    
    # 检查字段是否存在
    field = db.query(BusinessModelField).filter(
        BusinessModelField.model_id == model_id,
        BusinessModelField.field_id == field_id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    # 更新字段信息
    if "name" in field_data:
        field.name = field_data["name"]
    if "description" in field_data:
        field.description = field_data["description"]
    
    db.commit()
    db.refresh(field)
    return field

@router.post("/business-models/import")
def import_model(data: dict, db: Session = Depends(get_db)):
    data_source_id = data.get("data_source_id")
    table_name = data.get("table_name")
    model_id = data.get("model_id")  # 用于更新已有模型
    
    # 获取数据源
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    # 连接数据源，获取表结构
    client = DBClient(data_source.type, data_source.connection_string)
    client.connect()
    
    try:
        # 获取表列信息
        columns = client.get_table_columns(table_name)
        # 获取主键
        primary_keys = client.get_primary_keys(table_name)
        
        # 初始化LLM翻译器
        translator = LLMTranslator()
        
        # 检查是否存在模型
        existing_model = db.query(BusinessModel).filter(
            BusinessModel.id == (model_id or table_name)
        ).first()
        
        if existing_model:
            # 更新现有模型
            business_model = existing_model
        else:
            # 创建新模型
            business_model = BusinessModel(
                id=model_id or table_name,
                name=translator.translate_to_chinese(table_name),
                description=translator.generate_description(table_name),
                primary_key_id=primary_keys[0] if primary_keys else None,
                data_source_id=data_source_id
            )
            db.add(business_model)
        
        # 提取所有字段名用于批量翻译
        field_ids = [column['name'] for column in columns]
        
        # 批量翻译字段名称和描述
        field_names = translator.batch_translate(field_ids)
        field_descriptions = translator.batch_generate_descriptions(field_ids)
        
        # 处理字段
        for column in columns:
            field_id = column['name']
            # 检查字段是否存在
            existing_field = db.query(BusinessModelField).filter(
                BusinessModelField.model_id == business_model.id,
                BusinessModelField.field_id == field_id
            ).first()
            
            # 获取翻译结果
            field_name = field_names.get(field_id, field_id)
            field_description = field_descriptions.get(field_id, '')
            
            if existing_field:
                # 更新现有字段
                existing_field.data_type = str(column['type'])
                existing_field.name = field_name
                existing_field.description = field_description
            else:
                # 创建新字段
                field = BusinessModelField(
                    model_id=business_model.id,
                    field_id=field_id,
                    data_type=str(column['type']),
                    name=field_name,
                    description=field_description
                )
                db.add(field)
        
        db.commit()
        db.refresh(business_model)
        # 确保加载字段信息
        _ = business_model.fields
        return business_model
    finally:
        client.close()
