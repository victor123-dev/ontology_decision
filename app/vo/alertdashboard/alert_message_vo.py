from typing import List, Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# Mock Action 数据，以 id 作为 key
MOCK_ACTIONS = {
    "ACT000001": {
        "id": "ACT000001",
        "description": "该预警为最高风险级别的关键物料供应中断。ArF光刻胶是光刻工序的核心耗材，断供将直接导致生产线停工。建议立即启动紧急采购程序，同时评估是否可临时切换至KrF光刻胶工艺（需工艺评估），并向客户华为海思提前沟通交期风险，争取2-3天缓冲期。",
        "steps": [
            { "id": "S1", "step": "立即通知采购总监和生产总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "紧急会议通知", "type": "action" },
            { "id": "S2", "step": "联系信越化学确认最新到货时间", "role": "采购员", "deadline": "2小时内", "output": "供应商确认函", "type": "action" },
            { "id": "S3", "step": "评估是否可向JSR/陶氏紧急采购", "role": "采购经理", "deadline": "4小时内", "output": "替代供应商评估报告", "type": "decision", "branches": [{ "label": "可替代", "nextStep": "S4A" }, { "label": "无法替代", "nextStep": "S4B" }] },
            { "id": "S4A", "step": "向JSR或陶氏发出紧急采购订单", "role": "采购员", "deadline": "当日", "output": "紧急采购订单", "type": "action" },
            { "id": "S4B", "step": "评估工艺切换可行性（KrF替代ArF）", "role": "工艺工程师", "deadline": "当日", "output": "工艺评估报告", "type": "action" },
            { "id": "S5", "step": "向华为海思提前沟通交期风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
            { "id": "S6", "step": "更新工单WO000023/WO000024排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
            { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" },
        ]
    },
    "ACT000002": {
        "id": "ACT000002",
        "description": "12英寸硅晶圆是核心基础物料，库存不足将影响整个生产线。需立即追加采购订单，同时优化MRP参数，提高安全库存设置。短期内可考虑向友商借货或调配其他规格晶圆。",
        "steps": [
            { "id": "S1", "step": "确认当前实际库存和在途数量", "role": "仓库管理员", "deadline": "1小时内", "output": "库存盘点报告", "type": "action" },
            { "id": "S2", "step": "向信越化学追加紧急采购1,750片", "role": "采购员", "deadline": "当日", "output": "追加采购订单", "type": "action" },
            { "id": "S3", "step": "评估是否可向其他供应商分散采购", "role": "采购经理", "deadline": "当日", "output": "多供应商采购方案", "type": "decision", "branches": [{ "label": "可分散", "nextStep": "S4A" }, { "label": "集中采购", "nextStep": "S4B" }] },
            { "id": "S4A", "step": "向Siltronic/SK Siltron发出补充订单", "role": "采购员", "deadline": "次日", "output": "补充采购订单", "type": "action" },
            { "id": "S4B", "step": "与信越化学谈判加急费用和交期", "role": "采购经理", "deadline": "次日", "output": "谈判纪要", "type": "action" },
            { "id": "S5", "step": "更新MRP安全库存参数至3,000片", "role": "供应链规划师", "deadline": "本周内", "output": "MRP参数变更单", "type": "action" },
            { "id": "END", "step": "关闭预警", "role": "预警负责人", "deadline": "处理完成后", "output": "处理报告", "type": "end" },
        ]
    },
    "ACT000003": {
        "id": "ACT000003",
        "description": "供应商OTD持续下滑是系统性风险信号。需立即启动供应商绩效改善计划（SIP），同时评估备用供应商，避免过度依赖单一供应商。短期内增加安全库存缓冲。",
        "steps": [
            { "id": "S1", "step": "发起供应商绩效改善会议邀请", "role": "采购经理", "deadline": "3个工作日内", "output": "会议邀请函", "type": "action" },
            { "id": "S2", "step": "收集默克近3月延误根因报告", "role": "供应商质量工程师", "deadline": "5个工作日内", "output": "根因分析报告", "type": "action" },
            { "id": "S3", "step": "评估备用供应商（陶氏化学/巴斯夫）", "role": "采购经理", "deadline": "本周内", "output": "备用供应商评估报告", "type": "decision", "branches": [{ "label": "有合格备选", "nextStep": "S4A" }, { "label": "无合格备选", "nextStep": "S4B" }] },
            { "id": "S4A", "step": "启动备用供应商认证流程", "role": "供应商质量工程师", "deadline": "30天内", "output": "供应商认证报告", "type": "action" },
            { "id": "S4B", "step": "与默克签订绩效改善协议(SIP)", "role": "采购总监", "deadline": "10个工作日内", "output": "SIP协议", "type": "action" },
            { "id": "S5", "step": "临时增加相关化学品安全库存至30天", "role": "供应链规划师", "deadline": "本周内", "output": "库存调整方案", "type": "action" },
            { "id": "END", "step": "建立月度OTD监控机制", "role": "采购经理", "deadline": "持续", "output": "月度供应商绩效报告", "type": "end" },
        ]
    },
    "ACT000004": {
        "id": "ACT000004",
        "description": "工单缺料直接威胁客户交期，三星电子为战略客户，违约将面临高额罚款。需紧急协调：一是加快在途物料清关，二是向三星提前沟通，三是评估是否可拆分工单先交付部分数量。",
        "steps": [
            { "id": "S1", "step": "确认PO000004最新在途状态", "role": "采购员", "deadline": "2小时内", "output": "物流跟踪报告", "type": "action" },
            { "id": "S2", "step": "联系顺丰速运加急清关", "role": "物流专员", "deadline": "当日", "output": "加急清关申请", "type": "action" },
            { "id": "S3", "step": "评估是否可拆分工单先交付1,600片", "role": "生产计划员", "deadline": "当日", "output": "工单拆分方案", "type": "decision", "branches": [{ "label": "可拆分", "nextStep": "S4A" }, { "label": "不可拆分", "nextStep": "S4B" }] },
            { "id": "S4A", "step": "向三星提交部分交货方案", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
            { "id": "S4B", "step": "向三星申请延期4天并提供补偿方案", "role": "销售总监", "deadline": "当日下班前", "output": "延期申请函", "type": "action" },
            { "id": "S5", "step": "向SK海力士追加紧急采购400片", "role": "采购员", "deadline": "次日", "output": "紧急采购订单", "type": "action" },
            { "id": "END", "step": "关闭预警，更新工单排程", "role": "生产计划员", "deadline": "处理完成后", "output": "更新后工单", "type": "end" },
        ]
    },
    "ACT000005": {
        "id": "ACT000005",
        "description": "地缘政治导致的供应中断是最高级别风险，需要公司最高管理层介入。短期需保护现有库存，中期需加速国产FPGA替代评估，长期需重构供应链战略。这将影响公司核心产品路线图。",
        "steps": [
            { "id": "S1", "step": "立即上报CEO和董事会，启动应急响应", "role": "供应链总监", "deadline": "2小时内", "output": "应急响应启动通知", "type": "action" },
            { "id": "S2", "step": "咨询法律顾问确认合规要求", "role": "法务总监", "deadline": "当日", "output": "法律合规意见书", "type": "action" },
            { "id": "S3", "step": "暂停PO000031/PO000032执行，避免违规", "role": "采购总监", "deadline": "当日", "output": "采购暂停通知", "type": "action" },
            { "id": "S4", "step": "评估国产FPGA替代方案（紫光同创/安路）", "role": "技术总监", "deadline": "5个工作日内", "output": "国产替代技术评估报告", "type": "decision", "branches": [{ "label": "可替代", "nextStep": "S5A" }, { "label": "短期不可替代", "nextStep": "S5B" }] },
            { "id": "S5A", "step": "启动国产FPGA替代项目，制定12个月路线图", "role": "技术总监", "deadline": "10个工作日内", "output": "国产替代路线图", "type": "action" },
            { "id": "S5B", "step": "通过合法渠道（第三国）评估替代采购可行性", "role": "采购总监", "deadline": "5个工作日内", "output": "合规采购方案", "type": "action" },
            { "id": "S6", "step": "向中科院计算所说明情况，协商解决方案", "role": "销售总监", "deadline": "当日下班前", "output": "客户沟通纪要", "type": "action" },
            { "id": "END", "step": "建立地缘政治风险监控机制", "role": "供应链总监", "deadline": "持续", "output": "风险监控月报", "type": "end" },
        ]
    },
    "ACT000006": {
        "id": "ACT000006",
        "description": "已联系AMAT加急处理，预计提前2天到货，工单延期2天，已获客户紫光展锐确认。",
        "steps": [
            { "id": "S1", "step": "联系AMAT确认加急可行性", "role": "采购员", "deadline": "已完成", "output": "供应商确认函", "type": "action" },
            { "id": "END", "step": "已处理完毕", "role": "采购员", "deadline": "已完成", "output": "处理报告", "type": "end" },
        ]
    },
    "ACT000007": {
        "id": "ACT000007",
        "description": "已下达补货订单，预计3天内到货，库存可维持至到货，风险可控。",
        "steps": [
            { "id": "S1", "step": "确认PO000045在途状态", "role": "采购员", "deadline": "当日", "output": "物流确认", "type": "action" },
            { "id": "END", "step": "到货后关闭预警", "role": "仓库管理员", "deadline": "3天内", "output": "入库记录", "type": "end" },
        ]
    },
    "ACT000008": {
        "id": "ACT000008",
        "description": "不可抗力导致的OTD下滑，需关注后续恢复情况，同时临时增加安全库存缓冲。",
        "steps": [
            { "id": "S1", "step": "获取TEL工厂恢复生产证明", "role": "采购员", "deadline": "3个工作日内", "output": "供应商证明文件", "type": "action" },
            { "id": "S2", "step": "临时增加相关耗材安全库存", "role": "供应链规划师", "deadline": "本周内", "output": "库存调整方案", "type": "action" },
            { "id": "END", "step": "持续监控OTD，下月评估是否关闭", "role": "采购经理", "deadline": "持续", "output": "月度监控报告", "type": "end" },
        ]
    },
}


def get_action_by_id(action_id: str) -> dict:
    """根据 action_id 获取对应的 action 数据"""
    return MOCK_ACTIONS.get(action_id, {})


class ActionVO(BaseModel):
    id: str = Field("")
    description: str = Field("")
    steps: List[dict] = Field(default_factory=list, description="行动步骤")

    @classmethod
    def from_action_id(cls, action_id: str) -> "ActionVO":
        """根据 action_id 创建 ActionVO"""
        action_data = get_action_by_id(action_id)
        return cls(
            id=action_data.get("id", ""),
            description=action_data.get("description", ""),
            steps=action_data.get("steps", [])
        )

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

