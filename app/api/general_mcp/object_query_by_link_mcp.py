"""
MCP工具模块 - 通过关系查询对象功能
提供通过指定关系查询关联对象的能力
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from typing import Any, Dict, List, Optional, Literal
from app.models.business_model import BusinessModel
from app.models.business_model_link import BusinessModelLink
from app.utils.shared_utils import get_db
from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class QueryObjectsByLinkRequest(BaseModel):
    object_type_id: str = Field(..., description="源对象类型ID，例如：'work_order'")
    object_ids: List[str] = Field(..., description="源对象的主键ID列表")
    link_type_id: str = Field(..., description="关系类型ID，例如：'work_order_to_product'")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="返回结果的最大数量，默认100", example=100)
    offset: Optional[int] = Field(None, ge=0, description="跳过的记录数量，用于分页，默认为0", example=0)


def _build_in_condition(field: str, values: List[str]) -> str:
    """构建IN条件"""
    if not isinstance(field, str) or not field.replace('_', '').replace('-', '').isalnum():
        raise ValueError("Invalid field name")
    
    if not values:
        raise ValueError("Values list cannot be empty")
    
    # 简单的 SQL 注入防护
    quoted_values = []
    for value in values:
        if isinstance(value, str):
            # 验证值是否只包含字母数字和允许的特殊字符
            if not value.replace('_', '').replace('-', '').replace('.', '').isalnum():
                raise ValueError(f"Invalid value: {value}")
            quoted_values.append(f"'{value}'")
        else:
            quoted_values.append(str(value))
    
    return f"{field} IN ({', '.join(quoted_values)})"


@router.post(
    "/query_objects_by_link",
    operation_id="query_objects_by_link",
    summary="通过关系查询关联的对象实例",
    description="""
    通过指定的关系查询与给定对象列表关联的对象实例。
    
    **功能特性：**
    - **双向查询**: 自动识别object_type_id在关系中是作为source还是target
    - **多关系类型支持**: 支持一对一、一对多、多对一、多对多关系
    - **多对多中间表**: 自动处理多对多关系的中间表查询
    - **批量查询**: 支持同时查询多个源对象的关联对象
    - **分页支持**: 通过limit和offset参数支持分页
    
    **使用示例：**
    
    1. **查询预警规则关联的预警消息**: 
    ```json
    {
        "object_type_id": "alert_rule",
        "object_ids": ["RULE00001", "RULE000002"],
        "link_type_id": "alert_rule_generates_alert_message"
    }
    ```
    
    2. **查询预警消息关联的预警规则**（反向查询）:
    ```json
    {
        "object_type_id": "alert_message",
        "object_ids": ["MSG000001", "MSG000002"],
        "link_type_id": "alert_rule_generates_alert_message"
    }
    ```
    
    3. **带分页的查询**:
    ```json
    {
        "object_type_id": "alert_rule",
        "object_ids": ["RULE00001", "RULE000002"],
        "link_type_id": "alert_rule_generates_alert_message",
        "limit": 50,
        "offset": 0
    }
    ```
    
    **注意事项：**
    - object_type_id可以是关系的source_model或target_model
    - 对于多对多关系，系统会自动通过中间表进行查询
    - 返回的结果是关联对象的完整数据列表
    """,
    response_description="关联对象实例列表"
)
def query_objects_by_link(
    request: QueryObjectsByLinkRequest,
    db: Session = Depends(get_db)
):
    """
    通过指定的关系查询关联的对象实例
    
    Args:
        request: 查询参数
        
    Returns:
        关联对象实例列表
    """
    try:
        if not request.object_ids:
            raise HTTPException(status_code=400, detail="object_ids cannot be empty")
        
        # 查找关系定义
        link = db.query(BusinessModelLink).filter(BusinessModelLink.id == request.link_type_id).first()
        
        if not link:
            raise HTTPException(status_code=404, detail=f"Link type '{request.link_type_id}' not found")
        
        # 确定源对象类型和目标对象类型
        is_source = link.source_model == request.object_type_id
        is_target = link.target_model == request.object_type_id
        
        if not (is_source or is_target):
            raise HTTPException(
                status_code=400, 
                detail=f"Object type '{request.object_type_id}' is neither source nor target in link '{request.link_type_id}'"
            )
        
        # 确定查询方向
        if is_source:
            # 从source查询target
            source_model_id = link.source_model
            source_key = link.source_key
            target_model_id = link.target_model
            target_key = link.target_key
            direction = "forward"
        else:
            # 从target查询source
            source_model_id = link.target_model
            source_key = link.target_key
            target_model_id = link.source_model
            target_key = link.source_key
            direction = "reverse"
        
        # 验证源对象类型存在且有数据源
        source_business_model = db.query(BusinessModel).filter(
            BusinessModel.id == source_model_id
        ).first()
        if not source_business_model:
            raise HTTPException(status_code=404, detail=f"Source object type '{source_model_id}' not found")
        
        if not source_business_model.data_source_id:
            raise HTTPException(status_code=400, detail=f"Source object type '{source_model_id}' has no data source configured")
        
        # 获取目标对象类型信息
        target_business_model = db.query(BusinessModel).filter(
            BusinessModel.id == target_model_id
        ).first()
        if not target_business_model:
            raise HTTPException(status_code=404, detail=f"Target object type '{target_model_id}' not found")
        
        if not target_business_model.data_source_id:
            raise HTTPException(status_code=400, detail=f"Target object type '{target_model_id}' has no data source configured")
        
        # 处理多对多关系
        if link.cardinality == "many-to-many" and link.intermediate_model:
            # 多对多关系需要通过中间表查询
            # 注意：多对多关系的source_key和target_key必须是主键（由业务规则保证）
            # 因此可以直接使用传入的object_ids（主键值）查询中间表
            intermediate_model = db.query(BusinessModel).filter(
                BusinessModel.id == link.intermediate_model
            ).first()
            
            if not intermediate_model:
                raise HTTPException(status_code=404, detail=f"Intermediate model '{link.intermediate_model}' not found")
            
            if not intermediate_model.data_source_id:
                raise HTTPException(status_code=400, detail=f"Intermediate model '{link.intermediate_model}' has no data source configured")
            
            # 直接使用传入的object_ids查询中间表（因为它们就是主键值）
            if direction == "forward":
                # 从source到target，查询中间表中source_key匹配的记录
                intermediate_condition = _build_in_condition(link.intermediate_source_key, request.object_ids)
                intermediate_query = f"SELECT * FROM {link.intermediate_model} WHERE {intermediate_condition}"
            else:
                # 从target到source，查询中间表中target_key匹配的记录
                intermediate_condition = _build_in_condition(link.intermediate_target_key, request.object_ids)
                intermediate_query = f"SELECT * FROM {link.intermediate_model} WHERE {intermediate_condition}"
            
            try:
                intermediate_data = data_source_manager.execute_query(
                    data_source_id=intermediate_model.data_source_id,
                    query=intermediate_query,
                    max_rows=10000  # 中间表可能有很多记录
                )
                
                if not intermediate_data:
                    return []  # 没有关联记录
                
                # 提取目标对象ID
                if direction == "forward":
                    target_ids = [str(record.get(link.intermediate_target_key)) for record in intermediate_data 
                                 if record.get(link.intermediate_target_key) is not None]
                else:
                    target_ids = [str(record.get(link.intermediate_source_key)) for record in intermediate_data 
                                 if record.get(link.intermediate_source_key) is not None]
                
                if not target_ids:
                    return []
                
                # 去重
                target_ids = list(set(target_ids))
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Query intermediate table failed: {str(e)}")
        
        else:
            # 非多对多关系，检查映射字段是否为主键以决定是否需要查询源对象
            # 注意：source_business_model 已经在前面查询过，这里直接使用
            # 检查映射字段是否就是主键
            source_primary_key_field = source_business_model.primary_key_id or "id"
            if source_key == source_primary_key_field:
                # 映射字段就是主键，可以直接使用传入的object_ids
                target_ids = request.object_ids
            else:
                # 映射字段不是主键，需要先查询源对象获取映射字段值
                source_condition = _build_in_condition(source_primary_key_field, request.object_ids)
                source_query = f"SELECT * FROM {source_model_id} WHERE {source_condition}"
                
                try:
                    source_data = data_source_manager.execute_query(
                        data_source_id=source_business_model.data_source_id,
                        query=source_query,
                        max_rows=1000
                    )
                    
                    if not source_data:
                        return []  # 源对象不存在
                    
                    # 提取映射字段值（用于查询目标对象）
                    # 由于前面已经标准化了source_key和target_key，这里统一使用source_key
                    mapping_values = [str(record.get(source_key)) for record in source_data if record.get(source_key) is not None]
                    
                    if not mapping_values:
                        return []
                    
                    # 去重
                    target_ids = list(set(mapping_values))
                    
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Query source objects failed: {str(e)}")
        
        # 第二步：查询目标对象
        target_condition = _build_in_condition(target_key, target_ids)
        target_query = f"SELECT * FROM {target_model_id} WHERE {target_condition}"
        
        # 添加分页
        actual_limit = request.limit if request.limit is not None else 100
        actual_offset = request.offset if request.offset is not None else 0
        
        if actual_limit > 0:
            if actual_offset > 0:
                target_query += f" LIMIT {actual_limit} OFFSET {actual_offset}"
            else:
                target_query += f" LIMIT {actual_limit}"
        
        try:
            logger.info(f"Executing query: {target_query}")
            target_data = data_source_manager.execute_query(
                data_source_id=target_business_model.data_source_id,
                query=target_query,
                max_rows=1000
            )
            return target_data
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query target objects failed: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query objects by link: {str(e)}")