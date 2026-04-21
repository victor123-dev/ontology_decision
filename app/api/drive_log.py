from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.drive_log import DriveLog
from app.utils.shared_utils import get_db

router = APIRouter()

@router.get("/drive-logs/trace/{trace_id}")
def get_trace_chain_api(trace_id: str, db: Session = Depends(get_db)):
    """获取完整的链路追踪信息"""
    try:
        logs = db.query(DriveLog).filter(DriveLog.trace_id == trace_id).order_by(DriveLog.created_at).all()
        
        if not logs:
            raise HTTPException(status_code=404, detail="Trace ID not found")
        
        # 构建树形结构
        log_dict = {log.id: {
            "id": log.id,
            "level": log.level,
            "category": log.category,
            "message": log.message,
            "data": log.data,
            "trace_id": log.trace_id,
            "parent_id": log.parent_id,
            "created_at": log.created_at,
            "children": []
        } for log in logs}
        
        root_logs = []
        for log_id, log_data in log_dict.items():
            if log_data["parent_id"] is None:
                root_logs.append(log_data)
            else:
                parent = log_dict.get(log_data["parent_id"])
                if parent:
                    parent["children"].append(log_data)
        
        return {
            "success": True,
            "trace_id": trace_id,
            "chain": root_logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取链路信息失败: {str(e)}")

@router.get("/drive-logs/traces")
def get_all_traces(limit: int = 100,offset: int = 0,db: Session = Depends(get_db)):
    """获取所有链路摘要信息"""
    try:
        # 获取所有唯一的trace_id
        trace_ids = db.query(DriveLog.trace_id).distinct().order_by(DriveLog.created_at.desc()).limit(limit).offset(offset).all()
        
        traces = []
        for trace_id_tuple in trace_ids:
            trace_id = trace_id_tuple[0]
            # 获取该trace的所有日志
            all_logs = db.query(DriveLog).filter(DriveLog.trace_id == trace_id).order_by(DriveLog.created_at.desc()).all()
            if all_logs:
                latest_log = all_logs[0]  # 最新日志
                
                # 检查是否有error级别的日志
                has_error = any(log.level == 'error' for log in all_logs)
                
                traces.append({
                    "trace_id": trace_id,
                    "latest_message": latest_log.message,
                    "latest_level": 'error' if has_error else latest_log.level,
                    "latest_category": latest_log.category,
                    "latest_time": latest_log.created_at,
                    "log_count": len(all_logs)
                })
        
        return {
            "success": True,
            "traces": traces,
            "total": db.query(DriveLog.trace_id).distinct().count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取链路列表失败: {str(e)}")