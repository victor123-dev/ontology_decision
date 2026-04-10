from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.business_model_link import BusinessModelLink
from app.models.business_model import BusinessModel, BusinessModelField
from app.utils.shared_utils import get_db

router = APIRouter()

@router.post("/business-model-links")
def create_business_model_link(link_data: dict, db: Session = Depends(get_db)):
    # 验证源模型和目标模型是否存在
    source_model = db.query(BusinessModel).filter(BusinessModel.id == link_data.get("source_model")).first()
    target_model = db.query(BusinessModel).filter(BusinessModel.id == link_data.get("target_model")).first()
    
    if not source_model:
        raise HTTPException(status_code=404, detail="Source model not found")
    if not target_model:
        raise HTTPException(status_code=404, detail="Target model not found")
    
    # 验证源字段和目标字段是否存在
    source_field = db.query(BusinessModelField).filter(
        BusinessModelField.model_id == link_data.get("source_model"),
        BusinessModelField.field_id == link_data.get("source_key")
    ).first()
    
    target_field = db.query(BusinessModelField).filter(
        BusinessModelField.model_id == link_data.get("target_model"),
        BusinessModelField.field_id == link_data.get("target_key")
    ).first()
    
    if not source_field:
        raise HTTPException(status_code=404, detail="Source field not found")
    if not target_field:
        raise HTTPException(status_code=404, detail="Target field not found")
    
    # 验证基数约束
    cardinality = link_data.get("cardinality")
    if cardinality not in ["one-to-one", "one-to-many", "many-to-one", "many-to-many"]:
        raise HTTPException(status_code=400, detail="Invalid cardinality")
    
    # 验证主键约束
    if cardinality == "one-to-many":
        # one侧必须是主键
        if source_model.primary_key_id != link_data.get("source_key"):
            raise HTTPException(status_code=400, detail="For one-to-many relationship, the 'one' side (source) must use primary key")
    elif cardinality == "many-to-one":
        # one侧必须是主键
        if target_model.primary_key_id != link_data.get("target_key"):
            raise HTTPException(status_code=400, detail="For many-to-one relationship, the 'one' side (target) must use primary key")
    elif cardinality == "one-to-one":
        # 至少一侧必须是主键
        if (source_model.primary_key_id != link_data.get("source_key") and 
            target_model.primary_key_id != link_data.get("target_key")):
            raise HTTPException(status_code=400, detail="For one-to-one relationship, at least one side must use primary key")
    elif cardinality == "many-to-many":
        # many-to-many 关系需要中间表信息
        intermediate_model_id = link_data.get("intermediate_model")
        intermediate_source_key = link_data.get("intermediate_source_key")
        intermediate_target_key = link_data.get("intermediate_target_key")
        
        if not intermediate_model_id or not intermediate_source_key or not intermediate_target_key:
            raise HTTPException(status_code=400, detail="For many-to-many relationship, intermediate model and keys are required")
        
        # 验证中间模型是否存在
        intermediate_model = db.query(BusinessModel).filter(BusinessModel.id == intermediate_model_id).first()
        if not intermediate_model:
            raise HTTPException(status_code=404, detail="Intermediate model not found")
        
        # 验证中间表的字段是否存在
        intermediate_source_field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == intermediate_model_id,
            BusinessModelField.field_id == intermediate_source_key
        ).first()
        intermediate_target_field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == intermediate_model_id,
            BusinessModelField.field_id == intermediate_target_key
        ).first()
        
        if not intermediate_source_field:
            raise HTTPException(status_code=404, detail="Intermediate source field not found")
        if not intermediate_target_field:
            raise HTTPException(status_code=404, detail="Intermediate target field not found")
        
        # 验证中间表字段是否正确引用源模型和目标模型的主键
        if source_model.primary_key_id != link_data.get("source_key"):
            raise HTTPException(status_code=400, detail="For many-to-many relationship, source key must be the primary key of source model")
        if target_model.primary_key_id != link_data.get("target_key"):
            raise HTTPException(status_code=400, detail="For many-to-many relationship, target key must be the primary key of target model")
    
    # 创建关系
    db_link = BusinessModelLink(
        id=link_data.get("id"),
        name=link_data.get("name"),
        description=link_data.get("description"),
        source_model=link_data.get("source_model"),
        source_api_name=link_data.get("source_api_name"),
        source_key=link_data.get("source_key"),
        target_model=link_data.get("target_model"),
        target_api_name=link_data.get("target_api_name"),
        target_key=link_data.get("target_key"),
        cardinality=cardinality,
        intermediate_model=link_data.get("intermediate_model"),
        intermediate_source_key=link_data.get("intermediate_source_key"),
        intermediate_target_key=link_data.get("intermediate_target_key")
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

@router.get("/business-model-links")
def get_business_model_links(db: Session = Depends(get_db)):
    links = db.query(BusinessModelLink).all()
    return links

@router.get("/business-model-links/{link_id}")
def get_business_model_link(link_id: str, db: Session = Depends(get_db)):
    link = db.query(BusinessModelLink).filter(BusinessModelLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="BusinessModelLink not found")
    return link

@router.put("/business-model-links/{link_id}")
def update_business_model_link(link_id: str, link_data: dict, db: Session = Depends(get_db)):
    db_link = db.query(BusinessModelLink).filter(BusinessModelLink.id == link_id).first()
    if not db_link:
        raise HTTPException(status_code=404, detail="BusinessModelLink not found")
    
    # 执行与创建时相同的验证逻辑
    source_model = db.query(BusinessModel).filter(BusinessModel.id == link_data.get("source_model", db_link.source_model)).first()
    target_model = db.query(BusinessModel).filter(BusinessModel.id == link_data.get("target_model", db_link.target_model)).first()
    
    if not source_model:
        raise HTTPException(status_code=404, detail="Source model not found")
    if not target_model:
        raise HTTPException(status_code=404, detail="Target model not found")
    
    source_key = link_data.get("source_key", db_link.source_key)
    target_key = link_data.get("target_key", db_link.target_key)
    
    source_field = db.query(BusinessModelField).filter(
        BusinessModelField.model_id == link_data.get("source_model", db_link.source_model),
        BusinessModelField.field_id == source_key
    ).first()
    
    target_field = db.query(BusinessModelField).filter(
        BusinessModelField.model_id == link_data.get("target_model", db_link.target_model),
        BusinessModelField.field_id == target_key
    ).first()
    
    if not source_field:
        raise HTTPException(status_code=404, detail="Source field not found")
    if not target_field:
        raise HTTPException(status_code=404, detail="Target field not found")
    
    cardinality = link_data.get("cardinality", db_link.cardinality)
    if cardinality not in ["one-to-one", "one-to-many", "many-to-one", "many-to-many"]:
        raise HTTPException(status_code=400, detail="Invalid cardinality")
    
    # 验证主键约束
    if cardinality == "one-to-many":
        if source_model.primary_key_id != source_key:
            raise HTTPException(status_code=400, detail="For one-to-many relationship, the 'one' side (source) must use primary key")
    elif cardinality == "many-to-one":
        if target_model.primary_key_id != target_key:
            raise HTTPException(status_code=400, detail="For many-to-one relationship, the 'one' side (target) must use primary key")
    elif cardinality == "one-to-one":
        if (source_model.primary_key_id != source_key and 
            target_model.primary_key_id != target_key):
            raise HTTPException(status_code=400, detail="For one-to-one relationship, at least one side must use primary key")
    elif cardinality == "many-to-many":
        # many-to-many 关系需要中间表信息
        intermediate_model_id = link_data.get("intermediate_model", db_link.intermediate_model)
        intermediate_source_key = link_data.get("intermediate_source_key", db_link.intermediate_source_key)
        intermediate_target_key = link_data.get("intermediate_target_key", db_link.intermediate_target_key)
        
        if not intermediate_model_id or not intermediate_source_key or not intermediate_target_key:
            raise HTTPException(status_code=400, detail="For many-to-many relationship, intermediate model and keys are required")
        
        # 验证中间模型是否存在
        intermediate_model = db.query(BusinessModel).filter(BusinessModel.id == intermediate_model_id).first()
        if not intermediate_model:
            raise HTTPException(status_code=404, detail="Intermediate model not found")
        
        # 验证中间表的字段是否存在
        intermediate_source_field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == intermediate_model_id,
            BusinessModelField.field_id == intermediate_source_key
        ).first()
        intermediate_target_field = db.query(BusinessModelField).filter(
            BusinessModelField.model_id == intermediate_model_id,
            BusinessModelField.field_id == intermediate_target_key
        ).first()
        
        if not intermediate_source_field:
            raise HTTPException(status_code=404, detail="Intermediate source field not found")
        if not intermediate_target_field:
            raise HTTPException(status_code=404, detail="Intermediate target field not found")
        
        # 验证中间表字段是否正确引用源模型和目标模型的主键
        if source_model.primary_key_id != source_key:
            raise HTTPException(status_code=400, detail="For many-to-many relationship, source key must be the primary key of source model")
        if target_model.primary_key_id != target_key:
            raise HTTPException(status_code=400, detail="For many-to-many relationship, target key must be the primary key of target model")
    
    # 更新字段
    for key, value in link_data.items():
        if hasattr(db_link, key):
            setattr(db_link, key, value)
    
    db.commit()
    db.refresh(db_link)
    return db_link

@router.delete("/business-model-links/{link_id}")
def delete_business_model_link(link_id: str, db: Session = Depends(get_db)):
    db_link = db.query(BusinessModelLink).filter(BusinessModelLink.id == link_id).first()
    if not db_link:
        raise HTTPException(status_code=404, detail="BusinessModelLink not found")
    
    db.delete(db_link)
    db.commit()
    return {"message": "BusinessModelLink deleted successfully"}

@router.get("/business-models/{model_id}/links")
def get_business_model_links_by_model(model_id: str, db: Session = Depends(get_db)):
    # 获取与指定模型相关的所有链接（作为源或目标）
    links = db.query(BusinessModelLink).filter(
        (BusinessModelLink.source_model == model_id) | 
        (BusinessModelLink.target_model == model_id)
    ).all()
    return links