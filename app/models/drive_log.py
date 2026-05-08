from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.db_client import Base

class DriveLog(Base):
    __tablename__ = "drive_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)  # data_sensing, drive_logic, agent_task
    message = Column(Text, nullable=False)
    data = Column(JSON)
    trace_id = Column(String(100), autoincrement=True)  # 全局链路标识符
    parent_id = Column(Integer, ForeignKey("drive_logs.id"), nullable=True)  # 父日志ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 自引用关系
    parent = relationship("DriveLog", remote_side=[id])
