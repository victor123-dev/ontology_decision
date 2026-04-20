from typing import List, Any, Optional

from pydantic import BaseModel, ConfigDict, Field

class ActionVO(BaseModel):
    id: str = Field("")
    description: str = Field("")
    steps: List[dict] = Field(default_factory=list, description="行动步骤")

class AlertMeassageVO(BaseModel):
    """告警消息VO"""

    id: str = Field(description="告警消息ID", example="MSG000001")
    title: str = Field(description="告警标题", example="【供应中断预警】ArF光刻胶单一来源供应商交期异常")
    content: str = Field(description="告警内容", example="供应商日本信越化学工业(SUP0001)的ArF光刻胶(IC-PHR-001)预计到货日2025-04-15，已超出需求日期2025-04-08，延误7天。该物料为关键单一来源，当前库存覆盖仅3天，低于安全库存阈值14天。影响工单WO000023、WO000024，涉及销售订单SO000015(华为海思)。")
    status: str = Field(description="处理状态", example="未处理")
    riskLevel: str = Field(description="风险等级", example="最高风险")
    poId: str = Field(description="采购订单ID", example="PO000001")
    supplier: str = Field(description="供应商名称", example="日本信越化学工业")
    soId: str = Field(description="销售订单ID", example="SO000015")
    customer: str = Field(description="客户名称", example="华为海思半导体")
    ruleCode: str = Field(description="规则代码", example="SCRULE-001")
    createdAt: str = Field(description="创建时间", example="2025-04-09 08:30:00")
    rootCause: str = Field(description="根因分析", example="根因分析（5Why法）")
    action: ActionVO = Field(default_factory=ActionVO, description="行动信息")

    model_config = ConfigDict(from_attributes=True)

