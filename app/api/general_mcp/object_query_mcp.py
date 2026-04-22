"""
MCP工具模块 - 本体相关功能
提供对本体（ontology）的相关的操作能力，包括实例数据查询
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from typing import Any, Dict, List, Optional, Literal
from enum import Enum
from app.models.business_model import BusinessModel
from app.utils.shared_utils import get_db
from app.utils.data_source_manager import data_source_manager

router = APIRouter()

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
    object_type_id: str = Field(..., description="对象类型的唯一标识符（如 'product'）")
    filter: Dict[str, FilterCondition] = Field(default={}, description="过滤条件，用于筛选符合条件的对象实例。键必须为对象的属性名（如 'category'）")
    sort: Dict[str, Literal["asc", "desc"]] = Field(default={}, description="排序条件，用于对查询结果进行排序")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="返回结果的最大数量，默认10", example=10)
    offset: Optional[int] = Field(None, ge=0, description="跳过的记录数量，用于分页，默认为0", example=0)
    aggregate: Dict[str, AggregateCondition] = Field(default={}, description="聚合操作，用于对结果进行统计分析。键必须为对象的属性名（如supplier_name）。若指定alias，后续having条件和返回结果中需使用该别名")
    group: List[str] = Field(default=[], description="分组字段列表，只有当aggregate参数指定了聚合操作时才有意义。当有存在2个类似的属性，仅后缀是name和code不同，建议使用后缀为name的属性，除非用户明确指定使用编码/编号/号码/code。")
    having: Dict[str, FilterCondition] = Field(default={}, description="聚合过滤条件(类似SQL的HAVING)，用于根据聚合结果字段进行过滤")


def _get_valid_field_names(business_model: BusinessModel) -> set:
    """获取业务模型的有效字段名称集合"""
    if not business_model.fields:
        return set()
    return {field.field_id for field in business_model.fields}


def _validate_fields_against_model(field_names: List[str], valid_fields: set, field_type: str = "field") -> None:
    """验证字段名是否在有效字段集合中"""
    invalid_fields = [field for field in field_names if field not in valid_fields]
    if invalid_fields:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid {field_type}(s): {', '.join(invalid_fields)}. Valid fields are: {', '.join(valid_fields)}"
        )


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
    查询指定类型的对象实例，支持过滤、聚合、排序、分页和分组操作。

    **重要提示**:
    - 当查询关联对象时，优先使用 query_objects_by_link 工具
    
    **功能特性：**
    - **过滤**: 支持多种操作符 (eq, ne, gt, lt, gte, lte, contains, in, not_in)
    - **排序**: 支持按任意字段升序(asc)或降序(desc)排序
    - **分页**: 通过limit参数控制返回结果数量 (1-1000)，通过offset参数控制跳过的记录数
    - **聚合**: 支持 sum, avg, count, max, min 聚合操作
    - **分组**: 可按一个或多个字段进行分组
    - **HAVING**: 对聚合结果进行二次过滤
    
    **使用示例：**
    
    1. **基础查询**: 查询所有产品对象实例
    ```json
    {
        "object_type_id": "product"
    }
    ```
    
    2. **带过滤条件的查询**: 查询所有电子产品类别且价格大于1000的产品
    ```json
    {
        "object_type_id": "product",
        "filter": {
            "category": {"op": "eq", "value": "电子产品"},
            "price": {"op": "gt", "value": 1000}
        }
    }
    ```
    
    3. **带排序和分页的查询**: 查询产品并按价格降序排序，只返回前10条结果
    ```json
    {
        "object_type_id": "product",
        "sort": {"price": "desc"},
        "limit": 10
    }
    ```
    
    4. **带OFFSET的分页查询**: 查询产品列表的第2页（每页10条）
    ```json
    {
        "object_type_id": "product",
        "limit": 10,
        "offset": 10
    }
    ```
    
    5. **聚合查询**: 计算所有产品的总销售额和平均库存
    ```json
    {
        "object_type_id": "product",
        "aggregate": {
            "price": {"type": "sum", "alias": "total_sales"},
            "stock": {"type": "avg"}
        }
    }
    ```
    
    6. **分组聚合查询**: 按产品类别分组，计算每个类别的总销售额，并按总销售额降序排序
    ```json
    {
        "object_type_id": "product",
        "filter": {"category": {"op": "contains", "value": "电子"}},
        "aggregate": {
            "price": {"type": "sum", "alias": "total_sales"}
        },
        "group": ["category"],
        "sort": {"total_sales": "desc"}
    }
    ```
    
    7. **带HAVING条件的聚合查询**: 按产品类别分组，计算总销售额，并筛选出总销售额大于3000的类别
    ```json
    {
        "object_type_id": "product",
        "aggregate": {
            "price": {"type": "sum", "alias": "total_sales"}
        },
        "group": ["category"],
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
        # 查找业务模型并预加载字段
        business_model = db.query(BusinessModel).options(
            joinedload(BusinessModel.fields)
        ).filter(BusinessModel.id == request.object_type_id).first()
        if not business_model:
            raise HTTPException(status_code=404, detail=f"Object type '{request.object_type_id}' not found")
        
        if not business_model.data_source_id:
            raise HTTPException(status_code=400, detail=f"Object type '{request.object_type_id}' has no data source configured")
        
        # 获取有效字段名集合用于验证
        valid_fields = _get_valid_field_names(business_model)
        
        # 验证过滤字段
        if request.filter:
            _validate_fields_against_model(list(request.filter.keys()), valid_fields, "filter field")
        
        # 验证排序字段
        if request.sort:
            _validate_fields_against_model(list(request.sort.keys()), valid_fields, "sort field")
        
        # 验证分组字段
        if request.group:
            _validate_fields_against_model(request.group, valid_fields, "group field")
        
        # 验证聚合字段
        if request.aggregate:
            _validate_fields_against_model(list(request.aggregate.keys()), valid_fields, "aggregate field")
        
        # 验证HAVING字段（使用聚合别名或有效字段）
        if request.having:
            # 对于HAVING，允许使用聚合别名或有效字段
            valid_having_fields = set(valid_fields)
            if request.aggregate:
                # 添加聚合别名到有效字段中
                for field_name, agg_condition in request.aggregate.items():
                    alias = agg_condition.alias or f"{agg_condition.type.value}_{field_name}"
                    valid_having_fields.add(alias)
            _validate_fields_against_model(list(request.having.keys()), valid_having_fields, "having field")
        
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
            
            # 构建 LIMIT 和 OFFSET 子句
            limit_clause = ""
            actual_limit = request.limit if request.limit is not None else 20
            actual_offset = request.offset if request.offset is not None else 0
            
            if actual_limit > 0:
                if actual_offset > 0:
                    limit_clause = f" LIMIT {actual_limit} OFFSET {actual_offset}"
                else:
                    limit_clause = f" LIMIT {actual_limit}"
            
            query = f"SELECT * FROM {request.object_type_id}{where_clause}{order_clause}{limit_clause}"
            
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
            base_query = f"SELECT {', '.join(select_fields)} FROM {request.object_type_id}{where_clause}{group_clause}"
            
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
            
            # 添加 LIMIT 和 OFFSET（聚合查询通常不需要大量结果）
            actual_limit = request.limit if request.limit is not None else 100
            actual_offset = request.offset if request.offset is not None else 0
            
            if actual_limit > 0:
                if actual_offset > 0:
                    final_query += f" LIMIT {actual_limit} OFFSET {actual_offset}"
                else:
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