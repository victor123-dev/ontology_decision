from typing import List, Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# Mock Action 数据，以 id 作为 key
MOCK_ACTIONS = {
        "ACT000001": {
            "id": "ACT000001",
            "description": "1.立即触发紧急采购流程，向供应商SUP004发起加急订单，数量289件；2.同步启用替代物料或调整生产计划；3.向客户通报潜在风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购总监和生产总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "紧急会议通知", "type": "action" },
                { "id": "S2", "step": "向供应商SUP004发起加急订单", "role": "采购员", "deadline": "2小时内", "output": "紧急采购订单", "type": "action" },
                { "id": "S3", "step": "评估是否可启用替代物料", "role": "采购经理", "deadline": "4小时内", "output": "替代方案评估报告", "type": "decision", "branches": [{ "label": "可替代", "nextStep": "S4A" }, { "label": "无法替代", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "执行替代物料采购/切换", "role": "采购员/工艺工程师", "deadline": "当日", "output": "替代物料确认单", "type": "action" },
                { "id": "S4B", "step": "评估调整生产计划可行性", "role": "生产计划员", "deadline": "当日", "output": "生产计划调整方案", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000002": {
            "id": "ACT000002",
            "description": "1.立即触发紧急采购流程，向供应商SUP005发起加急订单，数量235件；2.同步启用替代物料或调整生产计划；3.向客户通报潜在风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购总监和生产总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "紧急会议通知", "type": "action" },
                { "id": "S2", "step": "向供应商SUP005发起加急订单", "role": "采购员", "deadline": "2小时内", "output": "紧急采购订单", "type": "action" },
                { "id": "S3", "step": "评估是否可启用替代物料", "role": "采购经理", "deadline": "4小时内", "output": "替代方案评估报告", "type": "decision", "branches": [{ "label": "可替代", "nextStep": "S4A" }, { "label": "无法替代", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "执行替代物料采购/切换", "role": "采购员/工艺工程师", "deadline": "当日", "output": "替代物料确认单", "type": "action" },
                { "id": "S4B", "step": "评估调整生产计划可行性", "role": "生产计划员", "deadline": "当日", "output": "生产计划调整方案", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000003": {
            "id": "ACT000003",
            "description": "1.立即触发紧急采购流程，向供应商SUP002发起加急订单，数量452件；2.同步启用替代物料或调整生产计划；3.向客户通报潜在风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购总监和生产总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "紧急会议通知", "type": "action" },
                { "id": "S2", "step": "向供应商SUP002发起加急订单", "role": "采购员", "deadline": "2小时内", "output": "紧急采购订单", "type": "action" },
                { "id": "S3", "step": "评估是否可启用替代物料", "role": "采购经理", "deadline": "4小时内", "output": "替代方案评估报告", "type": "decision", "branches": [{ "label": "可替代", "nextStep": "S4A" }, { "label": "无法替代", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "执行替代物料采购/切换", "role": "采购员/工艺工程师", "deadline": "当日", "output": "替代物料确认单", "type": "action" },
                { "id": "S4B", "step": "评估调整生产计划可行性", "role": "生产计划员", "deadline": "当日", "output": "生产计划调整方案", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000004": {
            "id": "ACT000004",
            "description": "1.立即触发紧急采购流程，向供应商SUP004发起加急订单，数量358件；2.同步启用替代物料或调整生产计划；3.向客户通报潜在风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购总监和生产总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "紧急会议通知", "type": "action" },
                { "id": "S2", "step": "向供应商SUP004发起加急订单", "role": "采购员", "deadline": "2小时内", "output": "紧急采购订单", "type": "action" },
                { "id": "S3", "step": "评估是否可启用替代物料", "role": "采购经理", "deadline": "4小时内", "output": "替代方案评估报告", "type": "decision", "branches": [{ "label": "可替代", "nextStep": "S4A" }, { "label": "无法替代", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "执行替代物料采购/切换", "role": "采购员/工艺工程师", "deadline": "当日", "output": "替代物料确认单", "type": "action" },
                { "id": "S4B", "step": "评估调整生产计划可行性", "role": "生产计划员", "deadline": "当日", "output": "生产计划调整方案", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000005": {
            "id": "ACT000005",
            "description": "1.采购部立即联系供应商SUP004确认最新交货计划，要求提供书面承诺交期；2.评估是否启用替代供应商或调整生产计划；3.向客户通报潜在风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "联系供应商SUP004确认交货计划", "role": "采购员", "deadline": "2小时内", "output": "供应商确认函", "type": "action" },
                { "id": "S3", "step": "评估是否启用替代供应商", "role": "采购经理", "deadline": "4小时内", "output": "替代供应商评估报告", "type": "decision", "branches": [{ "label": "可启用", "nextStep": "S4A" }, { "label": "无法启用", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "向替代供应商发出采购订单", "role": "采购员", "deadline": "当日", "output": "替代采购订单", "type": "action" },
                { "id": "S4B", "step": "评估调整生产计划可行性", "role": "生产计划员", "deadline": "当日", "output": "生产计划调整方案", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000006": {
            "id": "ACT000006",
            "description": "1.采购部立即联系供应商SUP005确认最新交货计划，要求提供书面承诺交期；2.评估是否启用替代供应商或调整生产计划；3.向客户通报潜在风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "联系供应商SUP005确认交货计划", "role": "采购员", "deadline": "2小时内", "output": "供应商确认函", "type": "action" },
                { "id": "S3", "step": "评估是否启用替代供应商", "role": "采购经理", "deadline": "4小时内", "output": "替代供应商评估报告", "type": "decision", "branches": [{ "label": "可启用", "nextStep": "S4A" }, { "label": "无法启用", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "向替代供应商发出采购订单", "role": "采购员", "deadline": "当日", "output": "替代采购订单", "type": "action" },
                { "id": "S4B", "step": "评估调整生产计划可行性", "role": "生产计划员", "deadline": "当日", "output": "生产计划调整方案", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000007": {
            "id": "ACT000007",
            "description": "1.采购部立即联系供应商SUP002确认最新交货计划，要求提供书面承诺交期；2.评估是否启用替代供应商或调整生产计划；3.向客户通报潜在风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "联系供应商SUP002确认交货计划", "role": "采购员", "deadline": "2小时内", "output": "供应商确认函", "type": "action" },
                { "id": "S3", "step": "评估是否启用替代供应商", "role": "采购经理", "deadline": "4小时内", "output": "替代供应商评估报告", "type": "decision", "branches": [{ "label": "可启用", "nextStep": "S4A" }, { "label": "无法启用", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "向替代供应商发出采购订单", "role": "采购员", "deadline": "当日", "output": "替代采购订单", "type": "action" },
                { "id": "S4B", "step": "评估调整生产计划可行性", "role": "生产计划员", "deadline": "当日", "output": "生产计划调整方案", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000008": {
            "id": "ACT000008",
            "description": "1.运行MRP重算，更新净需求数据，确认缺口数量和时间窗口；2.根据缺口优先级发起采购申请，优先保障高优先级工单；3.向客户通报潜在交期风险。",
            "steps": [
                { "id": "S1", "step": "立即通知计划部门", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "运行MRP重算，更新净需求数据", "role": "计划员", "deadline": "1小时内", "output": "MRP运算报告", "type": "action" },
                { "id": "S3", "step": "根据缺口优先级发起采购申请", "role": "采购员", "deadline": "当日", "output": "采购申请单", "type": "action" },
                { "id": "S4", "step": "向客户通报潜在交期风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S5", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000009": {
            "id": "ACT000009",
            "description": "1.运行MRP重算，更新净需求数据，确认缺口数量和时间窗口；2.根据缺口优先级发起采购申请，优先保障高优先级工单；3.向客户通报潜在交期风险。",
            "steps": [
                { "id": "S1", "step": "立即通知计划部门", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "运行MRP重算，更新净需求数据", "role": "计划员", "deadline": "1小时内", "output": "MRP运算报告", "type": "action" },
                { "id": "S3", "step": "根据缺口优先级发起采购申请", "role": "采购员", "deadline": "当日", "output": "采购申请单", "type": "action" },
                { "id": "S4", "step": "向客户通报潜在交期风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S5", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000010": {
            "id": "ACT000010",
            "description": "1.启动替代供应商开发计划，目标在6个月内完成至少1家新供应商认证；2.与现有供应商SUP004谈判价格保护协议，锁定未来6个月价格；3.评估是否可增加现有供应商采购份额。",
            "steps": [
                { "id": "S1", "step": "立即通知采购总监", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "启动替代供应商开发计划", "role": "采购经理", "deadline": "当日", "output": "供应商开发计划书", "type": "action" },
                { "id": "S3", "step": "与现有供应商SUP004谈判价格保护", "role": "采购经理", "deadline": "3日内", "output": "谈判纪要", "type": "action" },
                { "id": "S4", "step": "评估增加现有供应商采购份额可行性", "role": "采购分析师", "deadline": "1周内", "output": "采购份额分析报告", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000011": {
            "id": "ACT000011",
            "description": "1.立即核实缺料物料的在途采购订单状态和预计到货时间；2.评估是否可从其他工单或仓库调拨缺料物料；3.向客户通报潜在交期风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购和仓储部门", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "核实缺料物料的在途订单状态", "role": "采购员", "deadline": "2小时内", "output": "在途订单状态报告", "type": "action" },
                { "id": "S3", "step": "评估是否可从其他工单调拨", "role": "仓储主管", "deadline": "4小时内", "output": "调拨可行性评估报告", "type": "decision", "branches": [{ "label": "可调拨", "nextStep": "S4A" }, { "label": "无法调拨", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "执行物料调拨", "role": "仓储管理员", "deadline": "当日", "output": "物料调拨单", "type": "action" },
                { "id": "S4B", "step": "启动紧急采购", "role": "采购员", "deadline": "当日", "output": "紧急采购订单", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在交期风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000012": {
            "id": "ACT000012",
            "description": "1.立即核实缺料物料的在途采购订单状态和预计到货时间；2.评估是否可从其他工单或仓库调拨缺料物料；3.向客户通报潜在交期风险。",
            "steps": [
                { "id": "S1", "step": "立即通知采购和仓储部门", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "核实缺料物料的在途订单状态", "role": "采购员", "deadline": "2小时内", "output": "在途订单状态报告", "type": "action" },
                { "id": "S3", "step": "评估是否可从其他工单调拨", "role": "仓储主管", "deadline": "4小时内", "output": "调拨可行性评估报告", "type": "decision", "branches": [{ "label": "可调拨", "nextStep": "S4A" }, { "label": "无法调拨", "nextStep": "S4B" }] },
                { "id": "S4A", "step": "执行物料调拨", "role": "仓储管理员", "deadline": "当日", "output": "物料调拨单", "type": "action" },
                { "id": "S4B", "step": "启动紧急采购", "role": "采购员", "deadline": "当日", "output": "紧急采购订单", "type": "action" },
                { "id": "S5", "step": "向客户通报潜在交期风险", "role": "销售经理", "deadline": "当日下班前", "output": "客户沟通记录", "type": "action" },
                { "id": "S6", "step": "更新受影响工单排程", "role": "生产计划员", "deadline": "次日", "output": "更新后的生产计划", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        },
        "ACT000013": {
            "id": "ACT000013",
            "description": "1.立即对工单WO000118的BOM执行替代料切换，使用RM-WF-004-B01(6英寸)替代原物料；2.更新工艺参数和检验标准；3.通知生产和质量部门执行变更。",
            "steps": [
                { "id": "S1", "step": "立即通知工艺和质量部门", "role": "系统自动/预警负责人", "deadline": "30分钟内", "output": "预警通知", "type": "action" },
                { "id": "S2", "step": "对工单WO000118的BOM执行替代料切换", "role": "工艺工程师", "deadline": "当日", "output": "BOM变更单", "type": "action" },
                { "id": "S3", "step": "更新工艺参数和检验标准", "role": "工艺工程师/质量工程师", "deadline": "当日", "output": "工艺文件更新记录", "type": "action" },
                { "id": "S4", "step": "通知生产和质量部门执行变更", "role": "生产主管/质量主管", "deadline": "次日", "output": "变更执行确认单", "type": "action" },
                { "id": "END", "step": "关闭预警，记录处理结果", "role": "预警负责人", "deadline": "处理完成后", "output": "预警处理报告", "type": "end" }
            ]
        }
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

