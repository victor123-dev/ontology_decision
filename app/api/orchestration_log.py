"""
逻辑编排执行日志 API
存储在 MongoDB 的 orchestration_logs collection 中
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from app.utils.mongo_client import get_mongo_client
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

COLLECTION_NAME = "orchestration_logs"


def get_collection():
    client = get_mongo_client()
    return client.get_collection(COLLECTION_NAME)


@router.get("/orchestration-logs")
def get_orchestration_logs(
    orchestration_id: Optional[str] = Query(None, description="编排ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选: success/failed/running"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """获取编排执行日志列表"""
    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    query = {}
    if orchestration_id:
        query["orchestration_id"] = orchestration_id
    if status:
        query["status"] = status

    total = collection.count_documents(query)
    logs = list(collection.find(
        query,
        {"node_logs": 0}  # 列表时不返回节点详情
    ).sort("started_at", -1).skip((page - 1) * page_size).limit(page_size))

    for item in logs:
        item["id"] = str(item.pop("_id"))
        for field in ["started_at", "finished_at"]:
            if field in item and item[field]:
                if isinstance(item[field], datetime):
                    item[field] = item[field].isoformat()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": logs,
    }


@router.get("/orchestration-logs/{log_id}")
def get_orchestration_log(log_id: str):
    """获取单次执行日志详情（包含节点执行信息）"""
    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    from bson import ObjectId
    try:
        log = collection.find_one({"_id": ObjectId(log_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="无效的日志ID")

    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")

    log["id"] = str(log.pop("_id"))
    for field in ["started_at", "finished_at"]:
        if field in log and log[field]:
            if isinstance(log[field], datetime):
                log[field] = log[field].isoformat()

    # 获取编排的 graph_data 用于画布渲染
    orch_id = log.get("orchestration_id")
    if orch_id:
        orch_collection = get_mongo_client().get_collection("orchestrations")
        try:
            orchestration = orch_collection.find_one({"_id": ObjectId(orch_id)})
            if orchestration:
                log["graph_data"] = orchestration.get("graph_data", {})
        except Exception:
            pass

    return log


@router.delete("/orchestration-logs/{log_id}")
def delete_orchestration_log(log_id: str):
    """删除单条执行日志"""
    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    from bson import ObjectId
    try:
        obj_id = ObjectId(log_id)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的日志ID")

    result = collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="日志不存在")

    return {"message": "删除成功"}



