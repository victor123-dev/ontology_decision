from my_ontology_sdk import OntologyClient

# 创建公共OntologyClient实例，给多个service共同使用
_ontology_client = None

def get_ontology_client():
    """获取OntologyClient单例实例"""
    global _ontology_client
    if _ontology_client is None:
        _ontology_client = OntologyClient(
            api_url="http://localhost:8080",  # 后端API地址
            api_key="your-api-key"  # API密钥（如果需要）
        )
    return _ontology_client
