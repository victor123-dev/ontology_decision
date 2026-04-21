


from datetime import datetime
from typing import Tuple

from app.services.dashbaord.sdk_client import get_ontology_client


def _get_month_date_range(month: str) -> Tuple[str, str]:
    """
    将月份字符串转换为日期范围
    
    Args:
        month: 月份字符串，格式如"2024-01"
    
    Returns:
        (month_start, month_end) 日期范围的开始和结束，格式为"YYYY-MM-DD"
    """
    year, month_num = map(int, month.split('-'))
    month_start = datetime(year, month_num, 1)
    if month_num == 12:
        month_end = datetime(year + 1, 1, 1)
    else:
        month_end = datetime(year, month_num + 1, 1)
    
    return month_start.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d")


class KpiService:
    """KPI服务类，使用OntologyClient查询业务数据"""

    def get_purchase_on_time_rate(self, month: str) -> float:
        """
        计算及时到货率百分比

        Args:
            month: 月份字符串，格式如"2024-01"

        Returns:
            及时到货率百分比（0-100）
        """
        client = get_ontology_client()

        # 使用辅助函数计算日期范围
        month_start, month_end = _get_month_date_range(month)

        # 使用OntologyClient查询采购物流单数据
        orders = client.models.ProcurementLogistics.find(
            estimated_arrival_time__gte=month_start,
            estimated_arrival_time__lt=month_end
        )

        if not orders:
            return 0.0

        # 计算及时到货率：实际到货时间在预计到货时间之前的订单数 / 总订单数
        on_time_count = sum(1 for order in orders
                          if order.actual_arrival_time and
                          order.actual_arrival_time <= order.estimated_arrival_time)

        rate = (on_time_count / len(orders)) * 100
        return round(rate, 2)

    def get_monthly_sales_data(self, month: str) -> dict:
        """
        计算月销售数据（同时返回金额和数量）

        Args:
            month: 月份字符串，格式如"2024-01"

        Returns:
            包含销售金额和数量的字典，格式: {"amount": float, "qty": int}
        """
        client = get_ontology_client()

        # 使用辅助函数计算日期范围
        month_start, month_end = _get_month_date_range(month)

        orders = client.models.SalesOrder.find(
            document_date__gte=month_start,
            document_date__lt=month_end,
            status__ne="已取消"
        )

        if not orders:
            return {"amount": 0.0, "qty": 0}

        # 收集所有订单的 order_number
        order_numbers = [order.order_number for order in orders]

        # 使用 IN 查询一次性获取所有订单明细
        all_details = client.models.OrderDetail.find(order_number__in=order_numbers)

        # 从订单明细中同时计算总金额和总数量
        total_amount = sum(detail.amount for detail in all_details if detail.amount is not None)
        total_qty = sum(detail.quantity for detail in all_details if detail.quantity is not None)

        return {"amount": round(total_amount, 2), "qty": total_qty}

    def get_alert_count(self, month: str) -> int:
        """
        获取预警数量

        Args:
            month: 月份字符串，格式如"2024-01"

        Returns:
            预警数量
        """
        client = get_ontology_client()

        # 使用辅助函数计算日期范围
        month_start, month_end = _get_month_date_range(month)

        # 查询预警消息
        alerts = client.models.AlertMessage.find(
            create_time__gte=month_start,
            create_time__lt=month_end,
            status__ne="已处理"
        )

        return len(alerts)


    def get_alert_exec_count(self, month: str) -> int:
        """
        获取预警执行数量

        Args:
            month: 月份字符串，格式如"2024-01"

        Returns:
            预警执行数量
        """
        client = get_ontology_client()

        # 使用辅助函数计算日期范围
        month_start, month_end = _get_month_date_range(month)

        # 查询预警消息
        alerts = client.models.AlertMessage.find(
            create_time__gte=month_start,
            create_time__lt=month_end,
            status__eq="已处理",
            handle_type__eq=1
        )

        return len(alerts)
