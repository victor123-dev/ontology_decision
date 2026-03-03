from typing import List
from openai import AzureOpenAI
from app.config import settings

class EmbeddingService:
    def __init__(self):
        # 初始化Azure OpenAI客户端
        self.client = AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION
        )
        self.embedding_deployment = settings.AZURE_OPENAI_EMBED_DEPLOYMENT
    
    def get_embedding(self, text: str) -> List[float]:
        """获取单个文本的embedding向量"""
        if not text:
            return []
        
        response = self.client.embeddings.create(
            input=text,
            model=self.embedding_deployment
        )
        
        return response.data[0].embedding
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取多个文本的embedding向量"""
        if not texts:
            return []
        
        response = self.client.embeddings.create(
            input=texts,
            model=self.embedding_deployment
        )
        
        return [data.embedding for data in response.data]

# 创建全局实例（仅当配置存在时）
embedding_service = None
if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_API_VERSION and settings.AZURE_OPENAI_EMBED_DEPLOYMENT:
    try:
        embedding_service = EmbeddingService()
    except Exception as e:
        print(f"初始化EmbeddingService失败: {str(e)}")
        embedding_service = None
