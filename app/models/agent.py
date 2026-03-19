from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.db_client import Base

# 多对多关联表
agent_capability_association = Table(
    'agent_capability_association',
    Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id')),
    Column('capability_id', Integer, ForeignKey('capabilities.id'))
)

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 多对多关系
    capabilities = relationship("Capability", secondary=agent_capability_association, backref="agents")
    # 一对多关系：任务实例
    task_instances = relationship("TaskInstance", back_populates="assigned_agent")

class Capability(Base):
    __tablename__ = "capabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
