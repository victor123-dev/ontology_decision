"""
半导体供应链本体模型导入脚本
基于《半导体供应链完整本体建模方案v2.1修订版》生成

功能：
1. 清空现有数据（可选，默认开启）
2. 导入32个BusinessModel（对象）
3. 导入所有BusinessModelField（字段）
4. 导入73个BusinessModelLink（关系）
   - 主数据域关系：18个（R1-R8系列）
   - 供应链域关系：4个（R8.1-R8.4系列）
   - 客户域关系：5个（R8.5-R8.9系列）
   - 计划域关系：6个（R9-R10系列）
   - 执行域关系：8个（R11-R13系列）
   - 库存域关系：5个（R14-R16系列）
   - 质量域关系：6个（R17系列）
   - 采购与供应商域关系：2个（R17系列）
   - 库存事务与调拨域关系：5个（R17系列）
   - 工作日历与排程域关系：6个（R17系列）
   - 监控域关系：2个（R30-R31系列）

特点：
- 默认先清空再导入，确保干净的全量导入
- 使用 --no-clear 参数可切换为幂等模式（跳过已存在的）
- 包含所有业务关系（不仅限于外键）
- 包含中间表的1:N关系（如BOM、能力矩阵等）

使用方法：
# 默认模式：先清空再导入
python scripts/import_ontology_models.py --api-url http://localhost:8080

# 幂等模式：跳过已存在的记录
python scripts/import_ontology_models.py --api-url http://localhost:8080 --no-clear
"""

import requests
import json
import argparse
import sys
from typing import List, Dict, Any

# ==================== 配置区域 ====================

# 数据源ID（需要根据你的实际情况修改）
DATA_SOURCE_ID = "1"

# ==================== 29个本体对象定义 ====================

BUSINESS_MODELS = [
    # 主数据域 (9个)
    {
        "id": "product",
        "api_name": "Product",
        "name": "产品",
        "description": "半导体封装测试产品定义",
        "primary_key_id": "product_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "material",
        "api_name": "Material",
        "name": "物料",
        "description": "生产所需的原材料和辅料",
        "primary_key_id": "material_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "work_center",
        "api_name": "WorkCenter",
        "name": "工作中心",
        "description": "产能资源池",
        "primary_key_id": "work_center_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "machine",
        "api_name": "Machine",
        "name": "机台设备",
        "description": "具体生产设备",
        "primary_key_id": "machine_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "process_route",
        "api_name": "ProcessRoute",
        "name": "工艺路线",
        "description": "产品的标准生产工艺（每个产品独立路线）",
        "primary_key_id": "route_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "route_step",
        "api_name": "RouteStep",
        "name": "工序",
        "description": "工艺路线的具体步骤，包含时间、良率、设备要求",
        "primary_key_id": "step_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "machine_capability",
        "api_name": "MachineCapability",
        "name": "机台能力矩阵",
        "description": "机台-产品能力矩阵，决定哪些机台能生产哪些产品",
        "primary_key_id": "capability_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "setup_matrix",
        "api_name": "SetupMatrix",
        "name": "换线矩阵",
        "description": "产品间切换的换线时间定义",
        "primary_key_id": "matrix_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "shift_pattern",
        "api_name": "ShiftPattern",
        "name": "班次模式",
        "description": "班次定义（日班/夜班），包含工作时间、效率因子",
        "primary_key_id": "shift_id",
        "data_source_id": DATA_SOURCE_ID
    },
    
    # 供应链域 (4个)
    {
        "id": "supplier",
        "api_name": "Supplier",
        "name": "供应商",
        "description": "物料供应商",
        "primary_key_id": "supplier_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "supplier_material",
        "api_name": "SupplierMaterial",
        "name": "供应商物料清单",
        "description": "供应商能供应的物料及其价格、交期、最小订购量",
        "primary_key_id": "sm_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "material_substitute",
        "api_name": "MaterialSubstitute",
        "name": "物料可用替代料",
        "description": "物料缺料时可用的替代料关系",
        "primary_key_id": "ms_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "bom",
        "api_name": "Bom",
        "name": "物料清单",
        "description": "产品由哪些物料组成及用量",
        "primary_key_id": "bom_id",
        "data_source_id": DATA_SOURCE_ID
    },
    # 客户域 (3个)
    {
        "id": "customer",
        "api_name": "Customer",
        "name": "客户",
        "description": "客户主数据",
        "primary_key_id": "customer_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "customer_product",
        "api_name": "CustomerProduct",
        "name": "客户可购产品清单",
        "description": "客户可购买的产品清单及特定价格、交期、质量等级",
        "primary_key_id": "id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "customer_order",
        "api_name": "CustomerOrder",
        "name": "客户订单",
        "description": "客户采购订单，包含产品、数量、交期、优先级",
        "primary_key_id": "order_id",
        "data_source_id": DATA_SOURCE_ID
    },
    # 计划域 (6个)
    {
        "id": "work_order",
        "api_name": "WorkOrder",
        "name": "工单",
        "description": "由客户订单生成的生产计划，仿真核心驱动对象",
        "primary_key_id": "work_order_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "work_order_operation",
        "api_name": "WorkOrderOperation",
        "name": "工单工序",
        "description": "工单的工序级计划，排程算法的直接操作对象",
        "primary_key_id": "wo_op_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "work_order_material",
        "api_name": "WorkOrderMaterial",
        "name": "工单物料需求",
        "description": "工单工序的物料需求明细，MRP运算的直接对象",
        "primary_key_id": "wom_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "purchase_order",
        "api_name": "PurchaseOrder",
        "name": "采购订单",
        "description": "向供应商下达的采购订单",
        "primary_key_id": "po_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "purchase_order_line",
        "api_name": "PurchaseOrderLine",
        "name": "采购订单行",
        "description": "采购订单的物料明细行（一个PO可包含多种物料）",
        "primary_key_id": "line_id",
        "data_source_id": DATA_SOURCE_ID
    },
    
    # 执行域 (4个)
    {
        "id": "wip_lot",
        "api_name": "WipLot",
        "name": "在制品批次",
        "description": "Lot批量生产追踪（25片/批），OSAT行业标准",
        "primary_key_id": "lot_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "production_task",
        "api_name": "ProductionTask",
        "name": "生产任务",
        "description": "机台级别的任务执行记录",
        "primary_key_id": "task_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "material_transfer",
        "api_name": "MaterialTransfer",
        "name": "物料调拨",
        "description": "工单间的物料挪用记录，缺料时的应急策略",
        "primary_key_id": "transfer_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "work_calendar",
        "api_name": "WorkCalendar",
        "name": "工作日历",
        "description": "每个工作中心每天的班次安排（日班/夜班/休息）",
        "primary_key_id": "calendar_id",
        "data_source_id": DATA_SOURCE_ID
    },
    
    # 库存域 (3个)
    {
        "id": "inventory",
        "api_name": "Inventory",
        "name": "原材料库存",
        "description": "物料的实时库存状态",
        "primary_key_id": "inventory_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "inventory_transaction",
        "api_name": "InventoryTransaction",
        "name": "库存事务",
        "description": "所有库存变动的业务事件记录（消耗、入库、调拨、预留）",
        "primary_key_id": "transaction_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "finished_goods_inventory",
        "api_name": "FinishedGoodsInventory",
        "name": "成品库存",
        "description": "完工产品的库存（区别于原材料）",
        "primary_key_id": "fg_inv_id",
        "data_source_id": DATA_SOURCE_ID
    },
    
    # 质量域 (1个)
    {
        "id": "quality_inspection",
        "api_name": "QualityInspection",
        "name": "质量检验记录",
        "description": "IQC/IPQC/FQC等各类检验记录",
        "primary_key_id": "inspection_id",
        "data_source_id": DATA_SOURCE_ID
    },
    
    # 监控域 (4个)
    {
        "id": "schedule",
        "api_name": "Schedule",
        "name": "排程汇总",
        "description": "每日产能负荷统计快照，支持产能分析和瓶颈识别",
        "primary_key_id": "schedule_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "machine_status_log",
        "api_name": "MachineStatusLog",
        "name": "机台状态日志",
        "description": "机台状态变迁记录（运行、停机、维护、故障），用于OEE分析",
        "primary_key_id": "log_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "external_supply_chain_risk",
        "api_name": "ExternalSupplyChainRisk",
        "name": "外部供应链风险",
        "description": "通过舆情监控获取的外部风险事件。supplier_id字段记录主要受影响方（1个），如需记录多个关联供应商及其影响程度，使用SupplierRiskAssociation对象",
        "primary_key_id": "risk_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "supplier_risk_association",
        "api_name": "SupplierRiskAssociation",
        "name": "供应商风险关联",
        "description": "供应商与风险事件的多对多关联表，记录风险波及影响链。支持direct/indirect/potential三种关联类型，独立记录每个供应商的影响程度",
        "primary_key_id": "id",
        "data_source_id": DATA_SOURCE_ID
    },
]

# 所有对象的字段定义
ALL_FIELDS = {
    "product": [
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "product_name", "data_type": "string", "name": "产品名称", "required": True,  "description": "产品名称"},
        {"field_id": "product_type", "data_type": "string", "name": "产品类型", "required": True,  "description": "产品类型（枚举：成品）", "is_enum": True, "enum_values": ["成品"]},
        {"field_id": "standard_cycle_time", "data_type": "float", "name": "标准周期(小时)", "required": False,  "description": "标准生产周期（单位：小时）"},
        {"field_id": "routing_steps", "data_type": "integer", "name": "工序数", "required": False,  "description": "工艺路线工序数量"},
        {"field_id": "setup_group", "data_type": "string", "name": "换线组", "required": False,  "description": "换线组（用于排程优化，同组工单可合并）"},
        {"field_id": "unit_of_measure", "data_type": "string", "name": "计量单位", "required": False,  "description": "计量单位（如：PCS/片/千克/米）"},
        {"field_id": "is_active", "data_type": "boolean", "name": "是否激活", "required": False,  "description": "是否启用（True=启用，False=停用）"},
        {"field_id": "created_at", "data_type": "datetime", "name": "创建时间", "required": False,  "description": "创建时间（系统自动生成）"},
    ],
    "material": [
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "material_name", "data_type": "string", "name": "物料名称", "required": True,  "description": "物料名称"},
        {"field_id": "material_type", "data_type": "string", "name": "物料类型", "required": True,  "description": "物料类型（枚举：原材料/辅料）", "is_enum": True, "enum_values": ["原材料", "辅料"]},
        {"field_id": "unit_of_measure", "data_type": "string", "name": "计量单位", "required": False,  "description": "计量单位（如：PCS/片/千克/米）"},
        {"field_id": "safety_stock_level", "data_type": "float", "name": "安全库存", "required": False,  "description": "安全库存水平（低于此值触发预警）"},
        {"field_id": "reorder_point", "data_type": "float", "name": "Reorder点", "required": False,  "description": "再订购点（低于此值触发采购）"},
        {"field_id": "lot_size", "data_type": "float", "name": "订购批量", "required": False,  "description": "订购批量（每次采购的标准数量）"},
        {"field_id": "eoq", "data_type": "float", "name": "经济订购量", "required": False,  "description": "经济订购量（Economic Order Quantity，最优采购批量）"},
        {"field_id": "annual_demand", "data_type": "float", "name": "年需求量", "required": False,  "description": "年需求量（用于EOQ计算）"},
        {"field_id": "holding_cost_rate", "data_type": "float", "name": "持有成本率", "required": False,  "description": "持有成本率（库存成本占物料价值的比例）"},
        {"field_id": "is_active", "data_type": "boolean", "name": "是否激活", "required": False,  "description": "是否启用（True=启用，False=停用）"},
        {"field_id": "created_at", "data_type": "datetime", "name": "创建时间", "required": False,  "description": "创建时间（系统自动生成）"},
    ],
    "work_center": [
        {"field_id": "work_center_id", "data_type": "string", "name": "工作中心ID", "required": True,  "description": "工作中心唯一标识符（主键）"},
        {"field_id": "work_center_name", "data_type": "string", "name": "工作中心名称", "required": True,  "description": "工作中心名称"},
        {"field_id": "work_center_type", "data_type": "string", "name": "类型", "required": True,  "description": "工作中心类型（枚举：接收/加工/检验/测试/辅助/出货）", "is_enum": True, "enum_values": ["接收", "加工", "检验", "测试", "辅助", "出货"]},
        {"field_id": "capacity_uom", "data_type": "string", "name": "产能单位", "required": False,  "description": "产能计量单位（如：小时/片/批次）"},
        {"field_id": "is_active", "data_type": "boolean", "name": "是否激活", "required": False,  "description": "是否启用（True=启用，False=停用）"},
    ],
    "machine": [
        {"field_id": "machine_id", "data_type": "string", "name": "机台ID", "required": True,  "description": "机台唯一标识符"},
        {"field_id": "machine_name", "data_type": "string", "name": "机台名称", "required": True,  "description": "机台名称"},
        {"field_id": "machine_type", "data_type": "string", "name": "机台类型", "required": True,  "description": "机台类型（枚举：自动/半自动/手动）", "is_enum": True, "enum_values": ["自动", "半自动", "手动"]},
        {"field_id": "work_center_id", "data_type": "string", "name": "所属工作中心ID", "required": True,  "description": "所属工作中心ID（外键关联work_center表）"},
        {"field_id": "max_capacity_per_hour", "data_type": "float", "name": "最大产能(片/小时)", "required": False,  "description": "最大产能（单位：片/小时）"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "机台状态（枚举：在线/离线/维护中/故障/待机）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "current_product_id", "data_type": "string", "name": "当前生产产品ID", "required": False,  "description": "当前加工产品ID"},
        {"field_id": "current_setup_group", "data_type": "string", "name": "当前换线组", "required": False,  "description": "当前换线组状态"},
        {"field_id": "last_maintenance_date", "data_type": "date", "name": "上次维护日期", "required": False,  "description": "上次维护日期"},
        {"field_id": "next_maintenance_date", "data_type": "date", "name": "下次维护日期", "required": False,  "description": "下次维护日期（到期需安排保养）"},
        {"field_id": "is_active", "data_type": "boolean", "name": "是否启用", "required": False,  "description": "是否启用（True=启用，False=停用）"},
    ],
    "process_route": [
        {"field_id": "route_id", "data_type": "string", "name": "路线ID", "required": True,  "description": "工艺路线唯一标识符"},
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "route_name", "data_type": "string", "name": "路线名称", "required": True,  "description": "工艺路线名称"},
        {"field_id": "version", "data_type": "string", "name": "版本", "required": False,  "description": "版本号（格式：v1.0/v2.0）"},
        {"field_id": "is_active", "data_type": "boolean", "name": "是否激活", "required": False,  "description": "是否启用（True=启用，False=停用）"},
        {"field_id": "effective_date", "data_type": "date", "name": "生效日期", "required": False,  "description": "生效日期"},
        {"field_id": "expiry_date", "data_type": "date", "name": "失效日期", "required": False,  "description": "失效日期（过期后不可使用）"},
    ],
    "route_step": [
        {"field_id": "step_id", "data_type": "string", "name": "工序ID", "required": True,  "description": "工序唯一标识符"},
        {"field_id": "route_id", "data_type": "string", "name": "所属路线ID", "required": True,  "description": "工艺路线唯一标识符"},
        {"field_id": "sequence_no", "data_type": "integer", "name": "工序序号", "required": True,  "description": "工序序号（执行顺序，从1开始）"},
        {"field_id": "step_name", "data_type": "string", "name": "工序名称", "required": True,  "description": "工序名称"},
        {"field_id": "operation_type", "data_type": "string", "name": "操作类型", "required": False,  "description": "操作类型（枚举：加工/检验）", "is_enum": True, "enum_values": ["加工", "检验"]},
        {"field_id": "standard_time_hours", "data_type": "float", "name": "标准工时(小时)", "required": False,  "description": "标准工时（单位：小时）"},
        {"field_id": "machine_type_required", "data_type": "string", "name": "所需工作中心ID", "required": True,  "description": "所需机台类型"},
        {"field_id": "setup_time_minutes", "data_type": "integer", "name": "换线时间(分钟)", "required": False,  "description": "换线/准备时间（单位：分钟）"},
        {"field_id": "material_ready_offset_hours", "data_type": "float", "name": "物料准备偏移(小时)", "required": False,  "description": "物料准备提前时间（单位：小时，工序开始前物料需到位的时间）"},
        {"field_id": "yield_rate_standard", "data_type": "float", "name": "标准良率", "required": False,  "description": "标准良率（目标良率，如0.98表示98%）"},
        {"field_id": "is_critical", "data_type": "boolean", "name": "是否关键工序", "required": False,  "description": "是否关键工序（True=关键路径，影响整体交期）"},
        {"field_id": "wait_time_hours", "data_type": "float", "name": "等待时间(小时)", "required": False,  "description": "工序间等待时间（如固化/冷却时间，单位：小时）"},
        {"field_id": "transport_time_hours", "data_type": "float", "name": "转运时间(小时)", "required": False,  "description": "转运时间（到下一工作中心的时间，单位：小时）"},
        {"field_id": "min_batch_qty", "data_type": "float", "name": "最小批量", "required": False,  "description": "最小批量（合批排程的最小数量）"},
        {"field_id": "max_batch_qty", "data_type": "float", "name": "最大批量", "required": False,  "description": "最大批量（单次加工的最大数量约束）"},
    ],
    "machine_capability": [
        {"field_id": "capability_id", "data_type": "string", "name": "能力ID", "required": True,  "description": "能力矩阵唯一标识符"},
        {"field_id": "machine_id", "data_type": "string", "name": "机台ID", "required": True,  "description": "机台唯一标识符"},
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "efficiency_factor", "data_type": "float", "name": "效率因子", "required": False,  "description": "效率因子（如1.0表示标准效率，1.2表示120%效率）"},
        {"field_id": "setup_time_minutes", "data_type": "integer", "name": "换线时间(分钟)", "required": False,  "description": "换线/准备时间（单位：分钟）"},
        {"field_id": "yield_rate", "data_type": "float", "name": "良率", "required": False,  "description": "实际良率（历史统计良率）"},
        {"field_id": "is_preferred", "data_type": "boolean", "name": "是否首选", "required": False,  "description": "是否首选机台（True=优先分配任务）"},
        {"field_id": "rated_speed_per_hour", "data_type": "float", "name": "额定速度(片/小时)", "required": False,  "description": "额定速度（单位：片/小时）"},
        {"field_id": "effective_date", "data_type": "date", "name": "生效日期", "required": False,  "description": "生效日期"},
        {"field_id": "actual_efficiency_avg", "data_type": "float", "name": "实际效率均值", "required": False,  "description": "实际效率均值（基于历史任务统计）"},
        {"field_id": "actual_yield_avg", "data_type": "float", "name": "实际良率均值", "required": False,  "description": "实际良率均值（基于历史任务统计）"},
        {"field_id": "sample_count", "data_type": "integer", "name": "样本数量", "required": False,  "description": "统计样本数量（用于计算均值）"},
        {"field_id": "last_updated_at", "data_type": "datetime", "name": "最后更新时间", "required": False,  "description": "最后更新时间（OEE数据更新时间）"},
    ],
    "setup_matrix": [
        {"field_id": "matrix_id", "data_type": "string", "name": "矩阵ID", "required": True,  "description": "换线矩阵唯一标识符"},
        {"field_id": "machine_id", "data_type": "string", "name": "机台ID", "required": True,  "description": "机台唯一标识符"},
        {"field_id": "from_product_id", "data_type": "string", "name": "切换前产品ID", "required": True,  "description": "切换前产品ID"},
        {"field_id": "to_product_id", "data_type": "string", "name": "切换后产品ID", "required": True,  "description": "切换后产品ID"},
        {"field_id": "setup_time_minutes", "data_type": "integer", "name": "换线时间(分钟)", "required": False,  "description": "换线/准备时间（单位：分钟）"},
        {"field_id": "setup_type", "data_type": "string", "name": "换线类型", "required": False,  "description": "换线类型（枚举：换模）", "is_enum": True, "enum_values": ["换模"]},
        {"field_id": "is_active", "data_type": "boolean", "name": "是否激活", "required": False,  "description": "是否启用（True=启用，False=停用）"},
    ],
    "shift_pattern": [
        {"field_id": "shift_id", "data_type": "string", "name": "班次ID", "required": True,  "description": "班次唯一标识符"},
        {"field_id": "shift_name", "data_type": "string", "name": "班次名称", "required": True,  "description": "班次名称（如：早班/中班/夜班）"},
        {"field_id": "start_time", "data_type": "string", "name": "开始时间", "required": True,  "description": "开始时间（格式：HH:MM，如08:00）"},
        {"field_id": "end_time", "data_type": "string", "name": "结束时间", "required": True,  "description": "结束时间（格式：HH:MM，如17:00）"},
        {"field_id": "available_hours", "data_type": "float", "name": "可用工时", "required": False,  "description": "可用工时（单位：小时）"},
        {"field_id": "efficiency_factor", "data_type": "float", "name": "效率因子", "required": False,  "description": "效率因子（如1.0表示标准效率，1.2表示120%效率）"},
        {"field_id": "is_active", "data_type": "boolean", "name": "是否激活", "required": False,  "description": "是否启用（True=启用，False=停用）"},
    ],
    "supplier": [
        {"field_id": "supplier_id", "data_type": "string", "name": "供应商ID", "required": True,  "description": "供应商唯一标识符"},
        {"field_id": "supplier_name", "data_type": "string", "name": "供应商名称", "required": True,  "description": "供应商名称"},
        {"field_id": "supplier_type", "data_type": "string", "name": "合作类型", "required": False,  "description": "合作类型（枚举：战略合作/直供/进口/备选）", "is_enum": True, "enum_values": ["战略合作", "直供", "进口", "备选"]},
        {"field_id": "country", "data_type": "string", "name": "国家/地区", "required": False,  "description": "国家/地区（如：中国/美国/日本/台湾）"},
        {"field_id": "industry_position", "data_type": "string", "name": "行业地位", "required": False,  "description": "行业地位（如：全球前三/国内领先/区域主要供应商）"},
        {"field_id": "avg_lead_time_days", "data_type": "integer", "name": "平均交期(天)", "required": False,  "description": "平均交期（单位：天，从下单到收货的平均时间）"},
        {"field_id": "reliability_score", "data_type": "float", "name": "可靠度评分", "required": False,  "description": "可靠度评分（0-1之间，越高越可靠）"},
        {"field_id": "min_order_quantity", "data_type": "float", "name": "最小订购量", "required": False,  "description": "最小订购量（MOQ，低于此数量不接受订单）"},
        {"field_id": "lead_time_stddev_days", "data_type": "float", "name": "交期标准差(天)", "required": False,  "description": "交期标准差（天，衡量交期稳定性）"},
        {"field_id": "is_active", "data_type": "boolean", "name": "是否激活", "required": False,  "description": "是否启用（True=启用，False=停用）"},
    ],
    "supplier_material": [
        {"field_id": "sm_id", "data_type": "string", "name": "关系ID", "required": True,  "description": "供应商物料关系唯一标识符"},
        {"field_id": "supplier_id", "data_type": "string", "name": "供应商ID", "required": True,  "description": "供应商唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "unit_price", "data_type": "float", "name": "单价", "required": False,  "description": "订单单价（单位：元）"},
        {"field_id": "lead_time_days", "data_type": "integer", "name": "交期(天)", "required": False,  "description": "交期（单位：天）"},
        {"field_id": "min_order_qty", "data_type": "float", "name": "最小订购量", "required": False,  "description": "最小订购量（MOQ，供应商要求的最小采购数量）"},
        {"field_id": "max_order_qty", "data_type": "float", "name": "最大订购量", "required": False,  "description": "最大订购量（供应商单次最大供货能力）"},
        {"field_id": "is_preferred", "data_type": "boolean", "name": "是否首选供应商", "required": False,  "description": "是否首选供应商（True=优先采购）"},
        {"field_id": "effective_date", "data_type": "date", "name": "生效日期", "required": False,  "description": "生效日期"},
        {"field_id": "expiry_date", "data_type": "date", "name": "失效日期", "required": False,  "description": "失效日期（过期后不可使用）"},
    ],
    "material_substitute": [
        {"field_id": "ms_id", "data_type": "string", "name": "替代关系ID", "required": True,  "description": "物料替代关系唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "原物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "substitute_material_id", "data_type": "string", "name": "替代物料ID", "required": True,  "description": "替代物料ID"},
        {"field_id": "substitute_priority", "data_type": "integer", "name": "替代优先级", "required": False,  "description": "替代优先级（数字越小优先级越高）"},
        {"field_id": "quality_grade", "data_type": "string", "name": "质量等级", "required": False,  "description": "质量等级（枚举：同等级/略低）", "is_enum": True, "enum_values": ["同等级", "略低"]},
        {"field_id": "approval_status", "data_type": "string", "name": "审批状态", "required": False,  "description": "审批状态（枚举：已批准/待审批/已拒绝）", "is_enum": True, "enum_values": ["已批准", "待审批", "已拒绝"]},
        {"field_id": "cost_delta_percent", "data_type": "float", "name": "成本差异(%)", "required": False,  "description": "成本差异百分比（正数表示更贵，负数表示更便宜）"},
    ],
    "bom": [
        {"field_id": "bom_id", "data_type": "string", "name": "BOM ID", "required": True,  "description": "BOM唯一标识符"},
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "step_id", "data_type": "string", "name": "消耗工序ID", "required": False,  "description": "工序唯一标识符"},
        {"field_id": "quantity_per_unit", "data_type": "float", "name": "单位用量", "required": False,  "description": "单位用量（生产1个产品需要的物料数量）"},
        {"field_id": "is_critical", "data_type": "boolean", "name": "是否关键物料", "required": False,  "description": "是否关键物料（True=缺料会导致停产）"},
        {"field_id": "consumption_pattern", "data_type": "string", "name": "消耗模式", "required": False,  "description": "消耗模式（枚举：工序开始时消耗/按比例消耗）", "is_enum": True, "enum_values": ["工序开始时消耗", "按比例消耗"]},
        {"field_id": "version", "data_type": "string", "name": "版本", "required": False,  "description": "版本号（格式：v1.0/v2.0）"},
        {"field_id": "effective_date", "data_type": "date", "name": "生效日期", "required": False,  "description": "生效日期"},
        {"field_id": "expiry_date", "data_type": "date", "name": "失效日期", "required": False,  "description": "失效日期（过期后不可使用）"},
    ],
    "customer": [
        {"field_id": "customer_id", "data_type": "string", "name": "客户ID", "required": True,  "description": "客户唯一标识符"},
        {"field_id": "customer_name", "data_type": "string", "name": "客户名称", "required": True,  "description": "客户名称"},
        {"field_id": "customer_level", "data_type": "string", "name": "客户等级", "required": False,  "description": "客户等级（枚举：VIP/重要/普通）", "is_enum": True, "enum_values": ["VIP", "重要", "普通"]},
        {"field_id": "industry", "data_type": "string", "name": "行业类别", "required": False,  "description": "所属行业（如：汽车电子/消费电子/工业控制/通信）"},
        {"field_id": "credit_limit", "data_type": "float", "name": "信用额度(万元)", "required": False,  "description": "信用额度（单位：万元）"},
        {"field_id": "payment_terms", "data_type": "string", "name": "付款条件", "required": False,  "description": "付款条件（如：月结30天/货到付款/预付50%）"},
        {"field_id": "contact_person", "data_type": "string", "name": "联系人", "required": False,  "description": "联系人姓名"},
        {"field_id": "contact_phone", "data_type": "string", "name": "联系电话", "required": False,  "description": "联系电话"},
        {"field_id": "contact_email", "data_type": "string", "name": "联系邮箱", "required": False,  "description": "联系邮箱"},
        {"field_id": "address", "data_type": "text", "name": "地址", "required": False,  "description": "地址"},
        {"field_id": "country", "data_type": "string", "name": "国家", "required": False,  "description": "国家/地区（如：中国/美国/日本/台湾）"},
        {"field_id": "region", "data_type": "string", "name": "地区", "required": False,  "description": "地区（枚举：大陆/台湾/欧美/亚太）", "is_enum": True, "enum_values": ["大陆", "台湾", "欧美", "亚太"]},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "客户状态（枚举：活跃/暂停/关闭）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "customer_product": [
        {"field_id": "id", "data_type": "integer", "name": "ID", "required": False,  "description": "唯一标识符（主键）"},
        {"field_id": "customer_id", "data_type": "string", "name": "客户ID", "required": True,  "description": "客户唯一标识符"},
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "special_price", "data_type": "float", "name": "客户特定价格", "required": False,  "description": "客户特定价格（覆盖标准价格）"},
        {"field_id": "min_order_qty", "data_type": "float", "name": "最小订单量", "required": False,  "description": "最小订单量（客户级别的最小订购数量）"},
        {"field_id": "lead_time_days", "data_type": "integer", "name": "特定交期(天)", "required": False,  "description": "交期（单位：天）"},
        {"field_id": "quality_level", "data_type": "string", "name": "质量等级", "required": False,  "description": "质量等级要求（枚举：标准/车规/工规/军规）", "is_enum": True, "enum_values": ["标准", "车规", "工规", "军规"]},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "客户产品关系状态（枚举：有效/已停用）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
    ],
    "customer_order": [
        {"field_id": "order_id", "data_type": "string", "name": "订单ID", "required": True,  "description": "订单唯一标识符"},
        {"field_id": "customer_id", "data_type": "string", "name": "客户ID", "required": True,  "description": "客户唯一标识符"},
        {"field_id": "customer_name", "data_type": "string", "name": "客户名称", "required": True,  "description": "客户名称"},
        {"field_id": "customer_po_number", "data_type": "string", "name": "客户采购订单号", "required": False,  "description": "客户采购订单号（客户方的订单编号）"},
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "quantity", "data_type": "float", "name": "订单数量", "required": True,  "description": "数量"},
        {"field_id": "unit_price", "data_type": "float", "name": "订单单价", "required": False,  "description": "订单单价（单位：元）"},
        {"field_id": "order_date", "data_type": "datetime", "name": "下单日期", "required": True,  "description": "下单日期"},
        {"field_id": "required_date", "data_type": "datetime", "name": "要求交期", "required": True,  "description": "要求交货日期"},
        {"field_id": "priority", "data_type": "integer", "name": "优先级", "required": False,  "description": "订单优先级（数字越小优先级越高，1-5范围：1=紧急/3=普通/5=宽松）"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "订单状态（枚举：已确认/部分发货/已发货/已取消/重工中）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "shipping_address", "data_type": "text", "name": "发货地址", "required": False,  "description": "收货地址"},
        {"field_id": "quality_requirement", "data_type": "string", "name": "质量要求", "required": False,  "description": "质量要求（如：AQL 0.65/零缺陷）"},
        {"field_id": "packaging_requirement", "data_type": "string", "name": "包装要求", "required": False,  "description": "包装要求（如：防静电包装/真空包装）"},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "work_order": [
        {"field_id": "work_order_id", "data_type": "string", "name": "工单ID", "required": True,  "description": "工单唯一标识符"},
        {"field_id": "customer_order_id", "data_type": "string", "name": "关联订单ID", "required": False,  "description": "关联客户订单ID"},
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "work_order_type", "data_type": "string", "name": "工单类型", "required": False,  "description": "工单类型（枚举：正常/重工）", "is_enum": True, "enum_values": ["正常", "重工"]},
        {"field_id": "planned_quantity", "data_type": "float", "name": "计划投入量", "required": True,  "description": "计划投入量（含过量投入，考虑良率损耗）"},
        {"field_id": "expected_output_qty", "data_type": "float", "name": "预期产出量", "required": False,  "description": "预期产出量（订单需求数量）"},
        {"field_id": "planned_start_date", "data_type": "datetime", "name": "计划开始日期", "required": False,  "description": "计划开始日期"},
        {"field_id": "planned_completion_date", "data_type": "datetime", "name": "计划完成日期", "required": False,  "description": "计划完成日期"},
        {"field_id": "actual_start_date", "data_type": "datetime", "name": "实际开始日期", "required": False,  "description": "实际开始日期"},
        {"field_id": "actual_completion_date", "data_type": "datetime", "name": "实际完成日期", "required": False,  "description": "实际完成日期"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "工单状态（枚举：生产中/已完成/已取消）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "priority", "data_type": "integer", "name": "优先级", "required": False,  "description": "工单优先级（继承自订单优先级）"},
        {"field_id": "setup_group", "data_type": "string", "name": "换线组", "required": False,  "description": "换线组（用于排程优化，同组工单可合并）"},
        {"field_id": "current_step_id", "data_type": "string", "name": "当前工序ID", "required": False,  "description": "当前执行工序ID"},
        {"field_id": "completed_quantity", "data_type": "float", "name": "实际产出量", "required": False,  "description": "实际产出量（良品数量）"},
        {"field_id": "scrapped_quantity", "data_type": "float", "name": "报废数量", "required": False,  "description": "报废数量（不良品且不可返工）"},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
        {"field_id": "created_at", "data_type": "datetime", "name": "创建时间", "required": False,  "description": "创建时间（系统自动生成）"},
    ],
    "work_order_operation": [
        {"field_id": "wo_op_id", "data_type": "string", "name": "工单工序ID", "required": True,  "description": "工单工序唯一标识符"},
        {"field_id": "work_order_id", "data_type": "string", "name": "工单ID", "required": True,  "description": "工单唯一标识符"},
        {"field_id": "step_id", "data_type": "string", "name": "工序ID", "required": True,  "description": "工序唯一标识符"},
        {"field_id": "sequence_no", "data_type": "integer", "name": "工序序号", "required": True,  "description": "工序序号（执行顺序，从1开始）"},
        {"field_id": "planned_start", "data_type": "datetime", "name": "计划开始时间", "required": False,  "description": "计划开始时间"},
        {"field_id": "planned_end", "data_type": "datetime", "name": "计划结束时间", "required": False,  "description": "计划结束时间"},
        {"field_id": "actual_start", "data_type": "datetime", "name": "实际开始时间", "required": False,  "description": "实际开始时间"},
        {"field_id": "actual_end", "data_type": "datetime", "name": "实际结束时间", "required": False,  "description": "实际结束时间"},
        {"field_id": "required_input_qty", "data_type": "float", "name": "需求投入量", "required": True,  "description": "需求投入量（考虑良率后的实际投入数量）"},
        {"field_id": "completed_output_qty", "data_type": "float", "name": "实际产出量", "required": False,  "description": "实际产出量（良品数量）"},
        {"field_id": "scrapped_qty", "data_type": "float", "name": "报废量", "required": False,  "description": "报废数量"},
        {"field_id": "assigned_machine_id", "data_type": "string", "name": "分配机台ID", "required": False,  "description": "分配机台ID（外键关联machine表）"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "工单工序状态（枚举：已完成/已排程/待开工）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "is_rework", "data_type": "boolean", "name": "是否重工序", "required": False,  "description": "是否重工序（True=重工工序，用于追溯和统计）"},
        {"field_id": "setup_completed", "data_type": "boolean", "name": "换线是否完成", "required": False,  "description": "换线/准备是否完成（True=已完成）"},
        {"field_id": "material_issued", "data_type": "boolean", "name": "物料是否发放", "required": False,  "description": "物料是否已发放（True=物料已领用）"},
    ],
    "work_order_material": [
        {"field_id": "wom_id", "data_type": "string", "name": "工单物料需求ID", "required": True,  "description": "工单物料需求唯一标识符"},
        {"field_id": "work_order_id", "data_type": "string", "name": "工单ID", "required": True,  "description": "工单唯一标识符"},
        {"field_id": "wo_op_id", "data_type": "string", "name": "工单工序ID", "required": False,  "description": "工单工序唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "required_quantity", "data_type": "float", "name": "需求数量", "required": True,  "description": "需求数量"},
        {"field_id": "allocated_quantity", "data_type": "float", "name": "已分配数量", "required": False,  "description": "已分配数量（已从库存预留）"},
        {"field_id": "consumed_quantity", "data_type": "float", "name": "已消耗数量", "required": False,  "description": "已消耗数量（已实际使用）"},
        {"field_id": "shortage_quantity", "data_type": "float", "name": "缺料数量", "required": False,  "description": "缺料数量（需求-已分配）"},
        {"field_id": "required_date", "data_type": "datetime", "name": "需求日期", "required": False,  "description": "物料需求日期（工序计划开始时间）"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "工单物料状态（枚举：待分配/已消耗/已齐套/已取消/部分分配/缺料）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "purchase_order": [
        {"field_id": "po_id", "data_type": "string", "name": "采购订单ID", "required": True,  "description": "采购订单唯一标识符"},
        {"field_id": "supplier_id", "data_type": "string", "name": "供应商ID", "required": True,  "description": "供应商唯一标识符"},
        {"field_id": "order_date", "data_type": "datetime", "name": "下单日期", "required": True,  "description": "下单日期"},
        {"field_id": "expected_delivery_date", "data_type": "datetime", "name": "预期交货日期", "required": True,  "description": "期望交货日期"},
        {"field_id": "actual_delivery_date", "data_type": "datetime", "name": "实际交货日期", "required": False,  "description": "实际交货日期"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "采购订单状态（枚举：已入库/已创建）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "total_amount", "data_type": "float", "name": "总金额", "required": False,  "description": "总金额（单位：元）"},
        {"field_id": "created_by", "data_type": "string", "name": "创建者", "required": False,  "description": "创建人（如：SYSTEM/MRP/用户名）"},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "purchase_order_line": [
        {"field_id": "line_id", "data_type": "string", "name": "订单行ID", "required": True,  "description": "唯一标识符（主键）"},
        {"field_id": "po_id", "data_type": "string", "name": "采购订单ID", "required": True,  "description": "采购订单唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "quantity", "data_type": "float", "name": "采购数量", "required": True,  "description": "数量"},
        {"field_id": "unit_price", "data_type": "float", "name": "单价", "required": False,  "description": "订单单价（单位：元）"},
        {"field_id": "received_quantity", "data_type": "float", "name": "已收货数量", "required": False,  "description": "已收货数量"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "采购订单行状态（枚举：待收货/部分到货/全部到货）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "related_work_order_id", "data_type": "string", "name": "关联工单ID", "required": False,  "description": "关联工单ID"},
        {"field_id": "related_wom_id", "data_type": "string", "name": "关联工单物料需求ID", "required": False,  "description": "关联工单物料需求ID"},
    ],
    "wip_lot": [
        {"field_id": "lot_id", "data_type": "string", "name": "批次ID", "required": True,  "description": "批次唯一标识符"},
        {"field_id": "work_order_id", "data_type": "string", "name": "工单ID", "required": True,  "description": "工单唯一标识符"},
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "lot_size", "data_type": "float", "name": "批次大小", "required": False,  "description": "批次大小（标准25片/批）"},
        {"field_id": "current_step_id", "data_type": "string", "name": "当前工序ID", "required": False,  "description": "当前执行工序ID"},
        {"field_id": "current_machine_id", "data_type": "string", "name": "当前机台ID", "required": False,  "description": "当前加工机台ID（外键关联machine表）"},
        {"field_id": "lot_quantity", "data_type": "float", "name": "批次数量", "required": True,  "description": "批次数量"},
        {"field_id": "actual_quantity", "data_type": "float", "name": "实际数量", "required": False,  "description": "实际数量"},
        {"field_id": "lot_status", "data_type": "string", "name": "批次状态", "required": False,  "description": "批次状态（枚举：排队中/加工中/已完成）", "is_enum": True, "enum_values": ["排队中", "加工中", "已完成"]},
        {"field_id": "queue_start_time", "data_type": "datetime", "name": "排队开始时间", "required": False,  "description": "排队开始时间"},
        {"field_id": "processing_start_time", "data_type": "datetime", "name": "加工开始时间", "required": False,  "description": "加工开始时间"},
        {"field_id": "completed_time", "data_type": "datetime", "name": "完工时间", "required": False,  "description": "完工时间"},
        {"field_id": "hold_reason", "data_type": "string", "name": "Hold原因", "required": False,  "description": "冻结原因（如：待检验/质量问题/客户暂停）"},
        {"field_id": "priority", "data_type": "integer", "name": "优先级", "required": False,  "description": "优先级（数字越小优先级越高，1-10范围）"},
        {"field_id": "created_at", "data_type": "datetime", "name": "创建时间", "required": False,  "description": "创建时间（系统自动生成）"},
    ],
    "production_task": [
        {"field_id": "task_id", "data_type": "string", "name": "任务ID", "required": True,  "description": "生产任务唯一标识符"},
        {"field_id": "wo_op_id", "data_type": "string", "name": "工单工序ID", "required": True,  "description": "工单工序唯一标识符"},
        {"field_id": "work_order_id", "data_type": "string", "name": "工单ID", "required": True,  "description": "工单唯一标识符"},
        {"field_id": "machine_id", "data_type": "string", "name": "机台ID", "required": True,  "description": "机台唯一标识符"},
        {"field_id": "lot_id", "data_type": "string", "name": "批次ID", "required": False,  "description": "批次唯一标识符"},
        {"field_id": "planned_start_time", "data_type": "datetime", "name": "计划开始时间", "required": True,  "description": "计划开始时间"},
        {"field_id": "planned_end_time", "data_type": "datetime", "name": "计划结束时间", "required": True,  "description": "计划结束时间"},
        {"field_id": "actual_start_time", "data_type": "datetime", "name": "实际开始时间", "required": False,  "description": "实际开始时间"},
        {"field_id": "actual_end_time", "data_type": "datetime", "name": "实际结束时间", "required": False,  "description": "实际结束时间"},
        {"field_id": "planned_quantity", "data_type": "float", "name": "计划数量", "required": True,  "description": "计划数量"},
        {"field_id": "actual_quantity", "data_type": "float", "name": "实际数量", "required": False,  "description": "实际数量"},
        {"field_id": "scrap_quantity", "data_type": "float", "name": "报废数量", "required": False,  "description": "报废数量"},
        {"field_id": "actual_efficiency", "data_type": "float", "name": "实际效率", "required": False,  "description": "实际效率（相对于标准效率的比例）"},
        {"field_id": "actual_yield", "data_type": "float", "name": "实际良率", "required": False,  "description": "实际良率（良品/总投入）"},
        {"field_id": "setup_time_actual", "data_type": "float", "name": "实际换线时间", "required": False,  "description": "实际换线时间（单位：分钟）"},
        {"field_id": "wait_time_actual", "data_type": "float", "name": "实际等待时间", "required": False,  "description": "实际等待时间（含排队+转运，单位：小时）"},
        {"field_id": "shift_id", "data_type": "string", "name": "班次ID", "required": False,  "description": "班次唯一标识符"},
        {"field_id": "is_night_shift", "data_type": "boolean", "name": "是否夜班", "required": False,  "description": "是否夜班（True=夜班）"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "生产任务状态（枚举：已排程/待执行/执行中/已完成/已取消/已延期）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "material_transfer": [
        {"field_id": "transfer_id", "data_type": "string", "name": "调拨ID", "required": True,  "description": "调拨单唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "from_work_order_id", "data_type": "string", "name": "来源工单ID", "required": False,  "description": "调拨来源工单ID（从哪个工单调出）"},
        {"field_id": "to_work_order_id", "data_type": "string", "name": "目标工单ID", "required": False,  "description": "调拨目标工单ID（调入到哪个工单）"},
        {"field_id": "from_location", "data_type": "string", "name": "来源仓库", "required": False,  "description": "来源仓库/位置"},
        {"field_id": "to_location", "data_type": "string", "name": "目标仓库", "required": False,  "description": "目标仓库/位置"},
        {"field_id": "from_wom_id", "data_type": "string", "name": "来源工单物料需求ID", "required": False,  "description": "调出工单物料需求ID（from_work_order的物料需求）"},
        {"field_id": "to_wom_id", "data_type": "string", "name": "目标工单物料需求ID", "required": False,  "description": "调入工单物料需求ID（to_work_order的物料需求）"},
        {"field_id": "quantity", "data_type": "float", "name": "调拨数量", "required": True,  "description": "调拨数量（实际转移的物料数量）"},
        {"field_id": "transfer_reason", "data_type": "string", "name": "调拨原因", "required": False,  "description": "调拨原因（如：缺料挪用/紧急调拨/仓库调整）"},
        {"field_id": "trigger_source", "data_type": "string", "name": "触发来源", "required": False,  "description": "触发来源（如：MRP运算/人工创建/系统自动）"},
        {"field_id": "requested_time", "data_type": "datetime", "name": "申请时间", "required": True,  "description": "申请时间"},
        {"field_id": "executed_time", "data_type": "datetime", "name": "执行时间", "required": False,  "description": "执行时间（实际调拨完成时间）"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": False,  "description": "调拨单状态（枚举：已执行）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "approved_by", "data_type": "string", "name": "批准人", "required": False,  "description": "审批人"},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "work_calendar": [
        {"field_id": "calendar_id", "data_type": "string", "name": "日历ID", "required": True,  "description": "日历记录唯一标识符"},
        {"field_id": "calendar_date", "data_type": "date", "name": "日期", "required": True,  "description": "日历日期"},
        {"field_id": "work_center_id", "data_type": "string", "name": "工作中心ID", "required": True,  "description": "工作中心ID（外键关联work_center表）"},
        {"field_id": "shift_id", "data_type": "string", "name": "班次ID", "required": True,  "description": "班次唯一标识符"},
        {"field_id": "is_workday", "data_type": "boolean", "name": "是否工作日", "required": False,  "description": "是否工作日（True=工作日，False=休息日）"},
        {"field_id": "available_hours", "data_type": "float", "name": "可用工时", "required": False,  "description": "可用工时（单位：小时）"},
        {"field_id": "planned_capacity", "data_type": "float", "name": "计划产能", "required": False,  "description": "计划产能（单位：片/班次）"},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "inventory": [
        {"field_id": "inventory_id", "data_type": "string", "name": "库存ID", "required": True,  "description": "库存记录唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "location", "data_type": "string", "name": "仓库位置", "required": False,  "description": "仓库/位置（如：主仓库/线边仓/成品仓）"},
        {"field_id": "total_quantity", "data_type": "float", "name": "总数量", "required": False,  "description": "总数量（可用+预留）"},
        {"field_id": "available_quantity", "data_type": "float", "name": "可用数量", "required": False,  "description": "可用数量（可被分配的数量）"},
        {"field_id": "reserved_quantity", "data_type": "float", "name": "预留数量", "required": False,  "description": "预留数量（已分配但未领用）"},
        {"field_id": "in_transit_quantity", "data_type": "float", "name": "在途数量", "required": False,  "description": "在途数量（已采购但未到货，不可用）"},
        {"field_id": "last_updated", "data_type": "datetime", "name": "最后更新时间", "required": False,  "description": "最后更新时间"},
    ],
    "inventory_transaction": [
        {"field_id": "transaction_id", "data_type": "string", "name": "事务ID", "required": True,  "description": "事务流水唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": True,  "description": "物料唯一标识符"},
        {"field_id": "transaction_type", "data_type": "string", "name": "事务类型", "required": True,  "description": "事务类型（枚举：出库/IQC入库/取消释放/生产消耗/盘点亏损/盘点盈余/调拨出库/采购入库/预留）", "is_enum": True, "enum_values": ["出库", "IQC入库", "取消释放", "生产消耗", "盘点亏损", "盘点盈余", "调拨出库", "采购入库", "预留"]},
        {"field_id": "quantity", "data_type": "float", "name": "变动数量", "required": True,  "description": "数量"},
        {"field_id": "balance_after", "data_type": "float", "name": "变动后总库存", "required": True,  "description": "事务后总数量"},
        {"field_id": "available_balance_after", "data_type": "float", "name": "变动后可用库存", "required": True,  "description": "事务后可用数量"},
        {"field_id": "reserved_balance_after", "data_type": "float", "name": "变动后预留库存", "required": True,  "description": "事务后预留数量"},
        {"field_id": "related_document_type", "data_type": "string", "name": "关联单据类型", "required": False,  "description": "关联单据类型（如：WorkOrder/PurchaseOrder/Transfer）"},
        {"field_id": "related_document_id", "data_type": "string", "name": "关联单据ID", "required": False,  "description": "关联单据ID（根据related_document_type关联不同表）"},
        {"field_id": "from_work_order_id", "data_type": "string", "name": "来源工单ID", "required": False,  "description": "库存事务来源工单ID（出库时）"},
        {"field_id": "to_work_order_id", "data_type": "string", "name": "目标工单ID", "required": False,  "description": "库存事务目标工单ID（入库时）"},
        {"field_id": "transaction_time", "data_type": "datetime", "name": "事务时间", "required": True,  "description": "事务发生时间"},
        {"field_id": "description", "data_type": "text", "name": "事务说明", "required": False,  "description": "事务说明（详细描述本次库存变动原因）"},
        {"field_id": "created_by", "data_type": "string", "name": "创建者", "required": False,  "description": "创建人（如：SYSTEM/MRP/用户名）"},
    ],
    "finished_goods_inventory": [
        {"field_id": "fg_inv_id", "data_type": "string", "name": "成品库存ID", "required": True,  "description": "成品库存唯一标识符"},
        {"field_id": "product_id", "data_type": "string", "name": "产品ID", "required": True,  "description": "产品唯一标识符"},
        {"field_id": "location", "data_type": "string", "name": "仓库位置", "required": False,  "description": "仓库/位置（如：主仓库/线边仓/成品仓）"},
        {"field_id": "total_quantity", "data_type": "float", "name": "总数量", "required": False,  "description": "总数量（可用+预留）"},
        {"field_id": "available_quantity", "data_type": "float", "name": "可用数量", "required": False,  "description": "可用数量（可被分配的数量）"},
        {"field_id": "reserved_quantity", "data_type": "float", "name": "预留数量", "required": False,  "description": "预留数量（已分配但未领用）"},
        {"field_id": "shipped_quantity", "data_type": "float", "name": "已发货数量", "required": False,  "description": "已发货数量（累计出库数量）"},
        {"field_id": "last_updated", "data_type": "datetime", "name": "最后更新时间", "required": False,  "description": "最后更新时间"},
    ],
    "quality_inspection": [
        {"field_id": "inspection_id", "data_type": "string", "name": "检验ID", "required": True,  "description": "检验记录唯一标识符"},
        {"field_id": "inspection_type", "data_type": "string", "name": "检验类型", "required": True,  "description": "检验类型（枚举：FQC出货检验/IQC入料/IQC来料检验/首件检验）", "is_enum": True, "enum_values": ["FQC出货检验", "IQC入料", "IQC来料检验", "首件检验"]},
        {"field_id": "wo_op_id", "data_type": "string", "name": "工单工序ID", "required": False,  "description": "工单工序唯一标识符"},
        {"field_id": "lot_id", "data_type": "string", "name": "批次ID", "required": False,  "description": "批次唯一标识符"},
        {"field_id": "machine_id", "data_type": "string", "name": "机台ID", "required": False,  "description": "机台唯一标识符"},
        {"field_id": "po_id", "data_type": "string", "name": "采购订单ID", "required": False,  "description": "采购订单唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "物料ID", "required": False,  "description": "物料唯一标识符"},
        {"field_id": "related_doc_type", "data_type": "string", "name": "关联单据类型", "required": False,  "description": "关联单据类型（枚举：WorkOrderOperation/PurchaseOrder/CustomerOrder）", "is_enum": True, "enum_values": ["WorkOrderOperation", "PurchaseOrder", "CustomerOrder"]},
        {"field_id": "related_doc_id", "data_type": "string", "name": "关联单据ID", "required": False,  "description": "关联单据ID（根据related_doc_type关联不同表）"},
        {"field_id": "inspection_time", "data_type": "datetime", "name": "检验时间", "required": True,  "description": "检验时间"},
        {"field_id": "inspect_qty", "data_type": "float", "name": "检验数量", "required": False,  "description": "检验数量"},
        {"field_id": "pass_qty", "data_type": "float", "name": "合格数量", "required": False,  "description": "合格数量"},
        {"field_id": "rework_qty", "data_type": "float", "name": "返工数量", "required": False,  "description": "返工数量（可修复的不良品）"},
        {"field_id": "scrap_qty", "data_type": "float", "name": "报废数量", "required": False,  "description": "报废数量（不可修复的不良品）"},
        {"field_id": "concession_qty", "data_type": "float", "name": "让步接收数量", "required": False,  "description": "让步接收数量（不合格但可接受）"},
        {"field_id": "result", "data_type": "string", "name": "结果", "required": False,  "description": "检验结果（枚举：合格/返工/报废/不合格/让步接收/不合格-部分/拒收部分）", "is_enum": True, "enum_values": ["合格", "返工", "报废", "不合格", "让步接收", "不合格-部分", "拒收部分"]},
        {"field_id": "disposition", "data_type": "string", "name": "处置说明", "required": False,  "description": "处置说明（如何处理不合格品）"},
        {"field_id": "is_hold", "data_type": "boolean", "name": "是否Hold", "required": False,  "description": "是否冻结（True=批次被冻结，不可流转）"},
        {"field_id": "inspector", "data_type": "string", "name": "检验员", "required": False,  "description": "检验员（如：QC-AUTO/QC-张三）"},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "schedule": [
        {"field_id": "schedule_id", "data_type": "string", "name": "排程ID", "required": True,  "description": "排程汇总唯一标识符"},
        {"field_id": "schedule_date", "data_type": "date", "name": "排程日期", "required": True,  "description": "排程日期"},
        {"field_id": "total_load_hours", "data_type": "float", "name": "总负荷工时", "required": False,  "description": "总负荷工时（单位：小时）"},
        {"field_id": "utilization_rate", "data_type": "float", "name": "设备利用率", "required": False,  "description": "设备利用率（实际工时/可用工时）"},
        {"field_id": "bottleneck_machine_id", "data_type": "string", "name": "瓶颈机台ID", "required": False,  "description": "瓶颈机台ID（负荷最高的机台）"},
        {"field_id": "bottleneck_work_center_id", "data_type": "string", "name": "瓶颈工作中心ID", "required": False,  "description": "瓶颈工作中心ID（负荷最高的工作中心）"},
        {"field_id": "total_orders", "data_type": "integer", "name": "总订单数", "required": False,  "description": "总订单数"},
        {"field_id": "completed_orders", "data_type": "integer", "name": "完成订单数", "required": False,  "description": "已完成订单数"},
        {"field_id": "created_at", "data_type": "datetime", "name": "创建时间", "required": False,  "description": "创建时间（系统自动生成）"},
    ],
    "machine_status_log": [
        {"field_id": "log_id", "data_type": "string", "name": "日志ID", "required": True,  "description": "日志唯一标识符"},
        {"field_id": "machine_id", "data_type": "string", "name": "机台ID", "required": True,  "description": "机台唯一标识符"},
        {"field_id": "status_time", "data_type": "datetime", "name": "状态时间", "required": True,  "description": "状态记录时间"},
        {"field_id": "status", "data_type": "string", "name": "状态", "required": True,  "description": "机台状态（枚举：恢复/换线/故障/空闲/维护/运行）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "product_id", "data_type": "string", "name": "生产产品ID", "required": False,  "description": "当前加工产品ID（status=在线时有效）"},
        {"field_id": "running_wo_id", "data_type": "string", "name": "运行工单ID", "required": False,  "description": "运行中工单ID"},
        {"field_id": "running_task_id", "data_type": "string", "name": "运行任务ID", "required": False,  "description": "运行中任务ID"},
        {"field_id": "oee", "data_type": "float", "name": "OEE指标", "required": False,  "description": "设备综合效率（Overall Equipment Effectiveness）"},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明"},
    ],
    "external_supply_chain_risk": [
        {"field_id": "risk_id", "data_type": "string", "name": "风险ID", "required": True, "description": "风险事件唯一标识符"},
        {"field_id": "supplier_id", "data_type": "string", "name": "主要受影响供应商ID", "description": "风险事件的直接责任方或主要受影响方（1个）。如需记录多个关联供应商，使用SupplierRiskAssociation对象", "required": False},
        {"field_id": "customer_id", "data_type": "string", "name": "关联客户ID", "required": False, "description": "客户唯一标识符"},
        {"field_id": "material_id", "data_type": "string", "name": "关联物料ID", "required": False, "description": "物料唯一标识符"},
        {"field_id": "risk_category", "data_type": "string", "name": "风险类别", "description": "风险类别（枚举：自然灾害/政治事件/财务风险/质量风险/法律风险/运营风险）", "required": True},
        {"field_id": "risk_level", "data_type": "string", "name": "风险等级", "description": "风险等级（枚举：严重/高/中/低）", "required": True},
        {"field_id": "title", "data_type": "string", "name": "风险标题", "required": True, "description": "风险事件标题", "is_enum": True, "enum_values": ["自然灾害", "政治事件", "财务风险", "质量风险", "法律风险", "运营风险"]},
        {"field_id": "description", "data_type": "text", "name": "风险描述", "required": True, "description": "风险事件描述"},
        {"field_id": "source_url", "data_type": "text", "name": "信息来源URL", "required": False, "description": "信息来源URL（舆情原文链接）"},
        {"field_id": "source_name", "data_type": "string", "name": "信息来源名称", "required": False, "description": "信息来源名称（如：Reuters/Bloomberg/新华社）"},
        {"field_id": "impact_scope", "data_type": "string", "name": "影响范围", "description": "影响范围（枚举：全球/区域/局部）", "required": False},
        {"field_id": "estimated_impact_days", "data_type": "integer", "name": "预估影响天数", "required": False, "description": "预估影响天数", "is_enum": True, "enum_values": ["全球", "区域", "局部"]},
        {"field_id": "affected_materials", "data_type": "array", "name": "受影响物料", "description": "受影响物料的ID列表", "required": False},
        {"field_id": "affected_products", "data_type": "array", "name": "受影响产品", "description": "受影响产品ID列表", "required": False},
        {"field_id": "event_date", "data_type": "date", "name": "事件发生日期", "required": False, "description": "事件发生日期"},
        {"field_id": "detected_at", "data_type": "datetime", "name": "检测时间", "required": False, "description": "检测时间（系统捕获舆情时间）"},
        {"field_id": "status", "data_type": "string", "name": "处理状态", "description": "风险处理状态（枚举：新发现/分析中/缓解中/已解决/已忽略）", "required": False},
        {"field_id": "assigned_to", "data_type": "string", "name": "负责人", "required": False, "description": "负责人（处理该风险的责任人）", "is_enum": True, "enum_values": ["活跃", "暂停", "关闭"]},
        {"field_id": "mitigation_plan", "data_type": "text", "name": "缓解计划", "required": False, "description": "缓解计划（应对措施说明）"},
        {"field_id": "resolved_at", "data_type": "datetime", "name": "解决时间", "required": False, "description": "解决时间"},
        {"field_id": "confidence_score", "data_type": "float", "name": "AI置信度", "description": "AI分析置信度（0.0-1.0，越高越可信）", "required": False},
        {"field_id": "keywords", "data_type": "array", "name": "关键词", "description": "关键词列表", "required": False},
        {"field_id": "raw_content", "data_type": "text", "name": "原始舆情内容", "required": False, "description": "原始舆情内容（完整新闻/报告文本）"},
        {"field_id": "created_at", "data_type": "datetime", "name": "创建时间", "required": False, "description": "记录创建时间"},
        {"field_id": "updated_at", "data_type": "datetime", "name": "更新时间", "required": False, "description": "记录更新时间"}
    ],    
    "supplier_risk_association": [
        {"field_id": "id", "data_type": "integer", "name": "自增ID", "required": True,  "description": "唯一标识符（主键）"},
        {"field_id": "supplier_id", "data_type": "string", "name": "供应商ID", "required": True,  "description": "供应商唯一标识符"},
        {"field_id": "risk_id", "data_type": "string", "name": "风险ID", "required": True,  "description": "风险事件唯一标识符"},
        {"field_id": "association_type", "data_type": "string", "name": "关联类型", "description": "关联类型（枚举：直接/间接/潜在）", "required": False},
        {"field_id": "impact_level", "data_type": "string", "name": "影响程度", "description": "影响程度（枚举：严重/高/中/低）", "required": False},
        {"field_id": "note", "data_type": "text", "name": "备注", "required": False,  "description": "备注说明", "is_enum": True, "enum_values": ["直接", "间接", "潜在"]},
		{"field_id": "created_at", "data_type": "datetime", "name": "创建时间", "required": False, "description": "记录创建时间"},
    ],
}

# ==================== 66个完整关系定义 ====================

BUSINESS_MODEL_LINKS = [
    # ========== 主数据域关系（9个）==========
    # 1. 产品 → 工艺路线 (1:N)
    {
        "id": "R1_has_route",
        "name": "产品定义工艺路线",
        "description": "产品对应的工艺路线定义（支持多版本）",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "process_route",
        "target_key": "product_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetProcessRoute",
        "target_api_name": "GetProduct"
    },
    # 2. 工艺路线 → 工序 (1:N)
    {
        "id": "R2_has_steps",
        "name": "工艺路线包含工序",
        "description": "一条工艺路线包含80-120道工序",
        "source_model": "process_route",
        "source_key": "route_id",
        "target_model": "route_step",
        "target_key": "route_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetRouteSteps",
        "target_api_name": "GetProcessRoute"
    },
    # 3. 产品 ↔ 物料 N:N（通过BOM中间表）
    {
        "id": "R3_has_bom",
        "name": "产品物料组成",
        "description": "产品由哪些物料组成及用量",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "material",
        "target_key": "material_id",
        "cardinality": "many-to-many",
        "intermediate_model": "bom",
        "intermediate_source_key": "product_id",
        "intermediate_target_key": "material_id",
        "source_api_name": "GetMaterial",
        "target_api_name": "GetProduct"
    },
    # 3.1 产品 → BOM (1:N)
    {
        "id": "R3_1_product_has_bom",
        "name": "产品BOM组成明细",
        "description": "产品的BOM组成明细",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "bom",
        "target_key": "product_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetBomDetails",
        "target_api_name": "GetProduct"
    },
    # 3.2 BOM → 物料 (N:1)
    {
        "id": "R3_2_bom_has_material",
        "name": "BOM对应物料",
        "description": "BOM明细对应的物料",
        "source_model": "bom",
        "source_key": "material_id",
        "target_model": "material",
        "target_key": "material_id",
        "cardinality": "many-to-one",
        "source_api_name": "GetMaterial",
        "target_api_name": "GetBom"
    },
    # 3.3 工序 → BOM (1:N)
    {
        "id": "R3_3_step_has_bom",
        "name": "工序消耗物料",
        "description": "工序消耗的物料BOM",
        "source_model": "route_step",
        "source_key": "step_id",
        "target_model": "bom",
        "target_key": "step_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetBomDetails",
        "target_api_name": "GetRouteStep"
    },
    # 4. 机台 → 工作中心 (N:1)
    {
        "id": "R4_belongs_to",
        "name": "机台所属工作中心",
        "description": "每台机台属于一个工作中心",
        "source_model": "machine",
        "source_key": "work_center_id",
        "target_model": "work_center",
        "target_key": "work_center_id",
        "cardinality": "many-to-one",
        "source_api_name": "GetMachineStatus",
        "target_api_name": "GetWorkCenter"
    },
    # 5. 机台 ↔ 产品 N:N（通过能力矩阵中间表）
    {
        "id": "R5_capable_of",
        "name": "机台可加工产品",
        "description": "机台能生产哪些产品及效率",
        "source_model": "machine",
        "source_key": "machine_id",
        "target_model": "product",
        "target_key": "product_id",
        "cardinality": "many-to-many",
        "intermediate_model": "machine_capability",
        "intermediate_source_key": "machine_id",
        "intermediate_target_key": "product_id",
        "source_api_name": "GetProduct",
        "target_api_name": "GetMachine"
    },
    # 5.1 机台 → 能力矩阵 (1:N)
    {
        "id": "R5_1_machine_has_capability",
        "name": "机台产品能力配置",
        "description": "机台的产品能力配置",
        "source_model": "machine",
        "source_key": "machine_id",
        "target_model": "machine_capability",
        "target_key": "machine_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMachineCapabilities",
        "target_api_name": "GetMachine"
    },
    # 5.2 产品 → 能力矩阵 (1:N)
    {
        "id": "R5_2_product_has_capability",
        "name": "产品可被机台加工",
        "description": "产品可在哪些机台生产",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "machine_capability",
        "target_key": "product_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMachineCapabilities",
        "target_api_name": "GetProduct"
    },
    # 6. 产品 ↔ 产品 N:N（通过换线矩阵中间表）
    {
        "id": "R6_setup_between",
        "name": "产品切换需换线",
        "description": "产品A切换到产品B需要的换线时间",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "product",
        "target_key": "product_id",
        "cardinality": "many-to-many",
        "intermediate_model": "setup_matrix",
        "intermediate_source_key": "from_product_id",
        "intermediate_target_key": "to_product_id",
        "source_api_name": "GetProduct",
        "target_api_name": "GetProduct"
    },
    # 6.1 机台 → 换线矩阵 (1:N)
    {
        "id": "R6_1_machine_has_setup",
        "name": "机台换线配置",
        "description": "机台的产品换线时间配置",
        "source_model": "machine",
        "source_key": "machine_id",
        "target_model": "setup_matrix",
        "target_key": "machine_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetSetupMatrix",
        "target_api_name": "GetMachine"
    },
    # 6.2 产品 → 换线矩阵(切换前) (1:N)
    {
        "id": "R6_2_product_from_setup",
        "name": "产品切换前需换线",
        "description": "产品作为切换前对象的换线时间",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "setup_matrix",
        "target_key": "from_product_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetSetupMatrix",
        "target_api_name": "GetProduct"
    },
    # 6.3 产品 → 换线矩阵(切换后) (1:N)
    {
        "id": "R6_3_product_to_setup",
        "name": "产品切换后需换线",
        "description": "产品作为切换后对象的换线时间",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "setup_matrix",
        "target_key": "to_product_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetSetupMatrix",
        "target_api_name": "GetProduct"
    },
    # 7. 供应商 ↔ 物料 N:N（通过供应商物料关系中间表）
    {
        "id": "R7_supplies",
        "name": "供应商可供应物料",
        "description": "供应商能供应哪些物料及价格、交期",
        "source_model": "supplier",
        "source_key": "supplier_id",
        "target_model": "material",
        "target_key": "material_id",
        "cardinality": "many-to-many",
        "intermediate_model": "supplier_material",
        "intermediate_source_key": "supplier_id",
        "intermediate_target_key": "material_id",
        "source_api_name": "GetMaterial",
        "target_api_name": "GetSupplier"
    },
    # 7.1 供应商 → 供应商物料 (1:N)
    {
        "id": "R7_1_supplier_has_material",
        "name": "供应商物料清单",
        "description": "供应商能供应的物料清单",
        "source_model": "supplier",
        "source_key": "supplier_id",
        "target_model": "supplier_material",
        "target_key": "supplier_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetSupplierMaterials",
        "target_api_name": "GetSupplier"
    },
    # 7.2 物料 → 供应商物料 (1:N)
    {
        "id": "R7_2_material_has_supplier",
        "name": "物料可选供应商",
        "description": "物料可由哪些供应商供应",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "supplier_material",
        "target_key": "material_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetSupplierMaterials",
        "target_api_name": "GetMaterial"
    },
    # 8. 物料 ↔ 物料 N:N（通过替代关系中间表）
    {
        "id": "R8_substitutes",
        "name": "物料可用替代料",
        "description": "物料缺料时可用哪些替代料",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "material",
        "target_key": "material_id",
        "cardinality": "many-to-many",
        "intermediate_model": "material_substitute",
        "intermediate_source_key": "material_id",
        "intermediate_target_key": "substitute_material_id",
        "source_api_name": "GetMaterial",
        "target_api_name": "GetMaterial"
    },
    # 8.1 物料 → 替代关系(原物料) (1:N)
    {
        "id": "R8_1_material_has_substitute",
        "name": "物料替代清单",
        "description": "物料的可用替代料",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "material_substitute",
        "target_key": "material_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMaterialSubstitutes",
        "target_api_name": "GetMaterial"
    },
    # 8.2 物料 → 替代关系(替代物料) (1:N)
    {
        "id": "R8_2_material_is_substitute",
        "name": "物料可作为替代料",
        "description": "物料可作为哪些物料的替代料",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "material_substitute",
        "target_key": "substitute_material_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMaterialSubstitutes",
        "target_api_name": "GetMaterial"
    },
    
    # ========== 客户域关系（5个）==========
    # 8.5 客户 → 客户产品关系 (1:N)
    {
        "id": "R8_5_customer_has_products",
        "name": "客户可购产品清单",
        "description": "客户可购买的产品清单及特定价格、交期",
        "source_model": "customer",
        "source_key": "customer_id",
        "target_model": "customer_product",
        "target_key": "customer_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetCustomerProducts",
        "target_api_name": "GetCustomer"
    },
    # 8.6 客户产品关系 → 产品 (N:1)
    {
        "id": "R8_6_cp_to_product",
        "name": "客户产品关联产品",
        "description": "客户产品关系关联的产品",
        "source_model": "customer_product",
        "source_key": "product_id",
        "target_model": "product",
        "target_key": "product_id",
        "cardinality": "many-to-one",
        "source_api_name": "GetProduct",
        "target_api_name": "GetCustomerProduct"
    },
    # 8.7 客户 → 客户订单 (1:N)
    {
        "id": "R8_7_customer_has_orders",
        "name": "客户采购订单",
        "description": "客户的所有采购订单",
        "source_model": "customer",
        "source_key": "customer_id",
        "target_model": "customer_order",
        "target_key": "customer_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetCustomerOrders",
        "target_api_name": "GetCustomer"
    },
    # 8.8 客户订单 → 产品 (N:1)
    {
        "id": "R8_8_order_to_product",
        "name": "订单订购产品",
        "description": "订单订购的产品",
        "source_model": "customer_order",
        "source_key": "product_id",
        "target_model": "product",
        "target_key": "product_id",
        "cardinality": "many-to-one",
        "source_api_name": "GetProduct",
        "target_api_name": "GetCustomerOrder"
    },
    # 8.9 客户产品关系 → 客户订单 (1:N) （间接关系：客户购买的产品才能下订单）
    {
        "id": "R8_9_cp_validates_order",
        "name": "客户产品验证订单",
        "description": "客户只能订购其产品信息表中定义的产品",
        "source_model": "customer_product",
        "source_key": "id",
        "target_model": "customer_order",
        "target_key": "customer_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetCustomerOrders",
        "target_api_name": "GetCustomerProduct"
    },
    
    # ========== 计划域关系（6个）==========
    # 9. 客户订单 → 工单 (1:1)
    {
        "id": "R9_generates_wo",
        "name": "订单生成工单",
        "description": "每个客户订单生成一个工单",
        "source_model": "customer_order",
        "source_key": "order_id",
        "target_model": "work_order",
        "target_key": "customer_order_id",
        "cardinality": "one-to-one",
        "source_api_name": "GetWorkOrder",
        "target_api_name": "GetCustomerOrder"
    },
    # 9.1 产品 → 客户订单 (1:N)
    {
        "id": "R9_1_product_has_orders",
        "name": "产品被客户订购",
        "description": "产品被哪些客户订单订购",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "customer_order",
        "target_key": "product_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetCustomerOrders",
        "target_api_name": "GetProduct"
    },
    # 10. 工单 → 工单工序 (1:N)
    {
        "id": "R10_has_operations",
        "name": "工单包含工序",
        "description": "工单包含多个工序（从工艺路线展开）",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "work_order_operation",
        "target_key": "work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWorkOrderOperations",
        "target_api_name": "GetWorkOrder"
    },
    # 10.1 产品 → 工单 (1:N)
    {
        "id": "R10_1_product_has_work_orders",
        "name": "产品生成工单",
        "description": "产品对应的生产工单",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "work_order",
        "target_key": "product_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWorkOrders",
        "target_api_name": "GetProduct"
    },
    # 10.2 工序 → 工单 (1:N)
    {
        "id": "R10_2_step_has_work_orders",
        "name": "工序执行工单",
        "description": "工序当前正在执行的工单",
        "source_model": "route_step",
        "source_key": "step_id",
        "target_model": "work_order",
        "target_key": "current_step_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWorkOrders",
        "target_api_name": "GetRouteStep"
    },
    # 10.3 工单 → 工单物料 (1:N)
    {
        "id": "R10_3_wo_has_materials",
        "name": "工单物料需求",
        "description": "工单需要的物料清单",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "work_order_material",
        "target_key": "work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWorkOrderMaterials",
        "target_api_name": "GetWorkOrder"
    },
    
    # ========== 执行域关系（8个）==========
    # 10.4 工序 → 工单工序 (1:N)
    {
        "id": "R10_4_step_has_wo_operations",
        "name": "工序实例化工单工序",
        "description": "工序定义对应的工单工序实例",
        "source_model": "route_step",
        "source_key": "step_id",
        "target_model": "work_order_operation",
        "target_key": "step_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWorkOrderOperations",
        "target_api_name": "GetRouteStep"
    },
    # 11. 工单工序 ↔ 物料 N:N（通过工单物料中间表）
    {
        "id": "R11_requires_material",
        "name": "工序物料需求",
        "description": "工序需要哪些物料及需求量",
        "source_model": "work_order_operation",
        "source_key": "wo_op_id",
        "target_model": "material",
        "target_key": "material_id",
        "cardinality": "many-to-many",
        "intermediate_model": "work_order_material",
        "intermediate_source_key": "wo_op_id",
        "intermediate_target_key": "material_id",
        "source_api_name": "GetMaterial",
        "target_api_name": "GetWorkOrderOperation"
    },
    # 11.1 工单工序 → 工单物料 (1:N)
    {
        "id": "R11_1_wo_op_has_materials",
        "name": "工单工序需求物料",
        "description": "工单工序需要的物料",
        "source_model": "work_order_operation",
        "source_key": "wo_op_id",
        "target_model": "work_order_material",
        "target_key": "wo_op_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWorkOrderMaterials",
        "target_api_name": "GetWorkOrderOperation"
    },
    # 12. 工单工序 ↔ 机台 N:N（通过生产任务中间表）
    {
        "id": "R12_executed_by",
        "name": "工序分配机台执行",
        "description": "工序分配到哪台机台执行（N:N关系）",
        "source_model": "work_order_operation",
        "source_key": "wo_op_id",
        "target_model": "machine",
        "target_key": "machine_id",
        "cardinality": "many-to-many",
        "intermediate_model": "production_task",
        "intermediate_source_key": "wo_op_id",
        "intermediate_target_key": "machine_id",
        "source_api_name": "GetMachine",
        "target_api_name": "GetWorkOrderOperation"
    },
    # 12.1 工单工序 → 生产任务 (1:N)
    {
        "id": "R12_1_wo_op_has_tasks",
        "name": "工序分解生产任务",
        "description": "工单工序分解的生产任务",
        "source_model": "work_order_operation",
        "source_key": "wo_op_id",
        "target_model": "production_task",
        "target_key": "wo_op_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetProductionTasks",
        "target_api_name": "GetWorkOrderOperation"
    },
    # 12.2 工单 → 生产任务 (1:N)
    {
        "id": "R12_2_wo_has_tasks",
        "name": "工单包含生产任务",
        "description": "工单包含的所有生产任务",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "production_task",
        "target_key": "work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetProductionTasks",
        "target_api_name": "GetWorkOrder"
    },
    # 12.3 机台 → 生产任务 (1:N)
    {
        "id": "R12_3_machine_has_tasks",
        "name": "机台执行生产任务",
        "description": "机台执行的生产任务",
        "source_model": "machine",
        "source_key": "machine_id",
        "target_model": "production_task",
        "target_key": "machine_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetProductionTasks",
        "target_api_name": "GetMachine"
    },
    # 13. 工单 → 在制品批次 (1:N)
    {
        "id": "R13_tracks_lot",
        "name": "工单拆分批次",
        "description": "工单拆分为多个Lot批次（每25片一批）",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "wip_lot",
        "target_key": "work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWipLot",
        "target_api_name": "GetWorkOrder"
    },
    # 13.1 产品 → 在制品批次 (1:N)
    {
        "id": "R13_1_product_has_lots",
        "name": "产品在制品批次",
        "description": "产品的在制品批次",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "wip_lot",
        "target_key": "product_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWipLots",
        "target_api_name": "GetProduct"
    },
    # 13.2 工序 → 在制品批次 (1:N)
    {
        "id": "R13_2_step_has_lots",
        "name": "工序在制品批次",
        "description": "工序当前正在加工的批次",
        "source_model": "route_step",
        "source_key": "step_id",
        "target_model": "wip_lot",
        "target_key": "current_step_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWipLots",
        "target_api_name": "GetRouteStep"
    },
    # 13.3 机台 → 在制品批次 (1:N)
    {
        "id": "R13_3_machine_has_lots",
        "name": "机台加工在制品",
        "description": "机台正在加工的批次",
        "source_model": "machine",
        "source_key": "machine_id",
        "target_model": "wip_lot",
        "target_key": "current_machine_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWipLots",
        "target_api_name": "GetMachine"
    },
    # 13.4 批次 → 生产任务 (1:N)
    {
        "id": "R13_4_lot_has_tasks",
        "name": "批次对应生产任务",
        "description": "批次对应的生产任务",
        "source_model": "wip_lot",
        "source_key": "lot_id",
        "target_model": "production_task",
        "target_key": "lot_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetProductionTasks",
        "target_api_name": "GetWipLot"
    },
    # 13.5 班次 → 生产任务 (1:N)
    {
        "id": "R13_5_shift_has_tasks",
        "name": "班次生产任务安排",
        "description": "班次内的生产任务",
        "source_model": "shift_pattern",
        "source_key": "shift_id",
        "target_model": "production_task",
        "target_key": "shift_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetProductionTasks",
        "target_api_name": "GetShiftPattern"
    },
    
    # ========== 库存域关系（5个）==========
    # 14. 物料 → 原材料库存 (1:1)
    {
        "id": "R14_has_inventory",
        "name": "物料实时库存",
        "description": "物料的实时库存状态",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "inventory",
        "target_key": "material_id",
        "cardinality": "one-to-one",
        "source_api_name": "GetInventory",
        "target_api_name": "GetMaterial"
    },
    # 15. 产品 → 成品库存 (1:1)
    {
        "id": "R15_has_fg_inventory",
        "name": "产品成品库存",
        "description": "产品的成品库存状态",
        "source_model": "product",
        "source_key": "product_id",
        "target_model": "finished_goods_inventory",
        "target_key": "product_id",
        "cardinality": "one-to-one",
        "source_api_name": "GetFinishedGoodsInventory",
        "target_api_name": "GetProduct"
    },
    # 16. 工单物料 ↔ 采购订单 N:N（通过采购订单行中间表）
    {
        "id": "R16_triggers_po",
        "name": "物料缺料触发采购",
        "description": "物料缺料触发采购订单",
        "source_model": "work_order_material",
        "source_key": "wom_id",
        "target_model": "purchase_order",
        "target_key": "po_id",
        "cardinality": "many-to-many",
        "intermediate_model": "purchase_order_line",
        "intermediate_source_key": "related_wom_id",
        "intermediate_target_key": "po_id",
        "source_api_name": "GetPurchaseOrder",
        "target_api_name": "GetWorkOrderMaterial"
    },
    # 16.1 采购订单 → 采购订单行 (1:N)
    {
        "id": "R16_1_po_has_lines",
        "name": "采购订单包含采购行",
        "description": "采购订单的物料明细行",
        "source_model": "purchase_order",
        "source_key": "po_id",
        "target_model": "purchase_order_line",
        "target_key": "po_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetPurchaseOrderLines",
        "target_api_name": "GetPurchaseOrder"
    },
    # 16.2 工单 → 采购订单行 (1:N)
    {
        "id": "R16_2_wo_has_po_line",
        "name": "工单关联采购行",
        "description": "工单关联的采购订单行",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "purchase_order_line",
        "target_key": "related_work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetPurchaseOrderLines",
        "target_api_name": "GetWorkOrder"
    },
    # 16.3 物料 → 采购订单行 (1:N)
    {
        "id": "R16_3_material_has_po_lines",
        "name": "物料被采购行订购",
        "description": "物料的采购订单行",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "purchase_order_line",
        "target_key": "material_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetPurchaseOrderLines",
        "target_api_name": "GetMaterial"
    },
    # 16.4 工单物料 → 采购订单行 (1:N)
    {
        "id": "R16_4_wom_has_po_lines",
        "name": "物料需求触发采购行",
        "description": "工单物料需求触发的采购订单行",
        "source_model": "work_order_material",
        "source_key": "wom_id",
        "target_model": "purchase_order_line",
        "target_key": "related_wom_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetPurchaseOrderLines",
        "target_api_name": "GetWorkOrderMaterial"
    },
    
    # ========== 质量域关系（6个）==========
    # 17. 工单工序 → 质量检验 (1:N) 【修正：原为production_task→quality_inspection】
    {
        "id": "R17_triggers_inspection",
        "name": "生产任务触发检验",
        "description": "工单工序完成后触发质量检验",
        "source_model": "work_order_operation",
        "source_key": "wo_op_id",
        "target_model": "quality_inspection",
        "target_key": "wo_op_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetQualityInspection",
        "target_api_name": "GetWorkOrderOperation"
    },
    # 17.1 工单工序 → 质量检验 (1:N) [重复确认]
    {
        "id": "R17_1_wo_op_has_inspections",
        "name": "工单工序质量检验",
        "description": "工单工序的质量检验记录",
        "source_model": "work_order_operation",
        "source_key": "wo_op_id",
        "target_model": "quality_inspection",
        "target_key": "wo_op_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetQualityInspections",
        "target_api_name": "GetWorkOrderOperation"
    },
    # 17.2 批次 → 质量检验 (1:N)
    {
        "id": "R17_2_lot_has_inspections",
        "name": "批次质量检验",
        "description": "批次的质量检验记录",
        "source_model": "wip_lot",
        "source_key": "lot_id",
        "target_model": "quality_inspection",
        "target_key": "lot_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetQualityInspections",
        "target_api_name": "GetWipLot"
    },
    # 17.3 机台 → 质量检验 (1:N)
    {
        "id": "R17_3_machine_has_inspections",
        "name": "机台加工质量检验",
        "description": "机台相关的检验记录",
        "source_model": "machine",
        "source_key": "machine_id",
        "target_model": "quality_inspection",
        "target_key": "machine_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetQualityInspections",
        "target_api_name": "GetMachine"
    },
    # 17.4 采购订单 → 质量检验 (1:N)
    {
        "id": "R17_4_po_has_inspections",
        "name": "采购订单来料检验",
        "description": "采购订单的来料检验记录",
        "source_model": "purchase_order",
        "source_key": "po_id",
        "target_model": "quality_inspection",
        "target_key": "po_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetQualityInspections",
        "target_api_name": "GetPurchaseOrder"
    },
    # 17.5 物料 → 质量检验 (1:N)
    {
        "id": "R17_5_material_has_inspections",
        "name": "物料质量检验",
        "description": "物料的质量检验记录",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "quality_inspection",
        "target_key": "material_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetQualityInspections",
        "target_api_name": "GetMaterial"
    },
    
    # ========== 采购与供应商域关系（2个）==========
    # 17.6 供应商 → 采购订单 (1:N)
    {
        "id": "R17_6_supplier_has_orders",
        "name": "供应商接收采购订单",
        "description": "供应商的采购订单",
        "source_model": "supplier",
        "source_key": "supplier_id",
        "target_model": "purchase_order",
        "target_key": "supplier_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetPurchaseOrders",
        "target_api_name": "GetSupplier"
    },
    
    # ========== 库存事务与调拨域关系（5个）==========
    # 17.7 物料 → 库存事务 (1:N)
    {
        "id": "R17_7_material_has_transactions",
        "name": "物料库存流水",
        "description": "物料的库存变动记录",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "inventory_transaction",
        "target_key": "material_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetInventoryTransactions",
        "target_api_name": "GetMaterial"
    },
    # 17.8 工单 → 库存事务(调出) (1:N)
    {
        "id": "R17_8_wo_from_transactions",
        "name": "工单库存调出",
        "description": "工单作为调出方的库存事务",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "inventory_transaction",
        "target_key": "from_work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetInventoryTransactions",
        "target_api_name": "GetWorkOrder"
    },
    # 17.9 工单 → 库存事务(调入) (1:N)
    {
        "id": "R17_9_wo_to_transactions",
        "name": "工单库存调入",
        "description": "工单作为调入方的库存事务",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "inventory_transaction",
        "target_key": "to_work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetInventoryTransactions",
        "target_api_name": "GetWorkOrder"
    },
    # 17.10 工单物料 → 物料调拨(调出) (1:N)
    {
        "id": "R17_10_wom_from_transfers",
        "name": "工单物料需求调出",
        "description": "工单物料需求作为调出方",
        "source_model": "work_order_material",
        "source_key": "wom_id",
        "target_model": "material_transfer",
        "target_key": "from_wom_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMaterialTransfers",
        "target_api_name": "GetWorkOrderMaterial"
    },
    # 17.11 工单物料 → 物料调拨(调入) (1:N)
    {
        "id": "R17_11_wom_to_transfers",
        "name": "工单物料需求调入",
        "description": "工单物料需求作为调入方",
        "source_model": "work_order_material",
        "source_key": "wom_id",
        "target_model": "material_transfer",
        "target_key": "to_wom_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMaterialTransfers",
        "target_api_name": "GetWorkOrderMaterial"
    },
    
    # ========== 工作日历与排程域关系（6个）==========
    # 17.12 工作中心 → 工作日历 (1:N)
    {
        "id": "R17_12_workcenter_has_calendar",
        "name": "工作中心班次安排",
        "description": "工作中心的每日班次安排",
        "source_model": "work_center",
        "source_key": "work_center_id",
        "target_model": "work_calendar",
        "target_key": "work_center_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWorkCalendar",
        "target_api_name": "GetWorkCenter"
    },
    # 17.13 班次 → 工作日历 (1:N)
    {
        "id": "R17_13_shift_has_calendar",
        "name": "班次日历安排",
        "description": "班次的日历安排",
        "source_model": "shift_pattern",
        "source_key": "shift_id",
        "target_model": "work_calendar",
        "target_key": "shift_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetWorkCalendar",
        "target_api_name": "GetShiftPattern"
    },
    # 17.14 机台 → 排程汇总 (1:N)
    {
        "id": "R17_14_machine_has_schedule",
        "name": "机台产能负荷统计",
        "description": "机台的每日产能负荷统计",
        "source_model": "machine",
        "source_key": "machine_id",
        "target_model": "schedule",
        "target_key": "bottleneck_machine_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetSchedule",
        "target_api_name": "GetMachine"
    },
    # 17.15 工作中心 → 排程汇总 (1:N)
    {
        "id": "R17_15_workcenter_has_schedule",
        "name": "工作中心产能负荷统计",
        "description": "工作中心的每日产能负荷统计",
        "source_model": "work_center",
        "source_key": "work_center_id",
        "target_model": "schedule",
        "target_key": "bottleneck_work_center_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetSchedule",
        "target_api_name": "GetWorkCenter"
    },
    # 17.16 物料 → 物料调拨 (1:N)
    {
        "id": "R17_16_material_has_transfer",
        "name": "物料工间调拨",
        "description": "物料的工间调拨记录",
        "source_model": "material",
        "source_key": "material_id",
        "target_model": "material_transfer",
        "target_key": "material_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMaterialTransfers",
        "target_api_name": "GetMaterial"
    },
    # 17.17 工单 → 物料调拨(调出) (1:N)
    {
        "id": "R17_17_wo_from_transfer",
        "name": "工单作为调出方",
        "description": "工单作为调出方的物料调拨",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "material_transfer",
        "target_key": "from_work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMaterialTransfers",
        "target_api_name": "GetWorkOrder"
    },
    # 17.18 工单 → 物料调拨(调入) (1:N)
    {
        "id": "R17_18_wo_to_transfer",
        "name": "工单作为调入方",
        "description": "工单作为调入方的物料调拨",
        "source_model": "work_order",
        "source_key": "work_order_id",
        "target_model": "material_transfer",
        "target_key": "to_work_order_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMaterialTransfers",
        "target_api_name": "GetWorkOrder"
    },
    
    # ========== 监控域关系（2个）==========
    # R30 机台 → 机台状态日志 (1:N)
    {
        "id": "R30_machine_has_status_log",
        "name": "机台运行状态记录",
        "description": "机台的状态变迁记录（运行、停机、维护、故障），用于OEE分析",
        "source_model": "machine",
        "source_key": "machine_id",
        "target_model": "machine_status_log",
        "target_key": "machine_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetMachineStatusLogs",
        "target_api_name": "GetMachine"
    },
    # R31 产品 → 机台状态日志 (1:N) （可选关系，日志中可能记录生产的产品）
    {
        "id": "R31_product_in_status_log",
        "name": "机台日志生产产品",
        "description": "机台状态日志中记录的生产产品",
        "source_model": "machine_status_log",
        "source_key": "product_id",
        "target_model": "product",
        "target_key": "product_id",
        "cardinality": "many-to-one",
        "source_api_name": "GetProduct",
        "target_api_name": "GetMachineStatusLog"
    },
    # R32 供应商 → 外部供应链风险 (1:N)
    {
        "id": "R32_supplier_has_risk",
        "name": "供应商遭遇风险事件",
        "description": "供应商作为主要受影响方的风险事件",
        "source_model": "supplier",
        "source_key": "supplier_id",
        "target_model": "external_supply_chain_risk",
        "target_key": "supplier_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetExternalSupplyChainRisks",
        "target_api_name": "GetSupplier"
    },
    # R33 客户 → 外部供应链风险 (1:N)
    {
        "id": "R33_customer_has_risk",
        "name": "客户遭遇风险事件",
        "description": "客户关联的外部风险事件（需求变化、财务危机、行业政策等）",
        "source_model": "customer",
        "source_key": "customer_id",
        "target_model": "external_supply_chain_risk",
        "target_key": "customer_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetExternalSupplyChainRisks",
        "target_api_name": "GetCustomer"
    },
    # R34 供应商 → 供应商风险关联 (1:N)
    {
        "id": "R34_supplier_risk_link",
        "name": "供应商风险关联清单",
        "description": "供应商与风险事件的波及影响链（支持direct/indirect/potential三种关联类型）。用于查询供应商受哪些风险波及，及其影响程度",
        "source_model": "supplier",
        "source_key": "supplier_id",
        "target_model": "supplier_risk_association",
        "target_key": "supplier_id",
        "cardinality": "one-to-many",
        "source_api_name": "GetSupplierRiskAssociations",
        "target_api_name": "GetSupplier"
    },
]


# ==================== 导入脚本核心逻辑 ====================

class OntologyImporter:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip('/')
        # 添加/api/v1前缀
        if not self.api_url.endswith('/api/v1'):
            self.api_url = f"{self.api_url}/api/v1"
        self.session = requests.Session()
        self.stats = {
            "models": {"success": 0, "failed": 0, "errors": []},
            "fields": {"success": 0, "failed": 0, "errors": []},
            "links": {"success": 0, "failed": 0, "errors": []}
        }
    
    def clear_all_data(self):
        """清空所有本体数据（关系 → 模型，字段会级联删除）"""
        print(f"\n{'='*60}")
        print(f"🗑️  开始清空现有数据...")
        print(f"{'='*60}\n")
        
        # 步骤1: 清空所有关系
        print("📝 步骤1: 清空所有关系...")
        try:
            response = self.session.get(f"{self.api_url}/business-model-links")
            if response.status_code == 200:
                links = response.json()
                if isinstance(links, list):
                    deleted_count = 0
                    for link in links:
                        link_id = link.get('id')
                        if link_id:
                            del_response = self.session.delete(f"{self.api_url}/business-model-links/{link_id}")
                            if del_response.status_code in [200, 204]:
                                deleted_count += 1
                    print(f"  ✅ 已删除 {deleted_count} 个关系")
                else:
                    print(f"  ⚠️  关系数据格式异常")
            else:
                print(f"  ⚠️  获取关系列表失败: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 清空关系失败: {str(e)}")
        
        # 步骤2: 清空所有模型（字段会级联删除）
        print("\n📝 步骤2: 清空所有模型（字段将级联删除）...")
        try:
            response = self.session.get(f"{self.api_url}/business-models")
            if response.status_code == 200:
                models = response.json()
                if isinstance(models, list):
                    deleted_count = 0
                    failed_count = 0
                    for model in models:
                        model_id = model.get('id')
                        if model_id:
                            del_response = self.session.delete(f"{self.api_url}/business-models/{model_id}")
                            if del_response.status_code in [200, 204]:
                                deleted_count += 1
                            else:
                                failed_count += 1
                                print(f"  ❌ 删除模型 {model_id} 失败: {del_response.status_code}")
                    print(f"  ✅ 已删除 {deleted_count} 个模型")
                    if failed_count > 0:
                        print(f"  ❌ 删除失败 {failed_count} 个模型")
                else:
                    print(f"  ⚠️  模型数据格式异常")
            else:
                print(f"  ⚠️  获取模型列表失败: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 清空模型失败: {str(e)}")
        
        print(f"\n{'='*60}")
        print(f"✅ 数据清空完成")
        print(f"{'='*60}\n")
    
    def import_business_models(self):
        """导入所有业务模型（对象）"""
        print(f"\n{'='*60}")
        print(f"开始导入 {len(BUSINESS_MODELS)} 个业务模型...")
        print(f"{'='*60}\n")
        
        for idx, model in enumerate(BUSINESS_MODELS, 1):
            try:
                print(f"[{idx}/{len(BUSINESS_MODELS)}] 导入模型: {model['name']} ({model['id']})")
                
                # 创建新模型（不检查是否已存在，因为已经清空）
                response = self.session.post(
                    f"{self.api_url}/business-models",
                    json=model
                )
                
                if response.status_code in [200, 201]:
                    print(f"  ✅ 导入成功")
                    self.stats["models"]["success"] += 1
                else:
                    print(f"  ❌ 导入失败: {response.status_code} - {response.text}")
                    self.stats["models"]["failed"] += 1
                    self.stats["models"]["errors"].append({
                        "model_id": model['id'],
                        "error": response.text
                    })
                
            except Exception as e:
                print(f"  ❌ 导入异常: {str(e)}")
                self.stats["models"]["failed"] += 1
                self.stats["models"]["errors"].append({
                    "model_id": model['id'],
                    "error": str(e)
                })
    
    
    def import_fields(self):
        """导入所有字段定义"""
        session = self.session
        base_url = self.api_url  # self.api_url 已经包含 /api/v1 前缀
        
        total_fields = sum(len(fields) for fields in ALL_FIELDS.values())
        imported = 0
        failed = 0
        
        print(f"\n{'='*60}")
        print(f"开始导入 {len(ALL_FIELDS)} 个模型的字段定义...")
        print(f"总字段数: {total_fields}")
        print(f"{'='*60}\n")
        
        for model_id, fields in ALL_FIELDS.items():
            print(f"\n📦 模型: {model_id} ({len(fields)}个字段)")
            
            for field in fields:
                try:
                    # 创建字段
                    response = session.post(
                        f"{base_url}/business-models/{model_id}/fields",
                        json=field
                    )
                    
                    if response.status_code in [200, 201]:
                        print(f"  ✅ {field['field_id']}: {field['name']}")
                        imported += 1
                    else:
                        print(f"  ❌ {field['field_id']}: {response.status_code} - {response.text}")
                        failed += 1
                        
                except Exception as e:
                    print(f"  ❌ {field['field_id']}: 异常 - {str(e)}")
                    failed += 1
                    self.stats['fields']['errors'].append({
                        "field_id": field['field_id'],
                        "error": str(e)
                    })
        
        # 记录统计信息
        self.stats['fields']['success'] = imported
        self.stats['fields']['failed'] = failed


    def import_business_model_links(self):
        """导入所有业务模型关系"""
        print(f"\n{'='*60}")
        print(f"开始导入 {len(BUSINESS_MODEL_LINKS)} 个关系...")
        print(f"{'='*60}\n")
        
        for idx, link in enumerate(BUSINESS_MODEL_LINKS, 1):
            try:
                print(f"[{idx}/{len(BUSINESS_MODEL_LINKS)}] 导入关系: {link['name']} ({link['id']})")
                print(f"  {link['source_model']} → {link['target_model']} ({link['cardinality']})")
                
                # 创建新关系（不检查是否已存在，因为已经清空）
                response = self.session.post(
                    f"{self.api_url}/business-model-links",
                    json=link
                )
                
                if response.status_code in [200, 201]:
                    print(f"  ✅ 导入成功")
                    self.stats["links"]["success"] += 1
                else:
                    print(f"  ❌ 导入失败: {response.status_code} - {response.text}")
                    self.stats["links"]["failed"] += 1
                    self.stats["links"]["errors"].append({
                        "link_id": link['id'],
                        "error": response.text
                    })
                
            except Exception as e:
                print(f"  ❌ 导入异常: {str(e)}")
                self.stats["links"]["failed"] += 1
                self.stats["links"]["errors"].append({
                    "link_id": link['id'],
                    "error": str(e)
                })
    
    def _get_model(self, model_id: str) -> Dict:
        """获取已存在的模型"""
        try:
            response = self.session.get(f"{self.api_url}/business-models/{model_id}")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def _get_link(self, link_id: str) -> Dict:
        """获取已存在的关系"""
        try:
            response = self.session.get(f"{self.api_url}/business-model-links/{link_id}")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def print_summary(self):
        """打印导入汇总"""
        print(f"\n{'='*60}")
        print(f"导入完成汇总")
        print(f"{'='*60}")
        print(f"\n业务模型:")
        print(f"  ✅ 成功: {self.stats['models']['success']}")
        print(f"  ❌ 失败: {self.stats['models']['failed']}")
        if self.stats['models']['errors']:
            print(f"\n  错误详情:")
            for error in self.stats['models']['errors']:
                print(f"    - {error['model_id']}: {error['error']}")
        
        print(f"\n字段定义:")
        print(f"  ✅ 成功: {self.stats['fields']['success']}")
        print(f"  ❌ 失败: {self.stats['fields']['failed']}")
        if self.stats['fields']['errors']:
            print(f"\n  错误详情:")
            for error in self.stats['fields']['errors']:
                print(f"    - {error['field_id']}: {error['error']}")
        
        print(f"\n业务关系:")
        print(f"  ✅ 成功: {self.stats['links']['success']}")
        print(f"  ❌ 失败: {self.stats['links']['failed']}")
        if self.stats['links']['errors']:
            print(f"\n  错误详情:")
            for error in self.stats['links']['errors']:
                print(f"    - {error['link_id']}: {error['error']}")
        
        total_success = self.stats['models']['success'] + self.stats['fields']['success'] + self.stats['links']['success']
        total_failed = self.stats['models']['failed'] + self.stats['fields']['failed'] + self.stats['links']['failed']
        print(f"\n总计: {total_success} 成功, {total_failed} 失败")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='导入半导体供应链本体模型')
    parser.add_argument('--api-url', type=str, default='http://localhost:8080',
                       help='API基础URL (default: http://localhost:8080)')
    parser.add_argument('--no-clear', action='store_true',
                       help='不清空现有数据，直接导入（幂等模式）')
    parser.add_argument('--skip-models', action='store_true',
                       help='跳过模型导入，仅导入关系')
    parser.add_argument('--skip-links', action='store_true',
                       help='跳过关系导入，仅导入模型')
    
    args = parser.parse_args()
    
    print(f"\n🚀 开始导入半导体供应链本体模型")
    print(f"📡 API地址: {args.api_url}")
    
    importer = OntologyImporter(args.api_url)
    
    # 步骤0: 清空现有数据（默认行为）
    if not args.no_clear:
        importer.clear_all_data()
    
    # 步骤1: 导入业务模型和字段
    if not args.skip_models:
        importer.import_business_models()
        importer.import_fields()
    
    # 步骤2: 导入关系
    if not args.skip_links:
        importer.import_business_model_links()
    
    # 打印汇总
    importer.print_summary()
    
    # 返回退出码
    total_failed = importer.stats['models']['failed'] + importer.stats['links']['failed']
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
