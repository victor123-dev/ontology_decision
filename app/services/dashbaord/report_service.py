from collections import defaultdict
from typing import List
from datetime import datetime

from app.services.dashbaord.sdk_client import get_ontology_client
from app.vo.alertdashboard.char_vo import CharVO
from app.vo.alertdashboard.forecast_vo import ForecastDataVO, ForecastResponseVO
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReportService:
    """报表服务类，提供销售预测等报表数据查询功能"""

    def get_sale_forecast_by_year(self, year: str) -> List[CharVO]:
        """
        按年查询销售预测数据，按月份和品号分组合并

        Args:
            year: 年份字符串，格式如"2025"

        Returns:
            CharVO 对象列表，包含合并后的预测数据
        """
        client = get_ontology_client()

        # 计算年的开始和结束日期
        year_start = f"{year}-01-01"
        year_end = f"{int(year) + 1}-01-01"

        # 查询该年份内的销售预测数据
        forecasts = client.models.SalesForecast.find(
            demand_date__gte=year_start,
            demand_date__lt=year_end
        )

        if not forecasts:
            return []

        # 按月份和item_code分组合并数据
        grouped_data = defaultdict(lambda: {
            'forecast': 0,
            'order': 0,
            'purchase': 0,
            'product': ''
        })

        for forecast in forecasts:
            # 提取月份（YYYY-MM格式）
            demand_date_str = str(forecast.demand_date) if forecast.demand_date else ''
            month = demand_date_str[:7] if demand_date_str else '1970-01'
            item_code = forecast.item_code or 'UNKNOWN'

            # 累加数量（SalesForecast的quantity赋值给CharVO.forecast）
            grouped_data[(month, item_code)]['forecast'] += forecast.quantity or 0
            
            # 保存产品名称（使用item_name）
            if forecast.item_name:
                grouped_data[(month, item_code)]['product'] = forecast.item_name

        # 构建CharVO对象列表
        result = []
        for (month, item_code), data in grouped_data.items():
            char_vo = CharVO(
                item_code=item_code,
                month=month,
                product=data['product'] or f"{item_code}产品",
                salesForecast=int(data['forecast']),
                salesOrder=int(data['order']),
                purchaseQty=int(data['purchase'])
            )
            result.append(char_vo)

        # 按月份排序
        result.sort(key=lambda x: (x.month, x.item_code))

        return result


    def get_purchase_by_year(self, year: str) -> List[CharVO]:
        """
        按年查询采购订单数据，按月份和品号分组合并

        Args:
            year: 年份字符串，格式如"2025"

        Returns:
            CharVO 对象列表，包含合并后的采购数据
        """
        client = get_ontology_client()

        # 计算年的开始和结束日期
        year_start = f"{year}-01-01"
        year_end = f"{int(year) + 1}-01-01"

        # 查询该年份内的采购订单数据
        purchase_orders = client.models.PurchaseOrder.find(
            document_date__gte=year_start,
            document_date__lt=year_end,
            status__ne="已取消"
        )

        logger.info(f"查询到 {len(purchase_orders) if purchase_orders else 0} 条采购订单数据")

        if not purchase_orders:
            return []

        # 收集所有采购订单号
        purchase_order_numbers = [order.purchase_order_number for order in purchase_orders]

        # 使用 IN 查询一次性获取所有采购订单明细
        all_details = client.models.PurchaseOrderDetail.find(purchase_order_number__in=purchase_order_numbers)

        logger.info(f"查询到 {len(all_details)} 条采购订单明细数据")

        # 建立订单号到日期的映射
        order_date_map = {order.purchase_order_number: order.document_date for order in purchase_orders}

        # 按月份和item_code分组合并数据
        grouped_data = defaultdict(lambda: {
            'forecast': 0,
            'order': 0,
            'purchase': 0,
            'product': ''
        })

        for detail in all_details:
            purchase_order_number = detail.purchase_order_number

            # 从映射中获取订单日期
            document_date_str = str(order_date_map.get(purchase_order_number, '')) if order_date_map.get(purchase_order_number) else ''
            month = document_date_str[:7] if document_date_str else '1970-01'

            item_code = detail.item_code or 'UNKNOWN'

            # 累加采购数量
            qty = detail.quantity or 0
            grouped_data[(month, item_code)]['purchase'] += qty
            logger.debug(f"  明细: {item_code}, 数量: {qty}, 月份: {month}")

            # 保存产品名称
            if detail.item_name:
                grouped_data[(month, item_code)]['product'] = detail.item_name

        # 构建CharVO对象列表
        result = []
        for (month, item_code), data in grouped_data.items():
            char_vo = CharVO(
                item_code=item_code,
                month=month,
                product=data['product'],
                salesForecast=int(data['forecast']),
                salesOrder=int(data['order']),
                purchaseQty=int(data['purchase'])
            )
            result.append(char_vo)

        # 按月份排序
        result.sort(key=lambda x: (x.month, x.item_code))

        return result


    def get_sale_orders_by_year(self, year: str) -> List[CharVO]:
        """
        按年查询销售订单数据，按月份和品号分组合并

        Args:
            year: 年份字符串，格式如"2025"

        Returns:
            CharVO 对象列表，包含合并后的订单数据
        """
        client = get_ontology_client()

        # 计算年的开始和结束日期
        year_start = f"{year}-01-01"
        year_end = f"{int(year) + 1}-01-01"

        # 查询该年份内的销售订单数据
        sales_orders = client.models.SalesOrder.find(
            document_date__gte=year_start,
            document_date__lt=year_end,
            status__ne="已取消"
        )

        logger.info(f"查询到 {len(sales_orders) if sales_orders else 0} 条销售订单数据")

        if not sales_orders:
            return []

        # 收集所有销售订单号
        order_numbers = [order.order_number for order in sales_orders]

        # 使用 IN 查询一次性获取所有订单明细
        all_details = client.models.OrderDetail.find(order_number__in=order_numbers)

        logger.info(f"查询到 {len(all_details)} 条订单明细数据")

        # 建立订单号到日期的映射
        order_date_map = {order.order_number: order.document_date for order in sales_orders}

        # 按月份和item_code分组合并数据
        grouped_data = defaultdict(lambda: {
            'forecast': 0,
            'order': 0,
            'purchase': 0,
            'product': ''
        })

        for detail in all_details:
            order_number = detail.order_number

            # 从映射中获取订单日期
            document_date_str = str(order_date_map.get(order_number, '')) if order_date_map.get(order_number) else ''
            month = document_date_str[:7] if document_date_str else '1970-01'

            item_code = detail.item_code or 'UNKNOWN'

            # 累加订单数量
            qty = detail.quantity or 0
            grouped_data[(month, item_code)]['order'] += qty
            logger.debug(f"  明细: {item_code}, 数量: {qty}, 月份: {month}")

            # 保存产品名称
            if detail.item_name:
                grouped_data[(month, item_code)]['product'] = detail.item_name

        # 构建CharVO对象列表
        result = []
        for (month, item_code), data in grouped_data.items():
            char_vo = CharVO(
                item_code=item_code,
                month=month,
                product=data['product'],
                salesForecast=int(data['forecast']),
                salesOrder=int(data['order']),
                purchaseQty=int(data['purchase'])
            )
            result.append(char_vo)

        # 按月份排序
        result.sort(key=lambda x: (x.month, x.item_code))

        return result

    def get_forecast_data(self, start_month: str, end_month: str) -> ForecastResponseVO:
        """
        查询指定月份范围内的需求预测数据，按月份和品号分组合并

        Args:
            start_month: 开始月份，格式如"2026-05"
            end_month: 结束月份，格式如"2026-10"

        Returns:
            ForecastResponseVO 对象，包含月份列表和预测数据
        """
        client = get_ontology_client()

        # 生成月份列表
        months = []
        current_month = start_month
        while current_month < end_month:
            months.append(current_month)
            year, month = map(int, current_month.split('-'))
            month += 1
            if month > 12:
                month = 1
                year += 1
            current_month = f"{year:04d}-{month:02d}"

        # 查询指定月份范围内的需求预测数据
        forecasts = client.models.DemandForecast.find(
            forecast_month__gte=start_month,
            forecast_month__lte=end_month
        )

        logger.info(f"查询到 {len(forecasts) if forecasts else 0} 条需求预测数据 (范围: {start_month} - {end_month})")

        # 按product_id分组，构建months字典
        grouped_data = defaultdict(lambda: {
            'productName': '',
            'months': {}
        })

        for forecast in forecasts:
            # 提取月份（YYYY-MM格式）
            forecast_month_str = str(forecast.forecast_month) if forecast.forecast_month else ''
            month = forecast_month_str[:7] if forecast_month_str else '1970-01'
            product_id = forecast.product_id or 'UNKNOWN'

            # 累加需求数量（DemandForecast的demand_quantity是string类型）
            demand_qty_str = forecast.demand_quantity or '0'
            try:
                demand_qty = int(float(demand_qty_str))
            except (ValueError, TypeError):
                demand_qty = 0

            # 按产品累加每个月的数量
            grouped_data[product_id]['months'][month] = grouped_data[product_id]['months'].get(month, 0) + demand_qty
            logger.debug(f"需求预测: {product_id}, 数量: {demand_qty}, 月份: {month}")

            # 保存产品名称（使用product_name）
            if forecast.product_name:
                grouped_data[product_id]['productName'] = forecast.product_name

        # 构建ForecastDataVO对象列表
        result_data = []
        for product_id, data in grouped_data.items():
            forecast_vo = ForecastDataVO(
                productCode=product_id,
                productName=data['productName'] or f"{product_id}产品",
                months=data['months']
            )
            result_data.append(forecast_vo)

        # 按产品编码排序
        result_data.sort(key=lambda x: x.productCode)

        return ForecastResponseVO(
            months=months,
            data=result_data
        )
