from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.data_source import DataSource
from app.utils.db_client import DBClient
from app.utils.shared_utils import get_db
router = APIRouter()

@router.post("/data-sources")
def create_data_source(data_source: dict, db: Session = Depends(get_db)):
    db_data_source = DataSource(
        name=data_source.get("name"),
        type=data_source.get("type"),
        connection_string=data_source.get("connection_string"),
        description=data_source.get("description")
    )
    db.add(db_data_source)
    db.commit()
    db.refresh(db_data_source)
    return db_data_source

@router.get("/data-sources")
def get_data_sources(db: Session = Depends(get_db)):
    return db.query(DataSource).all()

@router.get("/data-sources/{data_source_id}")
def get_data_source(data_source_id: int, db: Session = Depends(get_db)):
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    return data_source

@router.put("/data-sources/{data_source_id}")
def update_data_source(data_source_id: int, data_source: dict, db: Session = Depends(get_db)):
    db_data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not db_data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    for key, value in data_source.items():
        setattr(db_data_source, key, value)
    
    db.commit()
    db.refresh(db_data_source)
    return db_data_source

@router.delete("/data-sources/{data_source_id}")
def delete_data_source(data_source_id: int, db: Session = Depends(get_db)):
    db_data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not db_data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    db.delete(db_data_source)
    db.commit()
    return {"message": "DataSource deleted successfully"}

@router.post("/data-sources/{data_source_id}/test-connection")
def test_connection(data_source_id: int, db: Session = Depends(get_db)):
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    try:
        client = DBClient(data_source.type, data_source.connection_string)
        client.connect()
        client.close()
        return {"status": "success", "message": "Connection successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

@router.get("/data-sources/{data_source_id}/tables")
def get_tables(data_source_id: int, db: Session = Depends(get_db)):
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    try:
        client = DBClient(data_source.type, data_source.connection_string)
        tables = client.get_tables()
        client.close()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get tables: {str(e)}")
