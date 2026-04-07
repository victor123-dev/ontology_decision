from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.config import settings
from typing import Optional, Dict, Any, List
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MongoDBClient:
    _instance: Optional['MongoDBClient'] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self.connect()
    
    def connect(self) -> bool:
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGO_URL}")
            self._client = MongoClient(
                settings.MONGO_URL,
                serverSelectionTimeoutMS=5000
            )
            self._client.admin.command('ping')
            self._db = self._client[settings.MONGO_DB_NAME]
            logger.info(f"Successfully connected to MongoDB database: {settings.MONGO_DB_NAME}")
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            return False
    
    def get_db(self) -> Optional[Database]:
        if self._db is None:
            self.connect()
        return self._db
    
    def get_collection(self, collection_name: str):
        db = self.get_db()
        if db is not None:
            return db[collection_name]
        return None
    
    def is_connected(self) -> bool:
        try:
            if self._client:
                self._client.admin.command('ping')
                return True
            return False
        except Exception:
            return False
    
    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")


def get_mongo_client() -> MongoDBClient:
    return MongoDBClient()
