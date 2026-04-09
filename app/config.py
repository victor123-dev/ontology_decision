from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # FastAPI配置
    APP_NAME: str = "Python Project Template"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8080
    
    # Neo4j配置
    NEO4J_URI: Optional[str] = None
    NEO4J_USER: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None
    NEO4J_DATA_DATABASE: str = "neo4j"
    
    # Azure OpenAI配置
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = None
    AZURE_OPENAI_GPT_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_EMBED_DEPLOYMENT: Optional[str] = None
    
    # 阿里云DashScope配置
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OWEN_3_5_PLUS_MODEL: str = "qwen3.5-plus"
    
    # Milvus配置
    MILVUS_URL: Optional[str] = None
    MILVUS_USER: Optional[str] = None
    MILVUS_PASSWORD: Optional[str] = None
    
    # SQLite数据库配置
    DATABASE_URL: str = "sqlite:///data.db"
    
    # MongoDB配置
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "commander"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
