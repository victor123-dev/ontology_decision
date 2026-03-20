"""共享工具函数模块"""
from typing import Dict, Any, Optional
from datetime import datetime
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_db_session():
    """获取数据库会话"""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def log_event(level: str, category: str, message: str, data: Dict[str, Any] = None, trace_id: str = None):
    """记录驱动日志"""
    try:
        import uuid
        from app.models.drive_log import DriveLog
        
        db = get_db_session()
        try:
            log = DriveLog(
                level=level,
                category=category,
                message=message,
                data=data,
                trace_id=trace_id or str(uuid.uuid4())
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"记录驱动日志失败: {str(e)}")