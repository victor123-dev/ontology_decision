from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.data_source import DataSource
from app.utils.db_client import DBClient, Base, create_engine, sessionmaker

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

@router.get("/test-data/{data_source_id}/{table_name}")
def get_test_data(
    data_source_id: int,
    table_name: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    # 获取数据源
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    # 连接数据源并查询数据
    client = DBClient(data_source.type, data_source.connection_string)
    client.connect()
    
    try:
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        data = client.execute_query(query)
        return {"data": data}
    finally:
        client.close()

@router.post("/test-data/{data_source_id}/{table_name}")
def insert_test_data(
    data_source_id: int,
    table_name: str,
    data: dict,
    db: Session = Depends(get_db)
):
    # 获取数据源
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    # 连接数据源并插入数据
    client = DBClient(data_source.type, data_source.connection_string)
    client.connect()
    
    try:
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data.values()])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        # 执行插入
        if data_source.type == 'sqlite':
            import sqlite3
            conn = sqlite3.connect(data_source.connection_string.replace('sqlite:///', ''))
            cursor = conn.cursor()
            cursor.execute(query, list(data.values()))
            conn.commit()
            conn.close()
        
        return {"message": "Data inserted successfully"}
    finally:
        client.close()
