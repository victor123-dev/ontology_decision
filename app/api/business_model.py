from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.business_model import BusinessModel, BusinessModelField
from app.models.business_model_link import BusinessModelLink
from app.models.data_source import DataSource
from app.utils.db_client import DBClient
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
        # 获取外键信息
        foreign_keys = client.get_foreign_keys(table_name)
        
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
        
        # 收集所有相关表的信息用于大模型关系推断
        tables_info = {}
        
        # 添加当前表信息
        tables_info[table_name] = {
            'columns': [col['name'] for col in columns],
            'primary_key': primary_keys[0] if primary_keys else None,
            'foreign_keys': foreign_keys
        }
        
        # 获取所有其他表的信息（用于关系推断）
        all_tables = client.get_tables()
        for other_table in all_tables:
            if other_table != table_name:
                try:
                    other_columns = client.get_table_columns(other_table)
                    other_pks = client.get_primary_keys(other_table)
                    other_fks = client.get_foreign_keys(other_table)
                    
                    tables_info[other_table] = {
                        'columns': [col['name'] for col in other_columns],
                        'primary_key': other_pks[0] if other_pks else None,
                        'foreign_keys': other_fks
                    }
                except Exception as e:
                    print(f"Warning: Could not get info for table {other_table}: {e}")
                    continue
        
        # 使用大模型推断关系
        inferred_relationships = translator.infer_relationships(tables_info)
        
        # 创建推断出的关系
        created_links = []
        for rel in inferred_relationships:
            try:
                source_table = rel['source_table']
                source_field = rel['source_field']
                target_table = rel['target_table']
                target_field = rel['target_field']
                cardinality = rel['cardinality']
                name = rel['name']
                description = rel['description']
                intermediate_table = rel.get('intermediate_table')
                intermediate_source_key = rel.get('intermediate_source_key')
                intermediate_target_key = rel.get('intermediate_target_key')
                
                # 确保源表和目标表都存在业务模型
                source_model = db.query(BusinessModel).filter(
                    BusinessModel.id == source_table,
                    BusinessModel.data_source_id == data_source_id
                ).first()
                
                target_model = db.query(BusinessModel).filter(
                    BusinessModel.id == target_table,
                    BusinessModel.data_source_id == data_source_id
                ).first()
                
                # 如果模型不存在，创建它们
                if not source_model:
                    source_columns_info = client.get_table_columns(source_table)
                    source_pks = client.get_primary_keys(source_table)
                    source_model = BusinessModel(
                        id=source_table,
                        name=translator.translate_to_chinese(source_table),
                        description=translator.generate_description(source_table),
                        primary_key_id=source_pks[0] if source_pks else None,
                        data_source_id=data_source_id
                    )
                    db.add(source_model)
                    db.flush()
                    
                    # 创建源表字段
                    source_field_ids = [col['name'] for col in source_columns_info]
                    source_field_names = translator.batch_translate(source_field_ids)
                    source_field_descriptions = translator.batch_generate_descriptions(source_field_ids)
                    for col in source_columns_info:
                        field = BusinessModelField(
                            model_id=source_model.id,
                            field_id=col['name'],
                            data_type=str(col['type']),
                            name=source_field_names.get(col['name'], col['name']),
                            description=source_field_descriptions.get(col['name'], '')
                        )
                        db.add(field)
                
                if not target_model:
                    target_columns_info = client.get_table_columns(target_table)
                    target_pks = client.get_primary_keys(target_table)
                    target_model = BusinessModel(
                        id=target_table,
                        name=translator.translate_to_chinese(target_table),
                        description=translator.generate_description(target_table),
                        primary_key_id=target_pks[0] if target_pks else None,
                        data_source_id=data_source_id
                    )
                    db.add(target_model)
                    db.flush()
                    
                    # 创建目标表字段
                    target_field_ids = [col['name'] for col in target_columns_info]
                    target_field_names = translator.batch_translate(target_field_ids)
                    target_field_descriptions = translator.batch_generate_descriptions(target_field_ids)
                    for col in target_columns_info:
                        field = BusinessModelField(
                            model_id=target_model.id,
                            field_id=col['name'],
                            data_type=str(col['type']),
                            name=target_field_names.get(col['name'], col['name']),
                            description=target_field_descriptions.get(col['name'], '')
                        )
                        db.add(field)
                
                # 生成关系ID
                if cardinality == 'many-to-many' and intermediate_table:
                    link_id = f"{source_table}_to_{target_table}_via_{intermediate_table}"
                else:
                    link_id = f"{source_table}_{source_field}_to_{target_table}_{target_field}"
                
                # 检查关系是否已存在
                existing_link = db.query(BusinessModelLink).filter(
                    BusinessModelLink.id == link_id
                ).first()
                
                if not existing_link:
                    link_kwargs = {
                        'id': link_id,
                        'name': name,
                        'description': description,
                        'source_model': source_model.id,
                        'source_key': source_field,
                        'target_model': target_model.id,
                        'target_key': target_field,
                        'cardinality': cardinality
                    }
                    
                    # 处理 many-to-many 关系的中间表字段
                    if cardinality == 'many-to-many' and intermediate_table:
                        link_kwargs['intermediate_model'] = intermediate_table
                        # 优先使用大模型返回的中间表字段信息
                        if intermediate_source_key and intermediate_target_key:
                            link_kwargs['intermediate_source_key'] = intermediate_source_key
                            link_kwargs['intermediate_target_key'] = intermediate_target_key
                        else:
                            # 如果大模型没有提供，尝试从中间表获取对应的外键字段
                            intermediate_info = tables_info.get(intermediate_table, {})
                            intermediate_fks = intermediate_info.get('foreign_keys', [])
                            
                            # 找到指向源表和目标表的外键
                            source_fk = None
                            target_fk = None
                            for fk in intermediate_fks:
                                referred_table = fk.get('referred_table')
                                if referred_table == source_table:
                                    source_fk = fk.get('constrained_columns', [None])[0]
                                elif referred_table == target_table:
                                    target_fk = fk.get('constrained_columns', [None])[0]
                            
                            if source_fk and target_fk:
                                link_kwargs['intermediate_source_key'] = source_fk
                                link_kwargs['intermediate_target_key'] = target_fk
                    
                    link = BusinessModelLink(**link_kwargs)
                    db.add(link)
                    created_links.append(link)
                    
            except Exception as e:
                print(f"Warning: Could not create relationship {rel.get('name', 'unknown')}: {e}")
                continue
        
        db.commit()
        db.refresh(business_model)
        # 确保加载字段信息
        _ = business_model.fields
        return business_model
    finally:
        client.close()
