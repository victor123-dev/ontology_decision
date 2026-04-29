"""
外部供应链风险相关VO类
"""
from typing import Optional, List, Dict
from pydantic import BaseModel


class AffectedSupplierVO(BaseModel):
    """受影响供应商视图对象"""
    supplier_id: str = ""
    supplier_name: str = ""
    association_type: str = ""
    impact_level: str = ""
    note: str = ""


class RiskEventVO(BaseModel):
    """风险事件视图对象"""
    risk_id: str = ""
    title: str = ""
    risk_category: str = ""
    risk_level: str = ""
    supplier_id: Optional[str] = None
    supplier_name: str = ""
    customer_id: Optional[str] = None
    material_id: Optional[str] = None
    status: str = ""
    impact_scope: Optional[str] = None
    estimated_impact_days: int = 0
    detected_at: Optional[str] = None
    event_date: Optional[str] = None
    source_name: Optional[str] = None
    confidence_score: float = 0.0
    affected_suppliers: List[AffectedSupplierVO] = []
    description: str = ""


class RiskStatisticsVO(BaseModel):
    """风险统计视图对象"""
    by_category: Dict[str, int] = {}
    by_level: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    total_count: int = 0


class RiskTrendVO(BaseModel):
    """风险趋势视图对象"""
    date: str = ""
    count: int = 0


class SupplierRiskImpactVO(BaseModel):
    """供应商风险影响视图对象"""
    supplier_id: str = ""
    supplier_name: str = ""
    risk_count: int = 0
    max_impact_level: str = ""
    association_types: List[str] = []
