from typing import Dict, Any, Optional
from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataSourceAccessor:
    def __init__(self):
        pass
    
    def get_data_source(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取数据源信息"""
        try:
            data_source = data_source_manager.get_data_source_by_name(name)
            if not data_source:
                return None
            return {
                'id': data_source.id,
                'name': data_source.name,
                'type': data_source.type
            }
        except Exception as e:
            logger.error(f"获取数据源信息失败: {str(e)}")
            return None
    
    def query(self, data_source_name: str, sql: str, max_rows: int = 100) -> Any:
        """执行查询"""
        if not isinstance(sql, str) or len(sql) > 1000:
            raise ValueError("Invalid query")
        return data_source_manager.execute_query(
            data_source_name=data_source_name, query=sql, max_rows=max_rows
        )