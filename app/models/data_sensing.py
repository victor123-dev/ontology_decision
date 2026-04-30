from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from app.utils.db_client import Base

class DataSensingConfig(Base):
    __tablename__ = "data_sensing_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # data_change, threshold
    model_id = Column(String(255), ForeignKey("business_models.id"))
    config = Column(JSON, nullable=False)  # 配置参数
    description = Column(Text)
    natural_language_description = Column(Text)  # 自然语言描述，用于前端展示
    status = Column(Boolean, default=True, nullable=False)  # True: active, False: inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
