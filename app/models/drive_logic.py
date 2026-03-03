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
    config = Column(JSON, nullable=False)  # 配置参数
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
    type = Column(String(100), nullable=False)
    config = Column(JSON)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
