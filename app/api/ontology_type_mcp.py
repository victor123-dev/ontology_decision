"""
MCP工具模块 - 本体相关功能
提供对本体（ontology）的完整操作能力，包括元数据查询、实例数据查询和行动执行
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from app.models.business_model import BusinessModel, BusinessModelField
from app.models.business_model_link import BusinessModelLink
from app.utils.shared_utils import get_db
from app.dao.action_dao import get_action_dao
from app.utils.data_source_manager import data_source_manager

router = APIRouter()

@router.get(
    "/get_ontology_context", 
    operation_id="get_ontology_context",
    summary="获取本体上下文",
    description="""
    获取当前本体的精选上下文，包括本体中所有的对象、关系、行动的精简信息。
    返回的数据结构包含三个主要部分：
    - objects: 所有业务模型（对象）的概要信息
    - links: 所有业务模型关系（链接）的概要信息  
    - actions: 所有可执行动作的概要信息
    """,
    response_description="包含本体上下文的JSON对象"
)
def get_ontology_context(db: Session = Depends(get_db)):
    """
    获取当前本体的精选上下文，包括本体中所有的对象、关系、行动的精简信息
    
    Returns:
        包含objects、links、actions三个部分的精简本体上下文
    """
    try:
        # 获取所有业务模型（对象）
        business_models = db.query(BusinessModel).all()
        objects_summary = []
        for model in business_models:
            _ = model.fields  # 确保加载字段
            objects_summary.append({
                "id": model.id,
                "name": model.name,
                "description": model.description or "",
                "field_count": len(model.fields) if model.fields else 0,
                "data_source_id": model.data_source_id
            })
        
        # 获取所有业务模型关系（链接）
        model_links = db.query(BusinessModelLink).all()
        links_summary = []
        for link in model_links:
            links_summary.append({
                "id": link.id,
                "name": link.name,
                "description": link.description or "",
                "source_model": link.source_model,
                "target_model": link.target_model,
                "cardinality": link.cardinality
            })
        
        # 获取所有行动
        action_dao = get_action_dao()
        actions = action_dao.get_actions()
        actions_summary = []
        for action in actions:
            actions_summary.append({
                "id": action["id"],
                "name": action.get("name", "Unnamed Action"),
                "description": action.get("description", ""),
                "action_type": action.get("action_type"),
                "target_model_id": action.get("target_model_id"),
                "target_link_id": action.get("target_link_id")
            })
        
        return {
            "objects": objects_summary,
            "links": links_summary,
            "actions": actions_summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ontology context: {str(e)}")

@router.get(
    "/search_ontology", 
    operation_id="search_ontology",
    summary="搜索本体实体",
    description="""
    在本体中搜索与给定查询相关的本体实体（对象、关系、行动）。
    支持模糊匹配，会在实体的ID、名称、描述等字段中进行搜索。
    """,
    response_description="匹配的本体实体列表"
)
def search_ontology(
    query: str = Query(..., description="搜索关键词，用于在本体中查找相关实体"),
    db: Session = Depends(get_db)
):
    """
    在本体中搜索与给定查询相关的本体实体（对象、关系、行动）
    
    Args:
        query: 搜索关键词
        
    Returns:
        匹配的对象、关系、行动列表
    """
    try:
        results = {"objects": [], "links": [], "actions": []}
        query_lower = query.lower()
        
        # 搜索业务模型（对象）
        business_models = db.query(BusinessModel).all()
        for model in business_models:
            _ = model.fields
            model_text = f"{model.id} {model.name} {model.description or ''}".lower()
            if query_lower in model_text:
                results["objects"].append({
                    "id": model.id,
                    "name": model.name,
                    "description": model.description or "",
                    "type": "object"
                })
        
        # 搜索业务模型关系（链接）
        model_links = db.query(BusinessModelLink).all()
        for link in model_links:
            link_text = f"{link.id} {link.name} {link.description or ''}".lower()
            if query_lower in link_text:
                results["links"].append({
                    "id": link.id,
                    "name": link.name,
                    "description": link.description or "",
                    "type": "link"
                })
        
        # 搜索行动
        action_dao = get_action_dao()
        actions = action_dao.get_actions()
        for action in actions:
            action_text = f"{action.get('id', '')} {action.get('name', '')} {action.get('description', '')}".lower()
            if query_lower in action_text:
                results["actions"].append({
                    "id": action["id"],
                    "name": action.get("name", "Unnamed Action"),
                    "description": action.get("description", ""),
                    "type": "action"
                })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search ontology: {str(e)}")

@router.get(
    "/view_object_type/{object_type_id}", 
    operation_id="view_object_type",
    summary="查看对象类型详情",
    description="""
    查看本体中现有对象类型的详细信息，包括其属性、关联链接类型和动作类型。
    返回完整的对象元数据，包括字段定义、相关的关系和可用的操作。
    """,
    response_description="对象类型的完整详细信息"
)
def view_object_type(
    object_type_id: str = Path(..., description="对象类型ID（业务模型ID）"),
    db: Session = Depends(get_db)
):
    """
    在本体中查看现有对象类型的详细信息，包括其属性、关联链接类型和动作类型
    
    Args:
        object_type_id: 对象类型ID（业务模型ID）
        
    Returns:
        对象类型的完整详细信息
    """
    try:
        # 获取业务模型
        business_model = db.query(BusinessModel).filter(BusinessModel.id == object_type_id).first()
        if not business_model:
            raise HTTPException(status_code=404, detail=f"Object type {object_type_id} not found")
        
        _ = business_model.fields  # 确保加载字段
        
        # 获取关联的链接类型
        source_links = db.query(BusinessModelLink).filter(
            BusinessModelLink.source_model == object_type_id
        ).all()
        target_links = db.query(BusinessModelLink).filter(
            BusinessModelLink.target_model == object_type_id
        ).all()
        all_links = source_links + target_links
        
        links_info = []
        for link in all_links:
            links_info.append({
                "id": link.id,
                "name": link.name,
                "description": link.description or "",
                "direction": "source" if link.source_model == object_type_id else "target",
                "cardinality": link.cardinality,
                "other_model": link.target_model if link.source_model == object_type_id else link.source_model
            })
        
        # 获取关联的动作类型
        action_dao = get_action_dao()
        object_actions = action_dao.get_actions_by_model(object_type_id)
        
        actions_info = []
        for action in object_actions:
            actions_info.append({
                "id": action["id"],
                "name": action.get("name", "Unnamed Action"),
                "description": action.get("description", ""),
                "action_type": action.get("action_type"),
                "operation": action.get("operation"),
                "parameters": action.get("parameters", [])
            })
        
        return {
            "object_type": {
                "id": business_model.id,
                "name": business_model.name,
                "description": business_model.description or "",
                "data_source_id": business_model.data_source_id,
                "primary_key_id": business_model.primary_key_id,
                "api_name": business_model.api_name
            },
            "fields": [
                {
                    "field_id": field.field_id,
                    "name": field.name,
                    "description": field.description or "",
                    "data_type": field.data_type
                }
                for field in business_model.fields
            ] if business_model.fields else [],
            "associated_links": links_info,
            "associated_actions": actions_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to view object type: {str(e)}")

@router.get(
    "/view_link_type/{link_type_id}", 
    operation_id="view_link_type",
    summary="查看链接类型详情",
    description="""
    查看本体中已有的链接类型的详细信息。
    返回完整的链接元数据，包括源模型、目标模型、基数类型、
    以及多对多关系的中间表信息（如果适用）。
    """,
    response_description="链接类型的完整详细信息"
)
def view_link_type(
    link_type_id: str = Path(..., description="链接类型ID"),
    db: Session = Depends(get_db)
):
    """
    查看本体中已有的链接类型的详细信息
    
    Args:
        link_type_id: 链接类型ID
        
    Returns:
        链接类型的完整详细信息
    """
    try:
        link = db.query(BusinessModelLink).filter(BusinessModelLink.id == link_type_id).first()
        if not link:
            raise HTTPException(status_code=404, detail=f"Link type {link_type_id} not found")
        
        # 获取源模型和目标模型信息
        source_model = db.query(BusinessModel).filter(BusinessModel.id == link.source_model).first()
        target_model = db.query(BusinessModel).filter(BusinessModel.id == link.target_model).first()
        
        result = {
            "link_type": {
                "id": link.id,
                "name": link.name,
                "description": link.description or "",
                "cardinality": link.cardinality,
                "source_model": {
                    "id": link.source_model,
                    "name": source_model.name if source_model else None
                },
                "target_model": {
                    "id": link.target_model,
                    "name": target_model.name if target_model else None
                },
                "source_key": link.source_key,
                "target_key": link.target_key
            }
        }
        
        # 如果是多对多关系，包含中间表信息
        if link.cardinality == "many-to-many" and link.intermediate_model:
            intermediate_model = db.query(BusinessModel).filter(
                BusinessModel.id == link.intermediate_model
            ).first()
            result["link_type"]["intermediate_model"] = {
                "id": link.intermediate_model,
                "name": intermediate_model.name if intermediate_model else None
            }
            result["link_type"]["intermediate_source_key"] = link.intermediate_source_key
            result["link_type"]["intermediate_target_key"] = link.intermediate_target_key
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to view link type: {str(e)}")

@router.get(
    "/view_action_type/{action_type_id}", 
    operation_id="view_action_type",
    summary="查看动作类型详情",
    description="""
    查看本体中已有的动作类型的详细信息，包括其参数、逻辑规则和依赖对象类型。
    返回完整的动作元数据，包括参数定义、提交条件、函数代码等详细信息。
    """,
    response_description="动作类型的完整详细信息"
)
def view_action_type(
    action_type_id: str = Path(..., description="动作类型ID"),
):
    """
    本体中查看已有的动作类型的详细信息，包括其参数、逻辑规则和依赖对象类型
    
    Args:
        action_type_id: 动作类型ID
        
    Returns:
        动作类型的完整详细信息
    """
    try:
        action_dao = get_action_dao()
        action = action_dao.get_action_by_id(action_type_id)
        if not action:
            raise HTTPException(status_code=404, detail=f"Action type {action_type_id} not found")
        
        return {
            "action_type": {
                "id": action["id"],
                "name": action.get("name"),
                "description": action.get("description"),
                "action_type": action.get("action_type"),  # object, link, function
                "operation": action.get("operation"),      # create, update, delete, custom
                "target_model_id": action.get("target_model_id"),
                "target_link_id": action.get("target_link_id"),
                "parameters": action.get("parameters", []),
                "submission_criteria": action.get("submission_criteria", []),
                "function_code": action.get("function_code"),
                "created_at": action.get("created_at"),
                "updated_at": action.get("updated_at")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to view action type: {str(e)}")


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    CONTAINS = "contains"
    IN = "in"
    NOT_IN = "not_in"


class AggregateType(str, Enum):
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MAX = "max"
    MIN = "min"


class FilterCondition(BaseModel):
    op: FilterOperator = Field(..., description="操作符，支持：eq(等于), ne(不等于), gt(大于), lt(小于), gte(大于等于), lte(小于等于), contains(包含), in(在列表中), not_in(不在列表中)")
    value: Any = Field(..., description="过滤值，可以是字符串、数字、布尔值等任意类型")


class AggregateCondition(BaseModel):
    type: AggregateType = Field(..., description="聚合类型，支持：sum(求和), avg(平均值), count(计数), max(最大值), min(最小值)")
    alias: Optional[str] = Field(None, description="聚合结果的别名，默认格式为：{聚合类型}_{属性名}")


class QueryObjectsRequest(BaseModel):
    object_type_name: str = Field(..., description="要查询的对象类型名称，例如：'test_Product'")
    filter: Dict[str, FilterCondition] = Field(default={}, description="过滤条件，用于筛选符合条件的对象实例。键必须为对象的属性名。")
    sort: Dict[str, Literal["asc", "desc"]] = Field(default={}, description="排序条件，用于对查询结果进行排序")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="返回结果的最大数量，默认10", example=10)
    aggregate: Dict[str, AggregateCondition] = Field(default={}, description="聚合操作，用于对结果进行统计分析。键必须为对象的属性名（如supplier_name）。若指定alias，后续having条件和返回结果中需使用该别名")
    group: List[str] = Field(default=[], description="分组字段列表，只有当aggregate参数指定了聚合操作时才有意义。当有存在2个类似的属性，仅后缀是name和code不同，建议使用后缀为name的属性，除非用户明确指定使用编码/编号/号码/code。")
    having: Dict[str, FilterCondition] = Field(default={}, description="聚合过滤条件(类似SQL的HAVING)，用于根据聚合结果字段进行过滤")


def _build_sql_condition(field: str, operator: str, value) -> str:
    """根据 FilterCondition 构建 SQL 条件"""
    # 简单的 SQL 注入防护
    if not isinstance(field, str) or not field.replace('_', '').replace('-', '').isalnum():
        raise ValueError("Invalid field name")
    
    if operator == "eq":
        if isinstance(value, str):
            return f"{field} = '{value}'"
        else:
            return f"{field} = {value}"
    elif operator == "ne":
        if isinstance(value, str):
            return f"{field} != '{value}'"
        else:
            return f"{field} != {value}"
    elif operator == "gt":
        if isinstance(value, str):
            return f"{field} > '{value}'"
        else:
            return f"{field} > {value}"
    elif operator == "gte":
        if isinstance(value, str):
            return f"{field} >= '{value}'"
        else:
            return f"{field} >= {value}"
    elif operator == "lt":
        if isinstance(value, str):
            return f"{field} < '{value}'"
        else:
            return f"{field} < {value}"
    elif operator == "lte":
        if isinstance(value, str):
            return f"{field} <= '{value}'"
        else:
            return f"{field} <= {value}"
    elif operator == "contains":
        if isinstance(value, str):
            return f"{field} LIKE '%{value}%'"
        else:
            raise ValueError("Contains operator only supports string values")
    elif operator == "in":
        if isinstance(value, list):
            if all(isinstance(v, str) for v in value):
                quoted_values = [f"'{v}'" for v in value]
                return f"{field} IN ({', '.join(quoted_values)})"
            else:
                # 数字列表
                str_values = [str(v) for v in value]
                return f"{field} IN ({', '.join(str_values)})"
        else:
            raise ValueError("IN operator requires a list of values")
    elif operator == "not_in":
        if isinstance(value, list):
            if all(isinstance(v, str) for v in value):
                quoted_values = [f"'{v}'" for v in value]
                return f"{field} NOT IN ({', '.join(quoted_values)})"
            else:
                # 数字列表
                str_values = [str(v) for v in value]
                return f"{field} NOT IN ({', '.join(str_values)})"
        else:
            raise ValueError("NOT_IN operator requires a list of values")
    else:
        raise ValueError(f"Unsupported operator: {operator}")


@router.post(
    "/query_objects",
    operation_id="query_objects",
    summary="查询指定类型的对象实例",
    description="""
    查询本体中指定类型的对象实例，支持过滤、聚合、排序、分页和分组操作。
    
    **功能特性：**
    - **过滤**: 支持多种操作符 (eq, ne, gt, lt, gte, lte, contains, in, not_in)
    - **排序**: 支持按任意字段升序(asc)或降序(desc)排序
    - **分页**: 通过limit参数控制返回结果数量 (1-1000)
    - **聚合**: 支持 sum, avg, count, max, min 聚合操作
    - **分组**: 可按一个或多个字段进行分组
    - **HAVING**: 对聚合结果进行二次过滤
    
    **使用示例：**
    
    1. **基础查询**: 查询所有产品对象实例
    ```json
    {
        "object_type_name": "test_Product"
    }
    ```
    
    2. **带过滤条件的查询**: 查询所有电子产品类别且价格大于1000的产品
    ```json
    {
        "object_type_name": "test_Product",
        "filter": {
            "test_category": {"op": "eq", "value": "电子产品"},
            "test_price": {"op": "gt", "value": 1000}
        }
    }
    ```
    
    3. **带排序和分页的查询**: 查询产品并按价格降序排序，只返回前10条结果
    ```json
    {
        "object_type_name": "test_Product",
        "sort": {"test_price": "desc"},
        "limit": 10
    }
    ```
    
    4. **聚合查询**: 计算所有产品的总销售额和平均库存
    ```json
    {
        "object_type_name": "test_Product",
        "aggregate": {
            "test_price": {"type": "sum", "alias": "total_sales"},
            "test_stock": {"type": "avg"}
        }
    }
    ```
    
    5. **分组聚合查询**: 按产品类别分组，计算每个类别的总销售额，并按总销售额降序排序
    ```json
    {
        "object_type_name": "test_Product",
        "filter": {"test_category": {"op": "contains", "value": "电子"}},
        "aggregate": {
            "test_price": {"type": "sum", "alias": "total_sales"}
        },
        "group": ["test_category"],
        "sort": {"total_sales": "desc"}
    }
    ```
    
    6. **带HAVING条件的聚合查询**: 按产品类别分组，计算总销售额，并筛选出总销售额大于3000的类别
    ```json
    {
        "object_type_name": "test_Product",
        "aggregate": {
            "test_price": {"type": "sum", "alias": "total_sales"}
        },
        "group": ["test_category"],
        "having": {"total_sales": {"op": "gt", "value": 3000}}
    }
    ```
    
    **注意事项：**
    - 当存在 name/code 类似属性时，建议优先使用 name 属性，除非用户明确指定使用编码/编号/号码/code
    - 聚合查询中，如果指定了 alias，则在 having 条件和返回结果中必须使用该别名
    - 非聚合查询返回对象实例列表，聚合查询返回聚合结果字典列表
    """,
    response_description="查询结果：如果没有聚合操作，返回对象实例列表；如果有聚合操作，返回聚合结果字典列表"
)
def query_objects(
    request: QueryObjectsRequest,
    db: Session = Depends(get_db)
):
    """
    查询指定类型的对象实例，支持过滤、聚合、排序、分页和分组
    
    Args:
        request: 查询参数
        
    Returns:
        如果没有聚合操作，返回对象实例列表；如果有聚合操作，返回聚合结果字典列表
    """
    try:
        # 查找业务模型
        business_model = db.query(BusinessModel).filter(BusinessModel.id == request.object_type_name).first()
        if not business_model:
            raise HTTPException(status_code=404, detail=f"Object type '{request.object_type_name}' not found")
        
        if not business_model.data_source_id:
            raise HTTPException(status_code=400, detail=f"Object type '{request.object_type_name}' has no data source configured")
        
        # 处理非聚合查询
        if not request.aggregate:
            # 构建 WHERE 条件
            where_conditions = []
            if request.filter:
                for field_name, filter_condition in request.filter.items():
                    try:
                        condition = _build_sql_condition(field_name, filter_condition.op.value, filter_condition.value)
                        where_conditions.append(condition)
                    except ValueError as e:
                        raise HTTPException(status_code=400, detail=f"Invalid filter condition for field '{field_name}': {str(e)}")
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 构建 ORDER BY 子句
            order_clause = ""
            if request.sort:
                order_parts = []
                for field_name, direction in request.sort.items():
                    if not isinstance(field_name, str) or not field_name.replace('_', '').replace('-', '').isalnum():
                        raise HTTPException(status_code=400, detail=f"Invalid sort field: {field_name}")
                    dir_str = "DESC" if direction.lower() == "desc" else "ASC"
                    order_parts.append(f"{field_name} {dir_str}")
                if order_parts:
                    order_clause = " ORDER BY " + ", ".join(order_parts)
            
            # 构建 LIMIT 子句
            limit_clause = ""
            actual_limit = request.limit if request.limit is not None else 10
            if actual_limit > 0:
                limit_clause = f" LIMIT {actual_limit}"
            
            query = f"SELECT * FROM {request.object_type_name}{where_clause}{order_clause}{limit_clause}"
            
            try:
                data = data_source_manager.execute_query(
                    data_source_id=business_model.data_source_id,
                    query=query,
                    max_rows=1000
                )
                return data
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")
        
        # 处理聚合查询
        else:
            # 构建基础 WHERE 条件
            where_conditions = []
            if request.filter:
                for field_name, filter_condition in request.filter.items():
                    try:
                        condition = _build_sql_condition(field_name, filter_condition.op.value, filter_condition.value)
                        where_conditions.append(condition)
                    except ValueError as e:
                        raise HTTPException(status_code=400, detail=f"Invalid filter condition for field '{field_name}': {str(e)}")
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 构建聚合字段
            aggregate_fields = []
            aggregate_aliases = {}
            for field_name, agg_condition in request.aggregate.items():
                alias = agg_condition.alias or f"{agg_condition.type.value}_{field_name}"
                aggregate_aliases[field_name] = alias
                
                if agg_condition.type == AggregateType.COUNT:
                    # COUNT 聚合通常对整个行计数
                    aggregate_fields.append(f"COUNT(*) as {alias}")
                else:
                    aggregate_fields.append(f"{agg_condition.type.value.upper()}({field_name}) as {alias}")
            
            # 构建 GROUP BY 子句
            group_clause = ""
            if request.group:
                # 验证分组字段
                for field_name in request.group:
                    if not isinstance(field_name, str) or not field_name.replace('_', '').replace('-', '').isalnum():
                        raise HTTPException(status_code=400, detail=f"Invalid group field: {field_name}")
                group_clause = " GROUP BY " + ", ".join(request.group)
                select_fields = request.group + aggregate_fields
            else:
                select_fields = aggregate_fields
            
            # 构建基础聚合查询
            base_query = f"SELECT {', '.join(select_fields)} FROM {request.object_type_name}{where_clause}{group_clause}"
            
            # 处理 HAVING 条件
            if request.having:
                having_conditions = []
                for alias_or_field, having_condition in request.having.items():
                    # 在 HAVING 中，应该使用聚合别名
                    try:
                        condition = _build_sql_condition(alias_or_field, having_condition.op.value, having_condition.value)
                        having_conditions.append(condition)
                    except ValueError as e:
                        raise HTTPException(status_code=400, detail=f"Invalid having condition for field '{alias_or_field}': {str(e)}")
                
                if having_conditions:
                    having_clause = " HAVING " + " AND ".join(having_conditions)
                    base_query += having_clause
            
            # 构建 ORDER BY 子句（针对聚合结果）
            order_clause = ""
            if request.sort:
                order_parts = []
                for field_name, direction in request.sort.items():
                    if not isinstance(field_name, str) or not field_name.replace('_', '').replace('-', '').isalnum():
                        raise HTTPException(status_code=400, detail=f"Invalid sort field: {field_name}")
                    dir_str = "DESC" if direction.lower() == "desc" else "ASC"
                    order_parts.append(f"{field_name} {dir_str}")
                if order_parts:
                    order_clause = " ORDER BY " + ", ".join(order_parts)
            
            final_query = base_query + order_clause
            
            # 添加 LIMIT（聚合查询通常不需要大量结果）
            actual_limit = request.limit if request.limit is not None else 100
            if actual_limit > 0:
                final_query += f" LIMIT {actual_limit}"
            
            try:
                data = data_source_manager.execute_query(
                    data_source_id=business_model.data_source_id,
                    query=final_query,
                    max_rows=1000
                )
                return data
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Aggregation query execution failed: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query objects: {str(e)}")