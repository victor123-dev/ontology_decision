from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.db_client import Base

# 多对多关联表
event_logic_association = Table(
    'event_logic_association',
    Base.metadata,
    Column('event_id', Integer, ForeignKey('data_sensing_configs.id')),
    Column('logic_id', Integer, ForeignKey('drive_logics.id'))
)

logic_task_association = Table(
    'logic_task_association',
    Base.metadata,
    Column('logic_id', Integer, ForeignKey('drive_logics.id')),
    Column('task_id', Integer, ForeignKey('tasks.id'))
)

class DriveLogic(Base):
    __tablename__ = "drive_logics"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # first_order, script
    config = Column(JSON, nullable=False, default={})  # 可选的预处理配置
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 多对多关系
    events = relationship("DataSensingConfig", secondary=event_logic_association, backref="logics")
    tasks = relationship("Task", secondary=logic_task_association, backref="logics")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    capability_type = Column(String(100), nullable=False)  # 能力类型，用于匹配Agent
    config = Column(JSON)  # 任务配置参数
    description = Column(Text)
    assigned_agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联Agent
    assigned_agent = relationship("Agent", back_populates="tasks")
    # 关联任务实例
    instances = relationship("TaskInstance", back_populates="task")

class TaskInstance(Base):
    __tablename__ = "task_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    status = Column(String(50), default="pending")  # pending, assigned, completed, failed
    result = Column(JSON)  # 任务执行结果
    assigned_agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关联任务
    task = relationship("Task", back_populates="instances")
    # 关联Agent
    assigned_agent = relationship("Agent")
