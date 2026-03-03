from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType
from app.config import settings
from typing import Optional, List, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MilvusClient:
    def __init__(self):
        self.connected = False
        self.connect()
    
    def connect(self):
        """连接到Milvus服务器"""
        if self.connected:
            logger.info("已经连接到Milvus服务器")
            return
        
        logger.info(f"连接到Milvus服务器: {settings.MILVUS_URL}")
        try:
            connections.connect(
                alias="default",
                uri=settings.MILVUS_URL,
                user=settings.MILVUS_USER,
                password=settings.MILVUS_PASSWORD
            )
            self.connected = True
            logger.debug("Milvus连接初始化完成")
        except Exception as e:
            logger.error(f"连接失败: {str(e)}")
            raise
    
    def disconnect(self):
        logger.info("断开Milvus服务器连接")
        connections.disconnect(alias="default")
        self.connected = False
    
    def create_collection(self, collection_name: str, dim: int, fields: Optional[List[FieldSchema]] = None, description: str = ""):
        """创建集合"""
        self.connect()
        logger.info(f"创建Milvus集合: {collection_name}, 维度: {dim}")
        
        # 创建默认字段
        default_fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
        ]
        
        # 如果提供了额外字段，则合并
        if fields:
            default_fields.extend(fields)
        
        schema = CollectionSchema(fields=default_fields, description=description)
        collection = Collection(name=collection_name, schema=schema)
        
        logger.info(f"Milvus集合创建完成: {collection_name}")
        return collection
    
    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """获取已存在的集合"""
        self.connect()
        logger.info(f"获取Milvus集合: {collection_name}")
        try:
            collection = Collection(name=collection_name)
            logger.debug(f"成功获取Milvus集合: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"获取Milvus集合失败: {collection_name} | 错误: {str(e)}")
            return None
    
    def insert_data(self, collection_name: str, data: List[Dict[str, Any]]):
        """插入数据到集合"""
        self.connect()
        logger.info(f"向集合 {collection_name} 插入数据: {len(data)} 条")
        collection = self.get_collection(collection_name)
        if not collection:
            raise Exception(f"集合不存在: {collection_name}")
        
        result = collection.insert(data)
        logger.info(f"数据插入完成，插入ID: {result.primary_keys[:10]}...")
        return result.primary_keys
    
    def create_index(self, collection_name: str, field_name: str = "embedding", index_type: str = "IVF_FLAT", metric_type: str = "L2", params: Dict[str, Any] = None):
        """为集合创建索引"""
        self.connect()
        logger.info(f"为集合 {collection_name} 的字段 {field_name} 创建索引")
        collection = self.get_collection(collection_name)
        if not collection:
            raise Exception(f"集合不存在: {collection_name}")
        
        # 默认索引参数
        default_params = {"nlist": 128}
        if params:
            default_params.update(params)
        
        index = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": default_params
        }
        
        collection.create_index(field_name=field_name, index_params=index)
        logger.info(f"索引创建完成")
        
    def search_vectors(self, collection_name: str, query_vectors: List[List[float]], limit: int = 10, output_fields: Optional[List[str]] = None, params: Dict[str, Any] = None):
        """向量检索"""
        self.connect()
        logger.info(f"在集合 {collection_name} 中检索向量: {len(query_vectors)} 个查询向量")
        collection = self.get_collection(collection_name)
        if not collection:
            raise Exception(f"集合不存在: {collection_name}")
        
        # 加载集合到内存
        collection.load()
        
        # 默认检索参数
        default_params = {"nprobe": 10}
        if params:
            default_params.update(params)
        
        # 默认输出字段
        default_output_fields = ["id"]
        if output_fields:
            default_output_fields.extend(output_fields)
        
        results = collection.search(
            data=query_vectors,
            anns_field="embedding",
            param=default_params,
            limit=limit,
            output_fields=default_output_fields
        )
        
        logger.info(f"检索完成，返回 {len(results)} 组结果")
        
        # 格式化结果
        formatted_results = []
        for i, result in enumerate(results):
            hits = []
            for hit in result:
                hits.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "fields": hit.fields
                })
            formatted_results.append({
                "query_index": i,
                "hits": hits
            })
        
        return formatted_results
    
    def query(self, collection_name: str, expr: str, output_fields: Optional[List[str]] = None, 
              limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """执行标量查询（基于字段过滤）"""
        self.connect()
        logger.info(f"在集合 {collection_name} 中执行标量查询: {expr}")
        collection = self.get_collection(collection_name)
        if not collection:
            raise Exception(f"集合不存在: {collection_name}")
        
        # 加载集合到内存
        collection.load()
        
        # 默认输出字段
        default_output_fields = ["id"]
        if output_fields:
            default_output_fields.extend(output_fields)
        
        try:
            # 执行标量查询
            results = collection.query(
                expr=expr,
                output_fields=default_output_fields,
                limit=limit,
                offset=offset
            )
            
            logger.info(f"标量查询完成，返回 {len(results)} 条记录")
            return results
            
        except Exception as e:
            logger.error(f"标量查询失败: {str(e)}")
            raise
    
    def delete_collection(self, collection_name: str):
        """删除集合"""
        self.connect()
        logger.info(f"删除Milvus集合: {collection_name}")
        collection = self.get_collection(collection_name)
        if not collection:
            logger.warning(f"集合不存在: {collection_name}")
            return False
        
        collection.drop()
        logger.info(f"集合删除完成: {collection_name}")
        return True

# 创建单例实例（仅当配置存在时）
milvus_client = None
if settings.MILVUS_URL and settings.MILVUS_USER and settings.MILVUS_PASSWORD:
    try:
        milvus_client = MilvusClient()
    except Exception as e:
        logger.error(f"初始化Milvus客户端失败: {str(e)}")
        milvus_client = None