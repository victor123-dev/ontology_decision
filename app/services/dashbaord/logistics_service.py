from typing import List

from app.services.dashbaord.sdk_client import get_ontology_client
from app.vo.alertdashboard.logistics_dynamic_vo import LogisticsDynamicVO


class LogistisService:
    """物流服务类，使用OntologyClient查询物流动态数据"""

    def get_all_logistics(self) -> List[LogisticsDynamicVO]:
        """
        查询所有物流动态，按时间倒序

        Returns:
            物流动态列表，每个物流动态包含以下字段：
            - id: 物流单号
            - time: 时间（格式：HH:mm）
            - carrier: 承运商
            - from: 发货地
            - to: 收货地
            - material: 物料名称
            - status: 状态（在途、已到达、清关中、延误等）
            - po: 采购订单号
        """
        client = get_ontology_client()

        logistics = client.models.LogisticsDynamic.find()

        logistics_sorted = sorted(logistics, key=lambda x: x.time, reverse=True)

        # 将查询结果转换为LogisticsDynamicVO列表
        return [
            LogisticsDynamicVO(
                id=log.logistics_id,
                time=log.time,
                carrier=log.carrier,
                from_=log.shipper,
                to=log.consignee,
                material=log.material_name,
                status=log.logistics_status,
                po=log.related_po
            )
            for log in logistics_sorted
        ]
