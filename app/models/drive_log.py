from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.utils.db_client import Base

class DriveLog(Base):
    __tablename__ = "drive_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)  # data_sensing, drive_logic, agent_task
    message = Column(Text, nullable=False)
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
