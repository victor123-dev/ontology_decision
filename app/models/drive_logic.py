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

class DriveLogic(Base):
    __tablename__ = "drive_logics"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # first_order, script
    config = Column(JSON, nullable=False, default={})  # 可选的预处理配置
    description = Column(Text)
    natural_language_description = Column(Text)  # 自然语言描述，用于前端展示
    action_ids = Column(JSON, nullable=True, default=[])  # 关联的行动ID列表
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 多对多关系
    events = relationship("DataSensingConfig", secondary=event_logic_association, backref="logics")