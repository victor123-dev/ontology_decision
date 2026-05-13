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


@router.post("/orchestrations/{orchestration_id}/execute")
def execute_orchestration(orchestration_id: str, request_data: Optional[dict] = None):
    """执行编排并返回执行结果"""
    from app.services.dag_service import execute_orchestration_by_id

    result = execute_orchestration_by_id(orchestration_id, request_data)

    if result.get("error") == "编排不存在":
        raise HTTPException(status_code=404, detail="编排不存在")
    elif result.get("error") == "编排内容为空":
        raise HTTPException(status_code=400, detail="编排内容为空，无法执行")
    elif result.get("error") == "无效的编排ID":
        raise HTTPException(status_code=400, detail="无效的编排ID")

    return result


class ParameterSchema(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    is_enum: bool = False
    enum_values: list = []


class OrchestrationSaveWithActionRequest(BaseModel):
    id: Optional[str] = None  # 编排ID，更新时传入
    name: str
    description: Optional[str] = ""
    graph_data: Optional[dict] = None
    inputs: Optional[list] = None  # action的输入参数定义
    output: Optional[str] = None  # action的输出定义
    parameters: Optional[list] = None  # action的parameters字段


@router.post("/orchestrations/save-with-action")
def save_orchestration_with_action(data: OrchestrationSaveWithActionRequest):
    """
    保存逻辑编排，并将编排包成 action
    返回编排信息和 action 信息
    """
    from bson import ObjectId
    from app.services.action_service import get_action_service

    collection = get_collection()
    if collection is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")

    now = datetime.now()

    # 1. 创建或更新编排
    orchestration_id = data.id
    if orchestration_id:
        # 更新已有编排
        try:
            obj_id = ObjectId(orchestration_id)
        except Exception:
            raise HTTPException(status_code=400, detail="无效的编排ID")

        update_data = {
            "name": data.name,
            "description": data.description or "",
            "updated_at": now,
        }
        if data.graph_data:
            update_data["graph_data"] = data.graph_data
        if data.inputs is not None:
            update_data["inputs"] = data.inputs
        if data.output is not None:
            update_data["output"] = data.output

        result = collection.update_one({"_id": obj_id}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="编排不存在")
        orchestration = collection.find_one({"_id": obj_id})
    else:
        # 创建新编排
        orchestration = {
            "name": data.name,
            "description": data.description or "",
            "graph_data": data.graph_data or {"nodes": [], "edges": []},
            "inputs": data.inputs or [],
            "output": data.output or "",
            "created_at": now,
            "updated_at": now,
        }
        result = collection.insert_one(orchestration)
        orchestration["_id"] = result.inserted_id

    orchestration_id = str(orchestration["_id"])

    # 2. 获取 action_service 创建或更新 action
    action_service = get_action_service()

    # 生成 api_name（驼峰转下划线再转驼峰）
    import re
    api_name = re.sub(r'_([a-z])', lambda m: m.group(1).upper(), data.name)

    # 检查是否已存在关联的 action
    existing_action = None
    if orchestration.get("action_id"):
        existing_action = action_service.get_action(orchestration["action_id"])

    # 确定 action_id：已有则用原有的，没有则生成
    action_id = orchestration.get("action_id") or f"Logic_{orchestration_id}"

    # 构建 action 数据
    action_data = {
        "id": action_id,
        "api_name": api_name,
        "name": data.name,
        "description": data.description or "",
        "action_type": "function",
        "function_code": f"""
from app.services.dag_service import execute_orchestration_by_id_for_action

result = execute_orchestration_by_id_for_action("{orchestration_id}", parameters)
""",
        "parameters": data.parameters or [],
        "submission_criteria": [],
    }

    if existing_action:
        # 更新已有 action
        action = action_service.update_action(orchestration["action_id"], action_data)
    else:
        # 创建新 action
        action = action_service.create_action(action_data)

    action_id = action.get("id")

    # 3. 将 action_id 存到编排上
    collection.update_one(
        {"_id": ObjectId(orchestration_id)},
        {"$set": {"action_id": action_id, "updated_at": datetime.now()}}
    )

    # 4. 返回结果
    orchestration["id"] = orchestration_id
    orchestration["action_id"] = action_id
    if "_id" in orchestration:
        orchestration.pop("_id")
    if "created_at" in orchestration:
        orchestration["created_at"] = orchestration["created_at"].isoformat()
    if "updated_at" in orchestration:
        orchestration["updated_at"] = orchestration["updated_at"].isoformat()

    return {
        "orchestration": orchestration,
        "action": action,
    }
