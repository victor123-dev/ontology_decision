from threading import Lock
from typing import Dict, Any, List, Optional
from app.models.data_source import DataSource
from app.utils.db_client import DBClient, create_engine, sessionmaker
from app.utils.logger import get_logger
from app.utils.shared_utils import get_db_session
logger = get_logger(__name__)


class DataSourceManager:
    def __init__(self):
        self.connection_pool = {}
        self.lock = Lock()
    
    def _get_system_db_session(self):
        # engine = create_engine("sqlite:///data.db")
        # Session = sessionmaker(bind=engine)
        return get_db_session()
    
    def get_data_source_by_id(self, data_source_id: int) -> Optional[DataSource]:
        db = self._get_system_db_session()
        try:
            data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
            if not data_source:
                logger.warning(f"DataSource not found: {data_source_id}")
            return data_source
        finally:
            db.close()
    
    def get_data_source_by_name(self, name: str) -> Optional[DataSource]:
        db = self._get_system_db_session()
        try:
            data_source = db.query(DataSource).filter(DataSource.name == name).first()
            if not data_source:
                logger.warning(f"DataSource not found: {name}")
            return data_source
        finally:
            db.close()
    
    def get_client(self, data_source_id: int = None, data_source_name: str = None) -> DBClient:
        if data_source_id:
            data_source = self.get_data_source_by_id(data_source_id)
        elif data_source_name:
            data_source = self.get_data_source_by_name(data_source_name)
        else:
            raise ValueError("Either data_source_id or data_source_name must be provided")
        
        if not data_source:
            raise ValueError(f"DataSource not found")
        
        client = DBClient(data_source.type, data_source.connection_string)
        client.connect()
        return client
    
    def execute_query(self, data_source_id: int = None, data_source_name: str = None, query: str = None, params: Dict = None, max_rows: int = 100) -> List[Dict]:
        if data_source_name:
            data_source = self.get_data_source_by_name(data_source_name)
            if not data_source:
                raise ValueError(f"DataSource not found: {data_source_name}")
            data_source_id = data_source.id
        
        client = self.get_client(data_source_id=data_source_id)
        try:
            if "LIMIT" not in query.upper():
                query += f" LIMIT {max_rows}"
            return client.execute_query(query, params)
        finally:
            client.close()
    
    def execute_insert(self, data_source_id: int = None, data_source_name: str = None, table_name: str = None, data: Dict[str, Any] = None) -> bool:
        if data_source_name:
            data_source = self.get_data_source_by_name(data_source_name)
            if not data_source:
                raise ValueError(f"DataSource not found: {data_source_name}")
            data_source_id = data_source.id
        
        client = self.get_client(data_source_id=data_source_id)
        try:
            # 使用client的execute_query方法来执行INSERT
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data.values()])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            # SQLite的execute_query方法支持执行非查询语句
            client.execute_query(query, list(data.values()))
            return True
        except Exception as e:
            logger.error(f"Execute insert failed: {str(e)}")
            return False
        finally:
            client.close()
    
    def execute_update(self, data_source_id: int = None, data_source_name: str = None, table_name: str = None, data: Dict[str, Any] = None, primary_key: str = None, primary_value: Any = None) -> bool:
        if data_source_name:
            data_source = self.get_data_source_by_name(data_source_name)
            if not data_source:
                raise ValueError(f"DataSource not found: {data_source_name}")
            data_source_id = data_source.id
        
        client = self.get_client(data_source_id=data_source_id)
        try:
            update_values = {k: v for k, v in data.items() if k != primary_key}
            
            set_clause = ', '.join([f"{key} = ?" for key in update_values.keys()])
            query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key} = ?"
            values = list(update_values.values()) + [primary_value]
            
            client.execute_query(query, values)
            return True
        except Exception as e:
            logger.error(f"Execute update failed: {str(e)}")
            return False
        finally:
            client.close()
    
    def execute_delete(self, data_source_id: int = None, data_source_name: str = None, table_name: str = None, primary_key: str = None, primary_value: Any = None) -> bool:
        if data_source_name:
            data_source = self.get_data_source_by_name(data_source_name)
            if not data_source:
                raise ValueError(f"DataSource not found: {data_source_name}")
            data_source_id = data_source.id
        
        client = self.get_client(data_source_id=data_source_id)
        try:
            # 使用client的execute_query方法来执行DELETE
            query = f"DELETE FROM {table_name} WHERE {primary_key} = ?"
            
            client.execute_query(query, [primary_value])
            return True
        except Exception as e:
            logger.error(f"Execute delete failed: {str(e)}")
            return False
        finally:
            client.close()


data_source_manager = DataSourceManager()