from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.data_source import DataSource
from app.utils.db_client import Base, create_engine, sessionmaker
from app.utils.data_source_manager import data_source_manager
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

@router.get("/test-data/{data_source_id}/{table_name}")
def get_test_data(
    data_source_id: int,
    table_name: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    query = f"SELECT * FROM {table_name} LIMIT {limit}"
    data = data_source_manager.execute_query(data_source_id=data_source_id, query=query, max_rows=limit)
    
    return {"data": data}

@router.post("/test-data/{data_source_id}/{table_name}")
def insert_test_data(
    data_source_id: int,
    table_name: str,
    data: dict,
    db: Session = Depends(get_db)
):
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    success = data_source_manager.execute_insert(data_source_id=data_source_id, table_name=table_name, data=data)
    
    if success:
        return {"message": "Data inserted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to insert data")

@router.delete("/test-data/{data_source_id}/{table_name}")
def delete_test_data(
    data_source_id: int,
    table_name: str,
    data: dict,
    db: Session = Depends(get_db)
):
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    if not data:
        raise HTTPException(status_code=400, detail="Delete conditions are required")
    
    success = data_source_manager.execute_delete(data_source_id=data_source_id, table_name=table_name, conditions=data)
    
    if success:
        return {"message": "Data deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete data")

@router.put("/test-data/{data_source_id}/{table_name}")
def update_test_data(
    data_source_id: int,
    table_name: str,
    data: dict,
    db: Session = Depends(get_db)
):
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    if not data:
        raise HTTPException(status_code=400, detail="Update data is required")
    
    success = data_source_manager.execute_update(data_source_id=data_source_id, table_name=table_name, data=data)
    
    if success:
        return {"message": "Data updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update data")
