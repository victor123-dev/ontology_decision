from fastapi import APIRouter, Depends, HTTPException
import os
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.utils.shared_utils import get_db
from app.services.excel_import_export_service import get_excel_service, ExcelImportExportService

router = APIRouter()

@router.post("/excel/export")
def export_to_excel(
    db: Session = Depends(get_db)
):
    """导出业务模型和实例数据到doc目录下的Excel文件"""
    try:
        excel_service = get_excel_service()
        export_result = excel_service.export_to_excel_file(db)
        
        if export_result["success"]:
            return {"message": f"Excel file exported successfully to {export_result['file_path']}"}
        else:
            raise HTTPException(status_code=500, detail=f"Export failed: {export_result['error']}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.post("/excel/import")
def import_from_excel(
    db: Session = Depends(get_db)
):
    """从doc目录下的固定Excel文件导入业务模型和实例数据"""
    try:
        excel_service = get_excel_service()
        import_result = excel_service.import_from_excel_file(db)
        
        return import_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")