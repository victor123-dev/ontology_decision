from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.utils.shared_utils import get_db
from app.services.sdk_generator import get_sdk_generator, SDKGenerator

router = APIRouter()
import traceback
import logging

logger = logging.getLogger(__name__)



@router.post("/sdk/generate")
def generate_sdk(
    request_data: Dict[str, Any],
    sdk_generator: SDKGenerator = Depends(get_sdk_generator),
    db: Session = Depends(get_db)
):
    """
    生成Python Ontology SDK
    
    - **output_path**: SDK输出路径（可选，默认为./ontology_sdk）
    - **package_name**: SDK包名（可选，默认为ontology_sdk）
    - **version**: SDK版本号（可选，默认为1.0.0）
    """
    try:
        package_name = request_data.get("package_name", "ontology_sdk")
        # 如果没有提供 output_path，则根据 package_name 自动生成
        if "output_path" in request_data:
            output_path = request_data["output_path"]
        else:
            output_path = f"./sdk/{package_name}"
        version = request_data.get("version", "1.0.0")
        
        result = sdk_generator.generate(
            db=db,
            output_path=output_path,
            package_name=package_name,
            version=version
        )
        
        return {
            "success": True,
            "message": "SDK generated successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"SDK generation failed: {str(e)}")


@router.get("/sdk/info")
def get_sdk_info(
    sdk_generator: SDKGenerator = Depends(get_sdk_generator),
    db: Session = Depends(get_db)
):
    """
    获取SDK生成的基本信息，包括可用的业务模型和关系
    """
    try:
        info = sdk_generator.get_info(db)
        return {
            "success": True,
            "data": info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SDK info: {str(e)}")
