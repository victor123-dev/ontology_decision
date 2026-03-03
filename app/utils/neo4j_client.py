from neo4j import GraphDatabase
from app.config import settings
from typing import Optional, List, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

class Neo4jClient:
    def __init__(self):
        logger.info(f"连接到Neo4j数据库: {settings.NEO4J_URI}")
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        logger.debug("Neo4j驱动初始化完成")
    
    def close(self):
        logger.info("关闭Neo4j数据库连接")
        self.driver.close()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, database: str = settings.NEO4J_DATA_DATABASE) -> List[Dict[str, Any]]:
        """执行Cypher查询并返回结果"""
        logger.debug(f"执行查询: {query} | 参数: {params}")
        try:
            with self.driver.session(database=database) as session:
                result = session.run(query, params)
                data = [record.data() for record in result]
                logger.debug(f"查询结果: {len(data)} 条记录")
                return data
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            logger.error(f"失败的查询: {query} | 参数: {params}")
            raise
    
    def execute_query_record(self, query: str, params: Optional[Dict[str, Any]] = None, database: str = settings.NEO4J_DATA_DATABASE) -> List[Any]:
        """执行Cypher查询并返回原始record对象，保留完整的Neo4j元素信息"""
        logger.debug(f"执行查询(record模式): {query} | 参数: {params}")
        try:
            with self.driver.session(database=database) as session:
                result = session.run(query, params)
                records = list(result)
                logger.debug(f"查询结果(record模式): {len(records)} 条记录")
                return records
        except Exception as e:
            logger.error(f"查询执行失败(record模式): {str(e)}")
            logger.error(f"失败的查询: {query} | 参数: {params}")
            raise
    
    def execute_write_query(self, query: str, params: Optional[Dict[str, Any]] = None, database: str = settings.NEO4J_DATA_DATABASE) -> Any:
        """执行写查询并返回结果"""
        logger.debug(f"执行写查询: {query} | 参数: {params}")
        try:
            with self.driver.session(database=database) as session:
                with session.begin_transaction() as tx:
                    result = tx.run(query, params).single()
                data = result.data() if result else None
                logger.debug(f"写查询结果: {data}")
                return data
        except Exception as e:
            logger.error(f"写查询执行失败: {str(e)}")
            logger.error(f"失败的查询: {query} | 参数: {params}")
            raise

# 创建单例实例（仅当配置存在时）
neo4j_client = None
if settings.NEO4J_URI and settings.NEO4J_USER and settings.NEO4J_PASSWORD:
    try:
        neo4j_client = Neo4jClient()
    except Exception as e:
        logger.error(f"初始化Neo4j客户端失败: {str(e)}")
        neo4j_client = None
