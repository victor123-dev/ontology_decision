from typing import Optional, Dict, Any, List
from bson.objectid import ObjectId
from datetime import datetime, timezone
from app.utils.mongo_client import get_mongo_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ActionDAO:
    COLLECTION_NAME = "actions"
    
    def __init__(self):
        self.client = get_mongo_client()
        self.collection = self.client.get_collection(self.COLLECTION_NAME)
    
    def create_action(self, action_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            now = datetime.now(timezone.utc)
            action_data["created_at"] = now
            action_data["updated_at"] = now
            
            result = self.collection.insert_one(action_data)
            if result.inserted_id:
                action_data["id"] = str(result.inserted_id)
                action_data.pop('_id', None)
                return action_data
            return None
        except Exception as e:
            logger.error(f"Error creating action: {e}")
            return None
    
    def get_action_by_id(self, action_id: str) -> Optional[Dict[str, Any]]:
        try:
            if not ObjectId.is_valid(action_id):
                return None
            action = self.collection.find_one({"_id": ObjectId(action_id)})
            if action:
                action["id"] = str(action["_id"])
                action.pop('_id', None)
            return action
        except Exception as e:
            logger.error(f"Error getting action by id {action_id}: {e}")
            return None
    
    def get_actions(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        try:
            query = filters or {}
            cursor = self.collection.find(query)
            actions = []
            for action in cursor:
                action["id"] = str(action["_id"])
                action.pop('_id', None)
                actions.append(action)
            return actions
        except Exception as e:
            logger.error(f"Error getting actions: {e}")
            return []
    
    def get_actions_by_model(self, business_model_id: str) -> List[Dict[str, Any]]:
        return self.get_actions({"target_model_id": business_model_id})
    
    def update_action(self, action_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if not ObjectId.is_valid(action_id):
                return None
            
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = self.collection.update_one(
                {"_id": ObjectId(action_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return self.get_action_by_id(action_id)
            return None
        except Exception as e:
            logger.error(f"Error updating action {action_id}: {e}")
            return None
    
    def delete_action(self, action_id: str) -> bool:
        try:
            if not ObjectId.is_valid(action_id):
                return False
            result = self.collection.delete_one({"_id": ObjectId(action_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting action {action_id}: {e}")
            return False


def get_action_dao() -> ActionDAO:
    return ActionDAO()
