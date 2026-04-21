import traceback
from datetime import datetime

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, HTTPException

from app.services.dashbaord.alert_service import AlertService
from app.services.dashbaord.kpi_service import KpiService
from app.services.dashbaord.logistics_service import LogistisService
from app.services.dashbaord.map_service import MapService
from app.services.dashbaord.report_service import ReportService
from app.utils.logger import get_logger
from app.vo.alertdashboard.char_vo import CharVO
from app.vo.alertdashboard.kpi_vo import KpiMetricVO, MonthlySalesMetricsVO

router = APIRouter(prefix="/alert-dashboard", tags=["alert-dashboard"])
logger = get_logger(__name__)
kpi_service = KpiService()
logistics_service = LogistisService()
alert_service = AlertService()
map_service = MapService()
report_service = ReportService()


# ==================== API 路由 ====================

@router.get("/kpi/purchase-on-time-rate")
def get_purchase_on_time_rate():
    """获取采购准时率KPI"""
    try:
        current_date = datetime.today()
        current_month = current_date.strftime("%Y-%m")
        last_month = (current_date - relativedelta(months=1)).strftime("%Y-%m")

        current_rate = kpi_service.get_purchase_on_time_rate(current_month)
        last_month_rate = kpi_service.get_purchase_on_time_rate(last_month)

        return KpiMetricVO(
            val=current_rate,
            trendVal=((current_rate - last_month_rate) / last_month_rate * 100) if last_month_rate > 0 else 0
        )
    except Exception as e:
        logger.error(f"获取采购准时率失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取采购准时率失败: {str(e)}")


@router.get("/kpi/monthly-sales")
def get_monthly_sales():
    """获取月销售数据KPI（合并金额和数量）"""
    try:
        current_date = datetime.today()
        current_month = current_date.strftime("%Y-%m")
        last_month = (current_date - relativedelta(months=1)).strftime("%Y-%m")

        # 使用合并后的查询方法，只查询一次数据库
        current_data = kpi_service.get_monthly_sales_data(current_month)
        last_month_data = kpi_service.get_monthly_sales_data(last_month)

        return MonthlySalesMetricsVO(
            monthlySalesAmount=KpiMetricVO(
                val=round(current_data["amount"] / 10000, 2)
,
                trendVal=((current_data["amount"] - last_month_data["amount"]) / last_month_data["amount"] * 100) if last_month_data["amount"] > 0 else 0
            ),
            monthlySalesQty=KpiMetricVO(
                val=current_data["qty"],
                trendVal=((current_data["qty"] - last_month_data["qty"]) / last_month_data["qty"] * 100) if last_month_data["qty"] > 0 else 0
            )
        )
    except Exception as e:
        logger.error(f"获取月销售数据失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取月销售数据失败: {str(e)}")

@router.get("/kpi/alert-count")
def get_alert_count():
    """获取预警数量KPI"""
    try:
        current_date = datetime.today()
        current_month = current_date.strftime("%Y-%m")
        last_month = (current_date - relativedelta(months=1)).strftime("%Y-%m")

        current_count = kpi_service.get_alert_count(current_month)
        last_month_count = kpi_service.get_alert_count(last_month)

        return KpiMetricVO(
            val=current_count,
            trendVal=current_count - last_month_count
        )
    except Exception as e:
        logger.error(f"获取预警数量失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取预警数量失败: {str(e)}")


@router.get("/kpi/alert-exec-count")
def get_alert_exec_count():
    """获取预警执行数量KPI"""
    try:
        current_date = datetime.today()
        current_month = current_date.strftime("%Y-%m")
        last_month = (current_date - relativedelta(months=1)).strftime("%Y-%m")

        current_count = 0
        last_month_count = 0

        return KpiMetricVO(
            val=current_count,
            trendVal=current_count - last_month_count
        )
    except Exception as e:
        logger.error(f"获取预警执行数量失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取预警执行数量失败: {str(e)}")


@router.get("/logistics")
def get_logistics_data() -> list[dict]:
    """获取物流动态数据"""
    try:
        logistics_list = logistics_service.get_all_logistics()
        # 使用 by_alias=True 确保使用别名（from 而不是 from_）
        return [log.model_dump(by_alias=True) for log in logistics_list]
    except Exception as e:
        logger.error(f"获取物流动态数据失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取物流动态数据失败: {str(e)}")



@router.get("/forecast")
def get_forecast_data():
    """获取需求预测数据（当前下一个月开始的6个月）"""
    try:
        # 计算当前时间的下一个月和后6个月
        today = datetime.today()
        # start_month: 当前下一个月
        next_month = today + relativedelta(months=1)
        start_month = next_month.strftime("%Y-%m")
        # end_month: 当前时间后6个月
        end_month = (today + relativedelta(months=6)).strftime("%Y-%m")
        return report_service.get_forecast_data(start_month, end_month)
    except Exception as e:
        logger.error(f"获取需求预测数据失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取需求预测数据失败: {str(e)}")


@router.get("/map")
def get_map_data():
    """获取地图数据"""
    try:
        return map_service.get_map_data()
    except Exception as e:
        logger.error(f"获取地图数据失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取地图数据失败: {str(e)}")


@router.get("/alerts")
def get_alert_messages():
    try:
        """获取预警消息数据"""
        return alert_service.get_all_alerts()
    except Exception as e:
        logger.error(f"获取预警消息数据失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取预警消息数据失败: {str(e)}")


@router.post("/alerts/process/manul")
def process_alert(request: dict):
    """人工处理告警，将指定告警更新为已处理状态"""
    try:
        alert_id = request.get("alert_id")
        if not alert_id:
            raise HTTPException(status_code=400, detail="缺少 alert_id 参数")
        success = alert_service.mark_alert_as_processed(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"告警不存在或处理失败: {alert_id}")
        return {"message": "处理成功", "alert_id": alert_id}
    except Exception as e:
        logger.error(f"处理告警失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"处理告警失败: {str(e)}")



@router.get("/chart")
def get_chart_data():
    """获取销售预测 vs 实际订单 vs 采购量（最近12个月）"""
    try:
        # 计算当前时间最近12个月
        today = datetime.today()
        # 结束月为当前月
        end_month = today.strftime("%Y-%m")
        # 开始月为11个月前
        start_date = today - relativedelta(months=11)
        start_month = start_date.strftime("%Y-%m")

        # 获取销售预测、销售订单、采购订单数据（各自已按品号+月份合并）
        forecast_list = report_service.get_sale_forecast(start_month, end_month)
        order_list = report_service.get_sale_orders(start_month, end_month)
        purchase_list = report_service.get_purchase(start_month, end_month)

        logger.info(f"销售预测: {len(forecast_list)}, 销售订单: {len(order_list)}, 采购订单: {len(purchase_list)}")

        # 按品号+年月将三种数据合并成CharVO
        merged_data = {}
        def add_to_merged(item_list, vo_field_name):
            """将数据添加到合并字典"""
            for item in item_list:
                key = (item.item_code, item.month)
                if key not in merged_data:
                    merged_data[key] = {
                        "item_code": item.item_code,
                        "month": item.month,
                        "product": "",
                        "salesForecast": 0,
                        "salesOrder": 0,
                        "purchaseQty": 0
                    }
                # 累加对应字段值
                merged_data[key][vo_field_name] += getattr(item, vo_field_name)
                # 更新产品名称（非空时）
                if item.product:
                    merged_data[key]["product"] = item.product

        # 合并三种数据
        add_to_merged(forecast_list, "salesForecast")
        add_to_merged(order_list, "salesOrder")
        add_to_merged(purchase_list, "purchaseQty")

        # 转换为CharVO对象列表并排序
        result = [
            CharVO(
                item_code=data["item_code"],
                month=data["month"],
                product=data["product"],
                salesForecast=data["salesForecast"],
                salesOrder=data["salesOrder"],
                purchaseQty=data["purchaseQty"]
            )
            for data in merged_data.values()
        ]
        result.sort(key=lambda x: (x.month, x.item_code))
        
        return result
    except Exception as e:
        logger.error(f"获取图表数据失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取图表数据失败: {str(e)}") 