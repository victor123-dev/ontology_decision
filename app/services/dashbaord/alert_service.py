from typing import List

from app.services.dashbaord.sdk_client import get_ontology_client
from app.vo.alertdashboard.alert_message_vo import AlertMeassageVO

# 排序优先级定义：值越小优先级越高
STATUS_ORDER = {"未处理": 0, "处理中": 1, "已处理": 2}
RISK_LEVEL_ORDER = {"高风险": 0, "最高风险": 0, "中风险": 1, "低风险": 2}


class AlertService:
    """告警服务类，使用OntologyClient查询告警消息数据"""

    def get_all_alerts(self) -> List[AlertMeassageVO]:
        """获取所有告警消息，按状态(未处理>处理中>已处理)和风险等级(高>中>低)排序"""
        client = get_ontology_client()
        # 查找status不为空且不为None的告警消息
        alerts = client.models.AlertMessage.find(status__ne="")

        alert_vos = [
            AlertMeassageVO(
                id=alert.message_id or "",
                title=alert.message_title or "",
                content=alert.message_content or "",
                status=alert.status or "",
                riskLevel=alert.risk_level or "",
                poId=alert.related_po or "",
                supplier=alert.supplier or "",
                soId=alert.related_so or "",
                customer=alert.related_customer or "",
                ruleCode=alert.rule_code or "",
                createdAt=alert.create_time or "",
                rootCause=""
            )
            for alert in alerts
        ]

        alert_vos.sort(key=lambda a: a.createdAt, reverse=True)  # 按创建时间倒序

        return alert_vos

    def mark_alert_as_processed(self, alert_id: str) -> bool:
        """将指定告警更新为已处理状态

        Args:
            alert_id: 告警消息ID

        Returns:
            bool: 更新是否成功
        """
        client = get_ontology_client()
        # 查找指定ID的告警
        alert = client.models.AlertMessage.get(alert_id)
        if not alert:
            return False

        # 更新状态为"已处理"
        return alert.update(status="已处理")
