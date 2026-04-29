import traceback
from fastapi import APIRouter, HTTPException

from app.services.dashbaord.operation_service import OperationService
from app.services.dashbaord.risk_service import RiskService
from app.utils.logger import get_logger
from app.vo.alertdashboard.kpi_vo import KpiMetricVO

router = APIRouter(prefix="/alert-dashboard", tags=["alert-dashboard"])
logger = get_logger(__name__)
operation_service = OperationService()
risk_service = RiskService()


# ==================== 供应链运营KPI API ====================

# ==================== 供应链运营KPI API ====================

@router.get("/kpi/po-execution-rate")
def get_po_execution_rate():
    """获取采购订单执行率"""
    try:
        rate = operation_service.get_po_execution_rate()
        return KpiMetricVO(val=rate, trendVal=0)
    except Exception as e:
        logger.error(f"获取采购订单执行率失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取采购订单执行率失败: {str(e)}")


@router.get("/kpi/inventory-health-rate")
def get_inventory_health_rate():
    """获取库存健康度"""
    try:
        rate = operation_service.get_inventory_health_rate()
        return KpiMetricVO(val=rate, trendVal=0)
    except Exception as e:
        logger.error(f"获取库存健康度失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取库存健康度失败: {str(e)}")


@router.get("/kpi/wo-on-time-delivery-rate")
def get_wo_on_time_delivery_rate():
    """获取工单准时交付率"""
    try:
        rate = operation_service.get_wo_on_time_delivery_rate()
        return KpiMetricVO(val=rate, trendVal=0)
    except Exception as e:
        logger.error(f"获取工单准时交付率失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取工单准时交付率失败: {str(e)}")


@router.get("/kpi/monthly-customer-order-amount")
def get_monthly_customer_order_amount():
    """获取本月客户订单金额"""
    try:
        amount = operation_service.get_monthly_customer_order_amount()
        return KpiMetricVO(val=amount, trendVal=0)
    except Exception as e:
        logger.error(f"获取本月客户订单金额失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取本月客户订单金额失败: {str(e)}")


@router.get("/kpi/active-risk-count")
def get_active_risk_count():
    """获取活跃风险数"""
    try:
        count = risk_service.get_active_risk_count()
        return KpiMetricVO(val=count, trendVal=0)
    except Exception as e:
        logger.error(f"获取活跃风险数失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取活跃风险数失败: {str(e)}")


@router.get("/kpi/high-risk-supplier-count")
def get_high_risk_supplier_count():
    """获取高风险供应商数"""
    try:
        count = risk_service.get_high_risk_supplier_count()
        return KpiMetricVO(val=count, trendVal=0)
    except Exception as e:
        logger.error(f"获取高风险供应商数失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取高风险供应商数失败: {str(e)}")


# ==================== 采购执行 API ====================

@router.get("/purchase/delayed-orders")
def get_delayed_purchase_orders():
    """获取延迟采购订单"""
    try:
        orders = operation_service.get_delayed_purchase_orders()
        return orders
    except Exception as e:
        logger.error(f"获取延迟采购订单失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取延迟采购订单失败: {str(e)}")


@router.get("/purchase/supplier-performance")
def get_supplier_delivery_performance():
    """获取供应商交付表现"""
    try:
        performance = operation_service.get_supplier_delivery_performance()
        return performance
    except Exception as e:
        logger.error(f"获取供应商交付表现失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取供应商交付表现失败: {str(e)}")


# ==================== 库存健康 API ====================

@router.get("/inventory/alerts")
def get_low_inventory_alerts():
    """获取低库存预警"""
    try:
        alerts = operation_service.get_low_inventory_alerts()
        return alerts
    except Exception as e:
        logger.error(f"获取低库存预警失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取低库存预警失败: {str(e)}")


# ==================== 工单跟踪 API ====================

@router.get("/work-order/delayed")
def get_delayed_work_orders():
    """获取延期工单"""
    try:
        orders = operation_service.get_delayed_work_orders()
        return orders
    except Exception as e:
        logger.error(f"获取延期工单失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取延期工单失败: {str(e)}")


# ==================== 销售订单 API ====================

@router.get("/customer-order/upcoming")
def get_upcoming_customer_orders():
    """获取即将到期订单"""
    try:
        orders = operation_service.get_upcoming_customer_orders()
        return orders
    except Exception as e:
        logger.error(f"获取即将到期订单失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取即将到期订单失败: {str(e)}")

@router.get("/customer-order/trend")
def get_customer_order_trend():
    """获取客户订单交付趋势(近30天)"""
    try:
        trend = operation_service.get_customer_order_trend(days=30)
        return trend
    except Exception as e:
        logger.error(f"获取客户订单交付趋势失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取客户订单交付趋势失败: {str(e)}")


# ==================== 风险监控 API ====================

@router.get("/risks/active")
def get_active_risks():
    """获取活跃风险列表"""
    try:
        risks = risk_service.get_active_risks()
        return risks
    except Exception as e:
        logger.error(f"获取活跃风险失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取活跃风险失败: {str(e)}")


@router.get("/risks/statistics")
def get_risk_statistics():
    """获取风险统计数据"""
    try:
        stats = risk_service.get_risk_statistics()
        return stats
    except Exception as e:
        logger.error(f"获取风险统计失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取风险统计失败: {str(e)}")


@router.get("/risks/trend")
def get_risk_trend(days: int = 30):
    """获取风险趋势"""
    try:
        trend = risk_service.get_risk_trend(days)
        return trend
    except Exception as e:
        logger.error(f"获取风险趋势失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取风险趋势失败: {str(e)}")


@router.get("/risks/top-suppliers")
def get_top_affected_suppliers():
    """获取受影响供应商TOP5"""
    try:
        suppliers = risk_service.get_top_affected_suppliers()
        return suppliers
    except Exception as e:
        logger.error(f"获取受影响供应商失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取受影响供应商失败: {str(e)}") 