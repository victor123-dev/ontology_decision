from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.business_model import BusinessModel
from app.utils.data_source_manager import data_source_manager
from app.utils.shared_utils import get_db

router = APIRouter()


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
    else:
        raise ValueError(f"Unsupported operator: {operator}")


@router.post("/business-data/{model_name}/query")
def query_business_data(
    model_name: str,
    query_params: dict,
    db: Session = Depends(get_db)
):
    """执行复杂查询"""
    # 查找业务模型
    business_model = db.query(BusinessModel).filter(BusinessModel.id == model_name).first()
    if not business_model:
        raise HTTPException(status_code=404, detail=f"Business model '{model_name}' not found")
    
    if not business_model.data_source_id:
        raise HTTPException(status_code=400, detail=f"Business model '{model_name}' has no data source configured")
    
    # 解析查询参数
    filters = query_params.get("filters", [])
    sort_by = query_params.get("sort_by")
    sort_direction = query_params.get("sort_direction", "asc")
    limit = query_params.get("limit")
    offset = query_params.get("offset", 0)
    
    # 构建 WHERE 条件
    where_conditions = []
    for filter_condition in filters:
        if isinstance(filter_condition, dict):
            field = filter_condition.get("field")
            operator = filter_condition.get("operator")
            value = filter_condition.get("value")
            
            if field and operator and value is not None:
                try:
                    condition = _build_sql_condition(field, operator, value)
                    where_conditions.append(condition)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid filter condition: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Invalid filter format")
    
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # 构建 ORDER BY 子句
    order_clause = ""
    if sort_by:
        if not isinstance(sort_by, str) or not sort_by.replace('_', '').replace('-', '').isalnum():
            raise HTTPException(status_code=400, detail="Invalid sort field")
        direction = "DESC" if sort_direction.lower() == "desc" else "ASC"
        order_clause = f" ORDER BY {sort_by} {direction}"
    
    # 构建 LIMIT 和 OFFSET 子句
    limit_clause = ""
    if limit is not None:
        try:
            limit_int = int(limit)
            if limit_int > 0:
                limit_clause = f" LIMIT {limit_int}"
                if offset > 0:
                    limit_clause += f" OFFSET {offset}"
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid limit or offset value")
    
    query = f"SELECT * FROM {model_name}{where_clause}{order_clause}{limit_clause}"
    
    try:
        data = data_source_manager.execute_query(
            data_source_id=business_model.data_source_id,
            query=query,
            max_rows=2000
        )
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.post("/business-data/{model_name}/count")
def count_business_data_query(
    model_name: str,
    query_params: dict,
    db: Session = Depends(get_db)
):
    """统计复杂查询条件下的记录数"""
    # 查找业务模型
    business_model = db.query(BusinessModel).filter(BusinessModel.id == model_name).first()
    if not business_model:
        raise HTTPException(status_code=404, detail=f"Business model '{model_name}' not found")
    
    if not business_model.data_source_id:
        raise HTTPException(status_code=400, detail=f"Business model '{model_name}' has no data source configured")
    
    # 解析过滤条件
    filters = query_params.get("filters", [])
    
    # 构建 WHERE 条件
    where_conditions = []
    for filter_condition in filters:
        if isinstance(filter_condition, dict):
            field = filter_condition.get("field")
            operator = filter_condition.get("operator")
            value = filter_condition.get("value")
            
            if field and operator and value is not None:
                try:
                    condition = _build_sql_condition(field, operator, value)
                    where_conditions.append(condition)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid filter condition: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Invalid filter format")
    
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    query = f"SELECT COUNT(*) as count FROM {model_name}{where_clause}"
    
    try:
        result = data_source_manager.execute_query(
            data_source_id=business_model.data_source_id,
            query=query,
            max_rows=1
        )
        count = result[0]['count'] if result else 0
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.get("/business-data/{model_name}/get")
def get_business_data_by_id(
    model_name: str,
    id: str,
    db: Session = Depends(get_db)
):
    """根据ID获取业务数据"""
    business_model = db.query(BusinessModel).filter(BusinessModel.id == model_name).first()
    if not business_model:
        raise HTTPException(status_code=404, detail=f"Business model '{model_name}' not found")
    
    if not business_model.data_source_id:
        raise HTTPException(status_code=400, detail=f"Business model '{model_name}' has no data source configured")
    
    if not business_model.primary_key_id:
        raise HTTPException(status_code=400, detail=f"Business model '{model_name}' has no primary key configured")
    
    query = f"SELECT * FROM {model_name} WHERE {business_model.primary_key_id} = '{id}'"
    
    try:
        data = data_source_manager.execute_query(
            data_source_id=business_model.data_source_id,
            query=query,
            max_rows=1
        )
        if data:
            return {"data": data[0]}
        else:
            raise HTTPException(status_code=404, detail="Record not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.post("/business-data/{model_name}/create")
def create_business_data(
    model_name: str,
    data: dict,
    db: Session = Depends(get_db)
):
    """创建业务数据"""
    business_model = db.query(BusinessModel).filter(BusinessModel.id == model_name).first()
    if not business_model:
        raise HTTPException(status_code=404, detail=f"Business model '{model_name}' not found")
    
    if not business_model.data_source_id:
        raise HTTPException(status_code=400, detail=f"Business model '{model_name}' has no data source configured")
    
    try:
        success = data_source_manager.execute_insert(
            data_source_id=business_model.data_source_id,
            table_name=model_name,
            data=data
        )
        if success:
            # 获取主键值（假设插入成功后可以通过某种方式获取）
            # 这里需要根据实际情况实现，比如从 data 中获取主键值
            primary_key_field = business_model.primary_key_id
            primary_key_value = data.get(primary_key_field)
            
            if primary_key_value is not None:
                # 查询刚创建的对象
                query = f"SELECT * FROM {model_name} WHERE {primary_key_field} = '{primary_key_value}'"
                result_data = data_source_manager.execute_query(
                    data_source_id=business_model.data_source_id,
                    query=query,
                    max_rows=1
                )
                if result_data:
                    return {"data": result_data[0]}
            
            # 如果无法获取完整数据，至少返回输入数据
            return {"data": data}
        else:
            raise HTTPException(status_code=500, detail="Failed to create data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insert execution failed: {str(e)}")


@router.put("/business-data/{model_name}/update")
def update_business_data(
    model_name: str,
    id: str,
    data: dict,
    db: Session = Depends(get_db)
):
    """更新业务数据"""
    business_model = db.query(BusinessModel).filter(BusinessModel.id == model_name).first()
    if not business_model:
        raise HTTPException(status_code=404, detail=f"Business model '{model_name}' not found")
    
    if not business_model.data_source_id:
        raise HTTPException(status_code=400, detail=f"Business model '{model_name}' has no data source configured")
    
    try:
        success = data_source_manager.execute_update(
            data_source_id=business_model.data_source_id,
            table_name=model_name,
            data=data,
            primary_key=business_model.primary_key_id,
            primary_value=id
        )
        if success:
            # 查询更新后的完整对象
            query = f"SELECT * FROM {model_name} WHERE {business_model.primary_key_id} = '{id}'"
            result_data = data_source_manager.execute_query(
                data_source_id=business_model.data_source_id,
                query=query,
                max_rows=1
            )
            if result_data:
                return {"data": result_data[0]}
            else:
                # 如果查询失败，返回合并后的数据
                updated_data = {}
                # 这里需要获取原始数据，但为了简化，直接合并
                updated_data.update(data)
                updated_data[business_model.primary_key_id] = id
                return {"data": updated_data}
        else:
            raise HTTPException(status_code=500, detail="Failed to update data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update execution failed: {str(e)}")


@router.delete("/business-data/{model_name}/delete")
def delete_business_data(
    model_name: str,
    id: str,
    db: Session = Depends(get_db)
):
    """删除业务数据"""
    business_model = db.query(BusinessModel).filter(BusinessModel.id == model_name).first()
    if not business_model:
        raise HTTPException(status_code=404, detail=f"Business model '{model_name}' not found")
    
    if not business_model.data_source_id:
        raise HTTPException(status_code=400, detail=f"Business model '{model_name}' has no data source configured")
    
    try:
        success = data_source_manager.execute_delete(
            data_source_id=business_model.data_source_id,
            table_name=model_name,
            primary_key=business_model.primary_key_id,
            primary_value=id
        )
        if success:
            return {"message": "Data deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete execution failed: {str(e)}")
