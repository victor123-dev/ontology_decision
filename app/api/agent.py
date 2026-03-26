from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.agent import Agent, Capability
from app.utils.shared_utils import get_db

router = APIRouter()

@router.post("/agents")
def create_agent(agent: dict, db: Session = Depends(get_db)):
    db_agent = Agent(
        name=agent.get("name"),
        description=agent.get("description"),
        status=agent.get("status", "active")
    )
    
    # 处理能力分配
    capability_ids = agent.get("capability_ids")
    if capability_ids:
        capabilities = db.query(Capability).filter(Capability.id.in_(capability_ids)).all()
        db_agent.capabilities = capabilities
    
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@router.get("/agents")
def get_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    result = []
    for agent in agents:
        agent_dict = {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "status": agent.status,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "capabilities": [
                {"id": cap.id, "name": cap.name}
                for cap in agent.capabilities
            ]
        }
        result.append(agent_dict)
    return result

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
    
    # 处理能力分配
    if "capability_ids" in agent:
        capability_ids = agent.pop("capability_ids")
        if capability_ids:
            capabilities = db.query(Capability).filter(Capability.id.in_(capability_ids)).all()
            db_agent.capabilities = capabilities
        else:
            db_agent.capabilities = []
    
    # 更新其他字段
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
        description=capability.get("description")
    )
    db.add(db_capability)
    db.commit()
    db.refresh(db_capability)
    return db_capability

@router.get("/capabilities")
def get_capabilities(db: Session = Depends(get_db)):
    return db.query(Capability).all()

@router.put("/capabilities/{capability_id}")
def update_capability(capability_id: int, capability: dict, db: Session = Depends(get_db)):
    db_capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not db_capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    for key, value in capability.items():
        setattr(db_capability, key, value)
    
    db.commit()
    db.refresh(db_capability)
    return db_capability

@router.delete("/capabilities/{capability_id}")
def delete_capability(capability_id: int, db: Session = Depends(get_db)):
    db_capability = db.query(Capability).filter(Capability.id == capability_id).first()
    if not db_capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    db.delete(db_capability)
    db.commit()
    return {"message": "Capability deleted successfully"}


