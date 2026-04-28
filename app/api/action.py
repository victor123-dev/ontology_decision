from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.action_service import get_action_service, ActionService
from app.utils.shared_utils import get_db
import traceback
from app.utils.logger import get_logger, get_request_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/actions")
def create_action(action_data: dict, action_service: ActionService = Depends(get_action_service)):
    try:
        action = action_service.create_action(action_data)
        if not action:
            raise HTTPException(status_code=500, detail="Failed to create action")
        return action
    except Exception as e:
        logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/actions")
def get_actions(
    model_id: str = None,
    action_service: ActionService = Depends(get_action_service)
):
    if model_id:
        return action_service.get_actions_by_model(model_id)
    return action_service.get_actions()


@router.get("/actions/{action_id}")
def get_action(action_id: str, action_service: ActionService = Depends(get_action_service)):
    action = action_service.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.put("/actions/{action_id}")
def update_action(
    action_id: str,
    update_data: dict,
    action_service: ActionService = Depends(get_action_service)
):
    action = action_service.update_action(action_id, update_data)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found or update failed")
    return action


@router.delete("/actions/{action_id}")
def delete_action(action_id: str, action_service: ActionService = Depends(get_action_service)):
    success = action_service.delete_action(action_id)
    if not success:
        raise HTTPException(status_code=404, detail="Action not found or delete failed")
    return {"message": "Action deleted successfully"}


@router.post("/actions/execute")
def execute_action(
    execution_data: dict,
    action_service: ActionService = Depends(get_action_service),
    db: Session = Depends(get_db)
):
    try:
        action_id = execution_data.get("action_id")
        parameters = execution_data.get("parameters", {})
        result = action_service.execute_action(action_id, parameters, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
