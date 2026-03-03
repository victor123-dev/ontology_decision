from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.agent import Agent, Capability
from app.utils.db_client import Base, create_engine, sessionmaker
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

@router.post("/agents")
def create_agent(agent: dict, db: Session = Depends(get_db)):
    db_agent = Agent(
        name=agent.get("name"),
        description=agent.get("description"),
        status=agent.get("status", "active")
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@router.get("/agents")
def get_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()

@router.get("/agents/{agent_id}")
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/agents/{agent_id}")
def update_agent(agent_id: int, agent: dict, db: Session = Depends(get_db)):
    db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    for key, value in agent.items():
        setattr(db_agent, key, value)
    
    db.commit()
    db.refresh(db_agent)
    return db_agent

@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(db_agent)
    db.commit()
    return {"message": "Agent deleted successfully"}

@router.post("/capabilities")
def create_capability(capability: dict, db: Session = Depends(get_db)):
    db_capability = Capability(
        name=capability.get("name"),
        task_type=capability.get("task_type"),
        description=capability.get("description")
    )
    db.add(db_capability)
    db.commit()
    db.refresh(db_capability)
    return db_capability

@router.get("/capabilities")
def get_capabilities(db: Session = Depends(get_db)):
    return db.query(Capability).all()

@router.post("/agents/{agent_id}/capabilities/{capability_id}")
def add_capability_to_agent(agent_id: int, capability_id: int, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    agent.capabilities.append(capability)
    db.commit()
    db.refresh(agent)
    return agent
