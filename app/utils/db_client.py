from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import sqlite3
import json
from typing import List, Dict, Any

Base = declarative_base()

class DBClient:
    def __init__(self, db_type: str, connection_string: str):
        self.db_type = db_type
        self.connection_string = connection_string
        self.engine = None
        self.Session = None
        
    def connect(self):
        if self.db_type == 'sqlite':
            # 自定义JSON编码器，确保中文字符不被转义
            class ChineseJSONEncoder(json.JSONEncoder):
                def encode(self, obj):
                    # 使用ensure_ascii=False来保持中文字符
                    return super().encode(obj)
                
                def iterencode(self, obj, _one_shot=False):
                    # 重写iterencode方法以确保ensure_ascii=False
                    return json.JSONEncoder.iterencode(self, obj, _one_shot)
            
            # 创建引擎并配置JSON序列化
            self.engine = create_engine(
                self.connection_string,
                json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
                json_deserializer=json.loads
            )
        elif self.db_type == 'mysql':
            # 预留MySQL支持
            pass
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        self.Session = sessionmaker(bind=self.engine)
        return self.engine
    
    def get_tables(self) -> List[str]:
        if not self.engine:
            self.connect()
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        if not self.engine:
            self.connect()
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        return columns
    
    def get_primary_keys(self, table_name: str) -> List[str]:
        if not self.engine:
            self.connect()
        inspector = inspect(self.engine)
        pk_constraint = inspector.get_pk_constraint(table_name)
        return pk_constraint.get('constrained_columns', [])
    
    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """获取表的外键约束信息"""
        if not self.engine:
            self.connect()
        inspector = inspect(self.engine)
        try:
            foreign_keys = inspector.get_foreign_keys(table_name)
            return foreign_keys
        except Exception as e:
            # 某些数据库可能不支持外键检测，返回空列表
            print(f"Warning: Could not get foreign keys for table {table_name}: {e}")
            return []
    
    def execute_query(self, query: str, params=None) -> List[Dict]:
        if self.db_type == 'sqlite':
            conn = sqlite3.connect(self.connection_string.replace('sqlite:///', ''))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # 检查是否是查询语句（SELECT）
            is_select = query.strip().upper().startswith('SELECT')
            if is_select:
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
            else:
                # 对于非查询语句（INSERT/UPDATE/DELETE），提交事务并返回空列表
                conn.commit()
                result = []
            
            conn.close()
            return result
        else:
            # 其他数据库类型的实现
            pass
    
    def close(self):
        if self.engine:
            self.engine.dispose()
