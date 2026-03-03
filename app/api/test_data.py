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

@router.delete("/test-data/{data_source_id}/{table_name}")
def delete_test_data(
    data_source_id: int,
    table_name: str,
    data: dict,
    db: Session = Depends(get_db)
):
    # 获取数据源
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    # 连接数据源并删除数据
    client = DBClient(data_source.type, data_source.connection_string)
    client.connect()
    
    try:
        # 构建删除条件
        conditions = []
        values = []
        for key, value in data.items():
            conditions.append(f"{key} = ?")
            values.append(value)
        
        if not conditions:
            raise HTTPException(status_code=400, detail="Delete conditions are required")
        
        condition_str = ' AND '.join(conditions)
        query = f"DELETE FROM {table_name} WHERE {condition_str}"
        
        # 执行删除
        if data_source.type == 'sqlite':
            import sqlite3
            conn = sqlite3.connect(data_source.connection_string.replace('sqlite:///', ''))
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            conn.close()
        
        return {"message": "Data deleted successfully"}
    finally:
        client.close()

@router.put("/test-data/{data_source_id}/{table_name}")
def update_test_data(
    data_source_id: int,
    table_name: str,
    data: dict,
    db: Session = Depends(get_db)
):
    # 获取数据源
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    # 连接数据源并更新数据
    client = DBClient(data_source.type, data_source.connection_string)
    client.connect()
    
    try:
        # 提取主键和更新值
        primary_key = None
        update_values = {}
        
        # 假设第一个字段为主键
        if data:
            primary_key = list(data.keys())[0]
            primary_value = data[primary_key]
            
            # 构建更新值
            for key, value in data.items():
                if key != primary_key:
                    update_values[key] = value
        
        if not primary_key or not update_values:
            raise HTTPException(status_code=400, detail="Primary key and update values are required")
        
        # 构建更新语句
        set_clause = ', '.join([f"{key} = ?" for key in update_values.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key} = ?"
        
        # 准备参数
        values = list(update_values.values()) + [primary_value]
        
        # 执行更新
        if data_source.type == 'sqlite':
            import sqlite3
            conn = sqlite3.connect(data_source.connection_string.replace('sqlite:///', ''))
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            conn.close()
        
        return {"message": "Data updated successfully"}
    finally:
        client.close()
