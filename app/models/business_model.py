from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.db_client import Base

class BusinessModel(Base):
    __tablename__ = "business_models"
    
    id = Column(String(255), primary_key=True)  # 映射表名
    api_name = Column(String(255))  # API名称，基于id自动生成的小驼峰命名
    name = Column(String(255), nullable=False)  # 中文名称
    description = Column(Text)  # 中文说明
    primary_key_id = Column(String(255))  # 主键ID
    data_source_id = Column(Integer, ForeignKey("data_sources.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    fields = relationship("BusinessModelField", back_populates="model", cascade="all, delete-orphan")

class BusinessModelField(Base):
    __tablename__ = "business_model_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(255), ForeignKey("business_models.id"))
    field_id = Column(String(255), nullable=False)  # 映射字段名
    data_type = Column(String(100), nullable=False)  # 通用数据类型
    name = Column(String(255), nullable=False)  # 中文名称
    description = Column(Text)  # 中文说明
    required = Column(Boolean, default=False)  # 是否必填，默认False
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    model = relationship("BusinessModel", back_populates="fields")
