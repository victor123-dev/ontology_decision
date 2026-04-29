"""
供应链运营相关VO类
"""
from typing import Optional, List, Dict
from pydantic import BaseModel


class PurchaseOrderVO(BaseModel):
    """采购订单视图对象"""
    po_id: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    order_date: str = ""
    expected_delivery_date: str = ""
    actual_delivery_date: Optional[str] = None
    status: str = ""
    total_amount: float = 0.0
    is_delayed: bool = False
    delay_days: int = 0


class InventoryAlertVO(BaseModel):
    """库存预警视图对象"""
    inventory_id: str = ""
    material_id: str = ""
    material_name: str = ""
    material_type: str = ""
    available_quantity: float = 0.0
    safety_stock_level: float = 0.0
    reserved_quantity: float = 0.0
    in_transit_quantity: float = 0.0
    health_ratio: float = 0.0
    location: str = ""


class WorkOrderVO(BaseModel):
    """工单视图对象"""
    work_order_id: str = ""
    product_id: str = ""
    product_name: str = ""
    planned_quantity: float = 0.0
    expected_output_qty: float = 0.0
    planned_start_date: str = ""
    planned_completion_date: str = ""
    actual_start_date: Optional[str] = None
    status: str = ""
    is_delayed: bool = False
    delay_days: int = 0


class CustomerOrderVO(BaseModel):
    """客户订单视图对象"""
    order_id: str = ""
    customer_id: str = ""
    customer_name: str = ""
    customer_po_number: str = ""
    product_id: str = ""
    product_name: str = ""
    quantity: float = 0.0
    unit_price: float = 0.0
    total_amount: float = 0.0
    order_date: str = ""
    required_date: str = ""
    status: str = ""
    is_upcoming: bool = False
    days_remaining: int = 0


class SupplierPerformanceVO(BaseModel):
    """供应商交付表现视图对象"""
    supplier_id: str = ""
    supplier_name: str = ""
    total_orders: int = 0
    on_time_count: int = 0
    on_time_rate: float = 0.0
