from threading import Lock
import sqlite3
import time
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
    
    def execute_upsert(self, data_source_id: int = None, data_source_name: str = None, table_name: str = None, data: Dict[str, Any] = None, primary_key: str = None) -> bool:
        """执行UPSERT操作（存在则更新，不存在则插入）"""
        if data_source_name:
            data_source = self.get_data_source_by_name(data_source_name)
            if not data_source:
                raise ValueError(f"DataSource not found: {data_source_name}")
            data_source_id = data_source.id
        
        max_retries = 3
        retry_delay = 0.1  # 秒
        
        for attempt in range(max_retries):
            client = self.get_client(data_source_id=data_source_id)
            try:
                if self._is_sqlite(client):
                    # SQLite 使用 INSERT OR REPLACE
                    columns = ', '.join(data.keys())
                    placeholders = ', '.join(['?' for _ in data.values()])
                    query = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
                    client.execute_query(query, list(data.values()))
                else:
                    # 其他数据库使用标准UPSERT语法（这里简化处理为先尝试插入，失败则更新）
                    try:
                        columns = ', '.join(data.keys())
                        placeholders = ', '.join(['?' for _ in data.values()])
                        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                        client.execute_query(query, list(data.values()))
                    except Exception:
                        # 插入失败，尝试更新
                        if primary_key and primary_key in data:
                            update_values = {k: v for k, v in data.items() if k != primary_key}
                            set_clause = ', '.join([f"{key} = ?" for key in update_values.keys()])
                            query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key} = ?"
                            values = list(update_values.values()) + [data[primary_key]]
                            client.execute_query(query, values)
                        else:
                            raise
                return True
            except Exception as e:
                client.close()
                if attempt < max_retries - 1 and "database is locked" in str(e).lower():
                    import time
                    time.sleep(retry_delay * (attempt + 1))  # 指数退避
                    continue
                else:
                    logger.error(f"Execute upsert failed after {attempt + 1} attempts: {str(e)}")
                    return False
            finally:
                client.close()
    
    def _is_sqlite(self, client: DBClient) -> bool:
        """检查客户端是否为SQLite"""
        return client.db_type == 'sqlite'
    
    def sync_table_structure(self, data_source_id: int, table_name: str, model_fields: List[Dict[str, Any]], primary_key: str = None) -> bool:
        """同步表结构，确保表存在且字段与模型定义一致
        
        Args:
            data_source_id: 数据源ID
            table_name: 表名
            model_fields: 模型字段列表，每个字段包含 'field_id' 和其他属性
            primary_key: 主键字段名
            
        Returns:
            bool: 是否成功同步
        """
        try:
            client = self.get_client(data_source_id=data_source_id)
            
            # 获取当前表的字段信息
            try:
                current_columns = client.get_table_columns(table_name)
                current_column_names = {col['name'] for col in current_columns}
                current_pks = set(client.get_primary_keys(table_name))
            except Exception:
                # 表不存在，需要创建
                current_column_names = set()
                current_pks = set()
            
            # 从模型字段获取期望的字段名
            expected_columns = {field['field_id'] for field in model_fields} if model_fields else set()
            if primary_key and primary_key not in expected_columns:
                expected_columns.add(primary_key)
            
            # 如果表不存在，创建表
            if not current_column_names:
                if self._create_table(client, table_name, model_fields, primary_key):
                    logger.info(f"成功创建表 {table_name}")
                    return True
                else:
                    logger.error(f"创建表 {table_name} 失败")
                    return False
            
            # 检查是否需要添加新字段
            columns_to_add = expected_columns - current_column_names
            if columns_to_add:
                for column_name in columns_to_add:
                    if self._add_column(client, table_name, column_name):
                        logger.info(f"成功添加字段 {column_name} 到表 {table_name}")
                    else:
                        logger.error(f"添加字段 {column_name} 到表 {table_name} 失败")
            
            # 检查主键是否一致（SQLite需要重建表来修改主键）
            if primary_key and primary_key not in current_pks:
                if self._recreate_table_with_correct_pk(client, table_name, model_fields, primary_key, current_columns):
                    logger.info(f"成功重建表 {table_name} 以修正主键")
                else:
                    logger.warning(f"重建表 {table_name} 修正主键失败，继续使用现有结构")
            
            return True
            
        except Exception as e:
            logger.error(f"同步表结构失败 {table_name}: {str(e)}")
            return False
    
    def _create_table(self, client: DBClient, table_name: str, model_fields: List[Dict[str, Any]], primary_key: str = None) -> bool:
        """创建表"""
        try:
            if not self._is_sqlite(client):
                logger.warning("目前仅支持SQLite的表创建")
                return False
            
            # 构建CREATE TABLE语句
            columns_def = []
            field_names = []
            
            # 添加模型字段
            if model_fields:
                for field in model_fields:
                    field_name = field['field_id']
                    field_names.append(field_name)
                    columns_def.append(f"{field_name} TEXT")
            
            # 确保主键字段存在
            if primary_key and primary_key not in field_names:
                columns_def.append(f"{primary_key} TEXT")
                field_names.append(primary_key)
            
            if not columns_def:
                logger.error("无法创建空表")
                return False
            
            # 添加主键约束
            columns_str = ", ".join(columns_def)
            if primary_key:
                create_sql = f"CREATE TABLE {table_name} ({columns_str}, PRIMARY KEY ({primary_key}))"
            else:
                create_sql = f"CREATE TABLE {table_name} ({columns_str})"
            
            # 执行创建表
            conn = sqlite3.connect(client.connection_string.replace('sqlite:///', ''))
            cursor = conn.cursor()
            cursor.execute(create_sql)
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"创建表失败 {table_name}: {str(e)}")
            return False
    
    def _add_column(self, client: DBClient, table_name: str, column_name: str) -> bool:
        """添加字段到现有表"""
        try:
            if not self._is_sqlite(client):
                logger.warning("目前仅支持SQLite的字段添加")
                return False
            
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT"
            
            conn = sqlite3.connect(client.connection_string.replace('sqlite:///', ''))
            cursor = conn.cursor()
            cursor.execute(alter_sql)
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"添加字段失败 {table_name}.{column_name}: {str(e)}")
            return False
    
    def _recreate_table_with_correct_pk(self, client: DBClient, table_name: str, model_fields: List[Dict[str, Any]], primary_key: str, current_columns: List[Dict]) -> bool:
        """重建表以修正主键（SQLite专用）"""
        try:
            if not self._is_sqlite(client):
                return False
            
            # 1. 创建临时表名
            temp_table_name = f"{table_name}_temp_{int(time.time())}"
            
            # 2. 获取所有字段（合并现有字段和模型字段）
            all_field_names = set()
            if current_columns:
                for col in current_columns:
                    all_field_names.add(col['name'])
            if model_fields:
                for field in model_fields:
                    all_field_names.add(field['field_id'])
            if primary_key:
                all_field_names.add(primary_key)
            
            # 3. 创建新表（带正确的主键）
            columns_def = []
            for field_name in all_field_names:
                columns_def.append(f"{field_name} TEXT")
            
            if not columns_def:
                return False
            
            columns_str = ", ".join(columns_def)
            if primary_key:
                create_sql = f"CREATE TABLE {temp_table_name} ({columns_str}, PRIMARY KEY ({primary_key}))"
            else:
                create_sql = f"CREATE TABLE {temp_table_name} ({columns_str})"
            
            conn = sqlite3.connect(client.connection_string.replace('sqlite:///', ''))
            cursor = conn.cursor()
            cursor.execute(create_sql)
            
            # 4. 迁移数据
            if current_columns:
                current_column_names = [col['name'] for col in current_columns]
                select_columns = ", ".join(current_column_names)
                insert_columns = ", ".join(current_column_names)
                migrate_sql = f"INSERT INTO {temp_table_name} ({insert_columns}) SELECT {select_columns} FROM {table_name}"
                cursor.execute(migrate_sql)
            
            # 5. 删除旧表
            cursor.execute(f"DROP TABLE {table_name}")
            
            # 6. 重命名新表
            cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"重建表修正主键失败 {table_name}: {str(e)}")
            # 清理临时表（如果存在）
            try:
                conn = sqlite3.connect(client.connection_string.replace('sqlite:///', ''))
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {temp_table_name}")
                conn.commit()
                conn.close()
            except:
                pass
            return False

    def execute_batch_upsert(self, data_source_id: int = None, data_source_name: str = None, table_name: str = None, data_list: List[Dict[str, Any]] = None, primary_key: str = None) -> Dict[str, int]:
        """批量执行UPSERT操作（存在则更新，不存在则插入）
        
        Returns:
            Dict with 'success_count' and 'failed_count'
        """
        if data_source_name:
            data_source = self.get_data_source_by_name(data_source_name)
            if not data_source:
                raise ValueError(f"DataSource not found: {data_source_name}")
            data_source_id = data_source.id
        
        if not data_list:
            return {"success_count": 0, "failed_count": 0}
        
        client = self.get_client(data_source_id=data_source_id)
        success_count = 0
        failed_count = 0
        
        try:
            if self._is_sqlite(client):
                # SQLite 批量 INSERT OR REPLACE
                if data_list:
                    # 获取所有字段名（取第一条记录的字段）
                    all_columns = set()
                    for record in data_list:
                        all_columns.update(record.keys())
                    all_columns = sorted(list(all_columns))
                    
                    columns_str = ', '.join(all_columns)
                    placeholders = ', '.join(['?' for _ in all_columns])
                    query = f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                    
                    # 准备批量数据
                    batch_data = []
                    for record in data_list:
                        row_data = [record.get(col) for col in all_columns]
                        batch_data.append(row_data)
                    
                    # 执行批量操作
                    conn = sqlite3.connect(client.connection_string.replace('sqlite:///', ''))
                    cursor = conn.cursor()
                    cursor.executemany(query, batch_data)
                    conn.commit()
                    
                    conn.close()
                    success_count = len(data_list)
            else:
                # 其他数据库：逐条处理（可以后续优化）
                for data in data_list:
                    if self.execute_upsert(data_source_id, data_source_name, table_name, data, primary_key):
                        success_count += 1
                    else:
                        failed_count += 1
                        
        except Exception as e:
            logger.error(f"Execute batch upsert failed: {str(e)}")
            failed_count = len(data_list) - success_count
        finally:
            client.close()
            
        return {"success_count": success_count, "failed_count": failed_count}


data_source_manager = DataSourceManager()