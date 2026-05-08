from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.utils.mongo_client import get_mongo_client
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

COLLECTION_NAME = "orchestrations"


def get_collection():
    client = get_mongo_client()
    return client.get_collection(COLLECTION_NAME)


class OrchestrationCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    graph_data: Optional[dict] = None


class OrchestrationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    graph_data: Optional[dict] = None


@router.post("/orchestrations")
def create_orchestration(data: OrchestrationCreate):
    """创建编排"""
    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    orchestration = {
        "name": data.name,
        "description": data.description,
        "graph_data": data.graph_data or {"nodes": [], "edges": []},
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    result = collection.insert_one(orchestration)
    orchestration["_id"] = str(result.inserted_id)
    orchestration["id"] = str(result.inserted_id)
    logger.info(f"创建编排: {orchestration['name']} (ID: {orchestration['_id']})")
    return orchestration


@router.get("/orchestrations")
def get_orchestrations():
    """获取编排列表"""
    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    orchestrations = list(collection.find(
        {},
        {"graph_data": 0}  # 列表时排除大数据字段
    ).sort("updated_at", -1))

    # 转换 ObjectId 为字符串
    for item in orchestrations:
        item["id"] = str(item.pop("_id"))
        if "created_at" in item:
            item["created_at"] = item["created_at"].isoformat()
        if "updated_at" in item:
            item["updated_at"] = item["updated_at"].isoformat()

    return orchestrations


@router.get("/orchestrations/{orchestration_id}")
def get_orchestration(orchestration_id: str):
    """获取单个编排"""
    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    from bson import ObjectId
    try:
        orchestration = collection.find_one({"_id": ObjectId(orchestration_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="无效的编排ID")

    if not orchestration:
        raise HTTPException(status_code=404, detail="编排不存在")

    orchestration["id"] = str(orchestration.pop("_id"))
    if "created_at" in orchestration:
        orchestration["created_at"] = orchestration["created_at"].isoformat()
    if "updated_at" in orchestration:
        orchestration["updated_at"] = orchestration["updated_at"].isoformat()

    return orchestration


@router.put("/orchestrations/{orchestration_id}")
def update_orchestration(orchestration_id: str, data: OrchestrationUpdate):
    """更新编排"""
    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    from bson import ObjectId
    try:
        obj_id = ObjectId(orchestration_id)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的编排ID")

    update_data = {"updated_at": datetime.now()}
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.graph_data is not None:
        update_data["graph_data"] = data.graph_data

    result = collection.update_one({"_id": obj_id}, {"$set": update_data})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="编排不存在")

    orchestration = collection.find_one({"_id": obj_id})
    orchestration["id"] = str(orchestration.pop("_id"))
    if "created_at" in orchestration:
        orchestration["created_at"] = orchestration["created_at"].isoformat()
    if "updated_at" in orchestration:
        orchestration["updated_at"] = orchestration["updated_at"].isoformat()

    logger.info(f"更新编排: {orchestration['name']} (ID: {orchestration_id})")
    return orchestration


@router.delete("/orchestrations/{orchestration_id}")
def delete_orchestration(orchestration_id: str):
    """删除编排"""
    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    from bson import ObjectId
    try:
        obj_id = ObjectId(orchestration_id)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的编排ID")

    result = collection.delete_one({"_id": obj_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="编排不存在")

    logger.info(f"删除编排: {orchestration_id}")
    return {"message": "删除成功"}
