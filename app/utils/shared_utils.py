"""共享工具函数模块"""
from typing import Dict, Any, Optional
from datetime import datetime
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_db_session():
    """获取数据库会话（直接返回模式，用于引擎类等需要手动管理的场景）"""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return SessionLocal()


def get_db():
    """获取数据库会话（生成器模式，用于FastAPI Depends依赖注入）"""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_event_with_parent(level: str, category: str, message: str, data: Dict[str, Any] = None, trace_id: str = None, parent_id: int = None):
    """记录带父子关系的驱动日志"""
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
                trace_id=trace_id or str(uuid.uuid4()),
                parent_id=parent_id
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log.id
        finally:
            db.close()
    except Exception as e:
        logger.error(f"记录驱动日志失败: {str(e)}")
        return None