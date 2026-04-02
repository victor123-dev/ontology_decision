from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from app.utils.db_client import Base

class BusinessModelLink(Base):
    __tablename__ = "business_model_links"
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)  # 中文名称
    description = Column(Text)  # 中文说明
    source_model = Column(String(255), ForeignKey("business_models.id"), nullable=False)
    source_key = Column(String(255), nullable=False)  # 对应business_model_fields.field_id
    target_model = Column(String(255), ForeignKey("business_models.id"), nullable=False)
    target_key = Column(String(255), nullable=False)  # 对应business_model_fields.field_id
    cardinality = Column(String(50), nullable=False)  # "one-to-one", "one-to-many", "many-to-one", "many-to-many"
    # many-to-many 关系的中间表信息（仅在 cardinality = "many-to-many" 时使用）
    intermediate_model = Column(String(255), ForeignKey("business_models.id"))  # 中间表模型ID
    intermediate_source_key = Column(String(255))  # 中间表到源模型的外键字段
    intermediate_target_key = Column(String(255))  # 中间表到目标模型的外键字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 添加约束确保基数类型有效
    __table_args__ = (
        CheckConstraint(
            cardinality.in_(["one-to-one", "one-to-many", "many-to-one", "many-to-many"]),
            name="valid_cardinality"
        ),
    )