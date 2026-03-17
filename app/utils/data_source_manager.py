from threading import Lock
from typing import Dict, Any, List, Optional
from app.models.data_source import DataSource
from app.utils.db_client import DBClient, create_engine, sessionmaker
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataSourceManager:
    def __init__(self):
        self.connection_pool = {}
        self.lock = Lock()
    
    def _get_system_db_session(self):
        engine = create_engine("sqlite:///data.db")
        Session = sessionmaker(bind=engine)
        return Session()
    
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
    
    def execute_insert(self, data_source_id: int, table_name: str, data: Dict[str, Any]) -> bool:
        client = self.get_client(data_source_id=data_source_id)
        try:
            data_source = self.get_data_source_by_id(data_source_id)
            if data_source.type == 'sqlite':
                import sqlite3
                conn = sqlite3.connect(data_source.connection_string.replace('sqlite:///', ''))
                cursor = conn.cursor()
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data.values()])
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(data.values()))
                conn.commit()
                conn.close()
                return True
            return False
        finally:
            client.close()
    
    def execute_update(self, data_source_id: int, table_name: str, data: Dict[str, Any]) -> bool:
        client = self.get_client(data_source_id=data_source_id)
        try:
            data_source = self.get_data_source_by_id(data_source_id)
            if data_source.type == 'sqlite':
                import sqlite3
                conn = sqlite3.connect(data_source.connection_string.replace('sqlite:///', ''))
                cursor = conn.cursor()
                
                primary_key = list(data.keys())[0]
                primary_value = data[primary_key]
                update_values = {k: v for k, v in data.items() if k != primary_key}
                
                set_clause = ', '.join([f"{key} = ?" for key in update_values.keys()])
                query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key} = ?"
                values = list(update_values.values()) + [primary_value]
                
                cursor.execute(query, values)
                conn.commit()
                conn.close()
                return True
            return False
        finally:
            client.close()
    
    def execute_delete(self, data_source_id: int, table_name: str, conditions: Dict[str, Any]) -> bool:
        client = self.get_client(data_source_id=data_source_id)
        try:
            data_source = self.get_data_source_by_id(data_source_id)
            if data_source.type == 'sqlite':
                import sqlite3
                conn = sqlite3.connect(data_source.connection_string.replace('sqlite:///', ''))
                cursor = conn.cursor()
                
                condition_list = []
                values = []
                for key, value in conditions.items():
                    condition_list.append(f"{key} = ?")
                    values.append(value)
                
                condition_str = ' AND '.join(condition_list)
                query = f"DELETE FROM {table_name} WHERE {condition_str}"
                
                cursor.execute(query, values)
                conn.commit()
                conn.close()
                return True
            return False
        finally:
            client.close()


data_source_manager = DataSourceManager()