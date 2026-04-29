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
        "description": "半导体封装测试产品定义（100个产品，10种封装×10种芯片）",
        "primary_key_id": "product_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "material",
        "api_name": "Material",
        "name": "物料",
        "description": "生产所需的原材料和辅料（Die、基板、EMC、键合线等）",
        "primary_key_id": "material_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "work_center",
        "api_name": "WorkCenter",
        "name": "工作中心",
        "description": "产能资源池（25个工作中心，按工序类型分组）",
        "primary_key_id": "work_center_id",
        "data_source_id": DATA_SOURCE_ID
    },
    {
        "id": "machine",
        "api_name": "Machine",
        "name": "机台设备",
        "description": "具体生产设备（96台），仿真核心资源",
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
        "description": "物料供应商（13个，5个主供+8个备选）",
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
        "description": "产品由哪些物料组成及用量（2-3层BOM）",
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
        "id": "customer_order",
        "api_name": "CustomerOrder",
        "name": "客户订单",
        "description": "市场需求输入，仿真中按泊松分布生成",
        "primary_key_id": "order_id",
        "data_source_id": DATA_SOURCE_ID
    },
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
        "description": "机台级别的任务执行记录，最细粒度",
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
    
    # 监控域 (2个)
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
]

# 所有对象的字段定义
ALL_FIELDS = {
    "product": [
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "product_name", "data_type": "VARCHAR(100)", "name": "产品名称"},
        {"field_id": "product_type", "data_type": "VARCHAR(50)", "name": "产品类型"},
        {"field_id": "standard_cycle_time", "data_type": "FLOAT", "name": "标准周期(小时)"},
        {"field_id": "routing_steps", "data_type": "INTEGER", "name": "工序数"},
        {"field_id": "setup_group", "data_type": "VARCHAR(50)", "name": "换线组"},
        {"field_id": "unit_of_measure", "data_type": "VARCHAR(20)", "name": "计量单位"},
        {"field_id": "is_active", "data_type": "BOOLEAN", "name": "是否激活"},
        {"field_id": "created_at", "data_type": "DATETIME", "name": "创建时间"},
    ],
    "material": [
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "material_name", "data_type": "VARCHAR(100)", "name": "物料名称"},
        {"field_id": "material_type", "data_type": "VARCHAR(50)", "name": "物料类型"},
        {"field_id": "unit_of_measure", "data_type": "VARCHAR(20)", "name": "计量单位"},
        {"field_id": "safety_stock_level", "data_type": "FLOAT", "name": "安全库存"},
        {"field_id": "reorder_point", "data_type": "FLOAT", "name": "Reorder点"},
        {"field_id": "lot_size", "data_type": "FLOAT", "name": "订购批量"},
        {"field_id": "eoq", "data_type": "FLOAT", "name": "经济订购量"},
        {"field_id": "annual_demand", "data_type": "FLOAT", "name": "年需求量"},
        {"field_id": "holding_cost_rate", "data_type": "FLOAT", "name": "持有成本率"},
        {"field_id": "is_active", "data_type": "BOOLEAN", "name": "是否激活"},
        {"field_id": "created_at", "data_type": "DATETIME", "name": "创建时间"},
    ],
    "work_center": [
        {"field_id": "work_center_id", "data_type": "VARCHAR(50)", "name": "工作中心ID"},
        {"field_id": "work_center_name", "data_type": "VARCHAR(100)", "name": "工作中心名称"},
        {"field_id": "work_center_type", "data_type": "VARCHAR(50)", "name": "类型"},
        {"field_id": "capacity_uom", "data_type": "VARCHAR(20)", "name": "产能单位"},
        {"field_id": "is_active", "data_type": "BOOLEAN", "name": "是否激活"},
    ],
    "machine": [
        {"field_id": "machine_id", "data_type": "VARCHAR(50)", "name": "机台ID"},
        {"field_id": "machine_name", "data_type": "VARCHAR(100)", "name": "机台名称"},
        {"field_id": "machine_type", "data_type": "VARCHAR(50)", "name": "机台类型"},
        {"field_id": "work_center_id", "data_type": "VARCHAR(50)", "name": "所属工作中心ID"},
        {"field_id": "max_capacity_per_hour", "data_type": "FLOAT", "name": "最大产能(片/小时)"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "current_product_id", "data_type": "VARCHAR(50)", "name": "当前生产产品ID"},
        {"field_id": "current_setup_group", "data_type": "VARCHAR(50)", "name": "当前换线组"},
        {"field_id": "last_maintenance_date", "data_type": "DATE", "name": "上次维护日期"},
        {"field_id": "next_maintenance_date", "data_type": "DATE", "name": "下次维护日期"},
        {"field_id": "is_active", "data_type": "BOOLEAN", "name": "是否启用"},
    ],
    "process_route": [
        {"field_id": "route_id", "data_type": "VARCHAR(50)", "name": "路线ID"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "route_name", "data_type": "VARCHAR(100)", "name": "路线名称"},
        {"field_id": "version", "data_type": "VARCHAR(20)", "name": "版本"},
        {"field_id": "is_active", "data_type": "BOOLEAN", "name": "是否激活"},
        {"field_id": "effective_date", "data_type": "DATE", "name": "生效日期"},
        {"field_id": "expiry_date", "data_type": "DATE", "name": "失效日期"},
    ],
    "route_step": [
        {"field_id": "step_id", "data_type": "VARCHAR(50)", "name": "工序ID"},
        {"field_id": "route_id", "data_type": "VARCHAR(50)", "name": "所属路线ID"},
        {"field_id": "sequence_no", "data_type": "INTEGER", "name": "工序序号"},
        {"field_id": "step_name", "data_type": "VARCHAR(100)", "name": "工序名称"},
        {"field_id": "operation_type", "data_type": "VARCHAR(50)", "name": "操作类型"},
        {"field_id": "standard_time_hours", "data_type": "FLOAT", "name": "标准工时(小时)"},
        {"field_id": "machine_type_required", "data_type": "VARCHAR(50)", "name": "所需工作中心ID"},
        {"field_id": "setup_time_minutes", "data_type": "INTEGER", "name": "换线时间(分钟)"},
        {"field_id": "material_ready_offset_hours", "data_type": "FLOAT", "name": "物料准备偏移(小时)"},
        {"field_id": "yield_rate_standard", "data_type": "FLOAT", "name": "标准良率"},
        {"field_id": "is_critical", "data_type": "BOOLEAN", "name": "是否关键工序"},
        {"field_id": "wait_time_hours", "data_type": "FLOAT", "name": "等待时间(小时)"},
        {"field_id": "transport_time_hours", "data_type": "FLOAT", "name": "转运时间(小时)"},
        {"field_id": "min_batch_qty", "data_type": "FLOAT", "name": "最小批量"},
        {"field_id": "max_batch_qty", "data_type": "FLOAT", "name": "最大批量"},
    ],
    "machine_capability": [
        {"field_id": "capability_id", "data_type": "VARCHAR(50)", "name": "能力ID"},
        {"field_id": "machine_id", "data_type": "VARCHAR(50)", "name": "机台ID"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "efficiency_factor", "data_type": "FLOAT", "name": "效率因子"},
        {"field_id": "setup_time_minutes", "data_type": "INTEGER", "name": "换线时间(分钟)"},
        {"field_id": "yield_rate", "data_type": "FLOAT", "name": "良率"},
        {"field_id": "is_preferred", "data_type": "BOOLEAN", "name": "是否首选"},
        {"field_id": "rated_speed_per_hour", "data_type": "FLOAT", "name": "额定速度(片/小时)"},
        {"field_id": "effective_date", "data_type": "DATE", "name": "生效日期"},
        {"field_id": "actual_efficiency_avg", "data_type": "FLOAT", "name": "实际效率均值"},
        {"field_id": "actual_yield_avg", "data_type": "FLOAT", "name": "实际良率均值"},
        {"field_id": "sample_count", "data_type": "INTEGER", "name": "样本数量"},
        {"field_id": "last_updated_at", "data_type": "DATETIME", "name": "最后更新时间"},
    ],
    "setup_matrix": [
        {"field_id": "matrix_id", "data_type": "VARCHAR(50)", "name": "矩阵ID"},
        {"field_id": "machine_id", "data_type": "VARCHAR(50)", "name": "机台ID"},
        {"field_id": "from_product_id", "data_type": "VARCHAR(50)", "name": "切换前产品ID"},
        {"field_id": "to_product_id", "data_type": "VARCHAR(50)", "name": "切换后产品ID"},
        {"field_id": "setup_time_minutes", "data_type": "INTEGER", "name": "换线时间(分钟)"},
        {"field_id": "setup_type", "data_type": "VARCHAR(50)", "name": "换线类型"},
        {"field_id": "is_active", "data_type": "BOOLEAN", "name": "是否激活"},
    ],
    "shift_pattern": [
        {"field_id": "shift_id", "data_type": "VARCHAR(50)", "name": "班次ID"},
        {"field_id": "shift_name", "data_type": "VARCHAR(50)", "name": "班次名称"},
        {"field_id": "start_time", "data_type": "VARCHAR(10)", "name": "开始时间"},
        {"field_id": "end_time", "data_type": "VARCHAR(10)", "name": "结束时间"},
        {"field_id": "available_hours", "data_type": "FLOAT", "name": "可用工时"},
        {"field_id": "efficiency_factor", "data_type": "FLOAT", "name": "效率因子"},
        {"field_id": "is_active", "data_type": "BOOLEAN", "name": "是否激活"},
    ],
    "supplier": [
        {"field_id": "supplier_id", "data_type": "VARCHAR(50)", "name": "供应商ID"},
        {"field_id": "supplier_name", "data_type": "VARCHAR(100)", "name": "供应商名称"},
        {"field_id": "supplier_type", "data_type": "VARCHAR(50)", "name": "供应类型"},
        {"field_id": "avg_lead_time_days", "data_type": "INTEGER", "name": "平均交期(天)"},
        {"field_id": "reliability_score", "data_type": "FLOAT", "name": "可靠度"},
        {"field_id": "min_order_quantity", "data_type": "FLOAT", "name": "最小订购量"},
        {"field_id": "lead_time_stddev_days", "data_type": "FLOAT", "name": "交期标准差"},
        {"field_id": "is_active", "data_type": "BOOLEAN", "name": "是否激活"},
    ],
    "supplier_material": [
        {"field_id": "sm_id", "data_type": "VARCHAR(50)", "name": "关系ID"},
        {"field_id": "supplier_id", "data_type": "VARCHAR(50)", "name": "供应商ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "unit_price", "data_type": "FLOAT", "name": "单价"},
        {"field_id": "lead_time_days", "data_type": "INTEGER", "name": "交期(天)"},
        {"field_id": "min_order_qty", "data_type": "FLOAT", "name": "最小订购量"},
        {"field_id": "is_preferred", "data_type": "BOOLEAN", "name": "是否首选供应商"},
        {"field_id": "effective_date", "data_type": "DATE", "name": "生效日期"},
        {"field_id": "expiry_date", "data_type": "DATE", "name": "失效日期"},
    ],
    "material_substitute": [
        {"field_id": "ms_id", "data_type": "VARCHAR(50)", "name": "替代关系ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "原物料ID"},
        {"field_id": "substitute_material_id", "data_type": "VARCHAR(50)", "name": "替代物料ID"},
        {"field_id": "substitute_priority", "data_type": "INTEGER", "name": "替代优先级"},
        {"field_id": "quality_grade", "data_type": "VARCHAR(50)", "name": "质量等级"},
        {"field_id": "approval_status", "data_type": "VARCHAR(50)", "name": "审批状态"},
        {"field_id": "cost_delta_percent", "data_type": "FLOAT", "name": "成本差异(%)"},
    ],
    "bom": [
        {"field_id": "bom_id", "data_type": "VARCHAR(50)", "name": "BOM ID"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "step_id", "data_type": "VARCHAR(50)", "name": "消耗工序ID"},
        {"field_id": "quantity_per_unit", "data_type": "FLOAT", "name": "单位用量"},
        {"field_id": "is_critical", "data_type": "BOOLEAN", "name": "是否关键物料"},
        {"field_id": "consumption_pattern", "data_type": "VARCHAR(50)", "name": "消耗模式"},
        {"field_id": "version", "data_type": "VARCHAR(20)", "name": "版本"},
        {"field_id": "effective_date", "data_type": "DATE", "name": "生效日期"},
        {"field_id": "expiry_date", "data_type": "DATE", "name": "失效日期"},
    ],
    "customer": [
        {"field_id": "customer_id", "data_type": "VARCHAR(50)", "name": "客户ID"},
        {"field_id": "customer_name", "data_type": "VARCHAR(200)", "name": "客户名称"},
        {"field_id": "customer_level", "data_type": "VARCHAR(50)", "name": "客户等级"},
        {"field_id": "industry", "data_type": "VARCHAR(100)", "name": "行业类别"},
        {"field_id": "credit_limit", "data_type": "FLOAT", "name": "信用额度(万元)"},
        {"field_id": "payment_terms", "data_type": "VARCHAR(100)", "name": "付款条件"},
        {"field_id": "contact_person", "data_type": "VARCHAR(100)", "name": "联系人"},
        {"field_id": "contact_phone", "data_type": "VARCHAR(50)", "name": "联系电话"},
        {"field_id": "contact_email", "data_type": "VARCHAR(100)", "name": "联系邮箱"},
        {"field_id": "address", "data_type": "VARCHAR(500)", "name": "地址"},
        {"field_id": "country", "data_type": "VARCHAR(50)", "name": "国家"},
        {"field_id": "region", "data_type": "VARCHAR(50)", "name": "地区"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
    ],
    "customer_product": [
        {"field_id": "id", "data_type": "INTEGER", "name": "ID"},
        {"field_id": "customer_id", "data_type": "VARCHAR(50)", "name": "客户ID"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "special_price", "data_type": "FLOAT", "name": "客户特定价格"},
        {"field_id": "min_order_qty", "data_type": "FLOAT", "name": "最小订单量"},
        {"field_id": "lead_time_days", "data_type": "INTEGER", "name": "特定交期(天)"},
        {"field_id": "quality_level", "data_type": "VARCHAR(50)", "name": "质量等级"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
    ],
    "customer_order": [
        {"field_id": "order_id", "data_type": "VARCHAR(50)", "name": "订单ID"},
        {"field_id": "customer_id", "data_type": "VARCHAR(50)", "name": "客户ID"},
        {"field_id": "customer_name", "data_type": "VARCHAR(200)", "name": "客户名称"},
        {"field_id": "customer_po_number", "data_type": "VARCHAR(100)", "name": "客户采购订单号"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "quantity", "data_type": "FLOAT", "name": "订单数量"},
        {"field_id": "unit_price", "data_type": "FLOAT", "name": "订单单价"},
        {"field_id": "order_date", "data_type": "DATETIME", "name": "下单日期"},
        {"field_id": "required_date", "data_type": "DATETIME", "name": "要求交期"},
        {"field_id": "priority", "data_type": "INTEGER", "name": "优先级"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "shipping_address", "data_type": "VARCHAR(500)", "name": "发货地址"},
        {"field_id": "quality_requirement", "data_type": "VARCHAR(100)", "name": "质量要求"},
        {"field_id": "packaging_requirement", "data_type": "VARCHAR(200)", "name": "包装要求"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
    ],
    "work_order": [
        {"field_id": "work_order_id", "data_type": "VARCHAR(50)", "name": "工单ID"},
        {"field_id": "customer_order_id", "data_type": "VARCHAR(50)", "name": "关联订单ID"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "planned_quantity", "data_type": "FLOAT", "name": "计划投入量"},
        {"field_id": "expected_output_qty", "data_type": "FLOAT", "name": "预期产出量"},
        {"field_id": "planned_start_date", "data_type": "DATETIME", "name": "计划开始日期"},
        {"field_id": "planned_completion_date", "data_type": "DATETIME", "name": "计划完成日期"},
        {"field_id": "actual_start_date", "data_type": "DATETIME", "name": "实际开始日期"},
        {"field_id": "actual_completion_date", "data_type": "DATETIME", "name": "实际完成日期"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "priority", "data_type": "INTEGER", "name": "优先级"},
        {"field_id": "setup_group", "data_type": "VARCHAR(50)", "name": "换线组"},
        {"field_id": "current_step_id", "data_type": "VARCHAR(50)", "name": "当前工序ID"},
        {"field_id": "completed_quantity", "data_type": "FLOAT", "name": "实际产出量"},
        {"field_id": "scrapped_quantity", "data_type": "FLOAT", "name": "报废数量"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
        {"field_id": "created_at", "data_type": "DATETIME", "name": "创建时间"},
    ],
    "work_order_operation": [
        {"field_id": "wo_op_id", "data_type": "VARCHAR(50)", "name": "工单工序ID"},
        {"field_id": "work_order_id", "data_type": "VARCHAR(50)", "name": "工单ID"},
        {"field_id": "step_id", "data_type": "VARCHAR(50)", "name": "工序ID"},
        {"field_id": "sequence_no", "data_type": "INTEGER", "name": "工序序号"},
        {"field_id": "planned_start", "data_type": "DATETIME", "name": "计划开始时间"},
        {"field_id": "planned_end", "data_type": "DATETIME", "name": "计划结束时间"},
        {"field_id": "actual_start", "data_type": "DATETIME", "name": "实际开始时间"},
        {"field_id": "actual_end", "data_type": "DATETIME", "name": "实际结束时间"},
        {"field_id": "required_input_qty", "data_type": "FLOAT", "name": "需求投入量"},
        {"field_id": "completed_output_qty", "data_type": "FLOAT", "name": "实际产出量"},
        {"field_id": "scrapped_qty", "data_type": "FLOAT", "name": "报废量"},
        {"field_id": "assigned_machine_id", "data_type": "VARCHAR(50)", "name": "分配机台ID"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "setup_completed", "data_type": "BOOLEAN", "name": "换线是否完成"},
        {"field_id": "material_issued", "data_type": "BOOLEAN", "name": "物料是否发放"},
    ],
    "work_order_material": [
        {"field_id": "wom_id", "data_type": "VARCHAR(50)", "name": "工单物料需求ID"},
        {"field_id": "work_order_id", "data_type": "VARCHAR(50)", "name": "工单ID"},
        {"field_id": "wo_op_id", "data_type": "VARCHAR(50)", "name": "工单工序ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "required_quantity", "data_type": "FLOAT", "name": "需求数量"},
        {"field_id": "allocated_quantity", "data_type": "FLOAT", "name": "已分配数量"},
        {"field_id": "consumed_quantity", "data_type": "FLOAT", "name": "已消耗数量"},
        {"field_id": "shortage_quantity", "data_type": "FLOAT", "name": "缺料数量"},
        {"field_id": "required_date", "data_type": "DATETIME", "name": "需求日期"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
    ],
    "purchase_order": [
        {"field_id": "po_id", "data_type": "VARCHAR(50)", "name": "采购订单ID"},
        {"field_id": "supplier_id", "data_type": "VARCHAR(50)", "name": "供应商ID"},
        {"field_id": "order_date", "data_type": "DATETIME", "name": "下单日期"},
        {"field_id": "expected_delivery_date", "data_type": "DATETIME", "name": "预期交货日期"},
        {"field_id": "actual_delivery_date", "data_type": "DATETIME", "name": "实际交货日期"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "total_amount", "data_type": "FLOAT", "name": "总金额"},
        {"field_id": "created_by", "data_type": "VARCHAR(50)", "name": "创建者"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
    ],
    "purchase_order_line": [
        {"field_id": "line_id", "data_type": "VARCHAR(50)", "name": "订单行ID"},
        {"field_id": "po_id", "data_type": "VARCHAR(50)", "name": "采购订单ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "quantity", "data_type": "FLOAT", "name": "采购数量"},
        {"field_id": "unit_price", "data_type": "FLOAT", "name": "单价"},
        {"field_id": "received_quantity", "data_type": "FLOAT", "name": "已收货数量"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "related_work_order_id", "data_type": "VARCHAR(50)", "name": "关联工单ID"},
        {"field_id": "related_wom_id", "data_type": "VARCHAR(50)", "name": "关联工单物料需求ID"},
    ],
    "wip_lot": [
        {"field_id": "lot_id", "data_type": "VARCHAR(50)", "name": "批次ID"},
        {"field_id": "work_order_id", "data_type": "VARCHAR(50)", "name": "工单ID"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "current_step_id", "data_type": "VARCHAR(50)", "name": "当前工序ID"},
        {"field_id": "current_machine_id", "data_type": "VARCHAR(50)", "name": "当前机台ID"},
        {"field_id": "lot_quantity", "data_type": "FLOAT", "name": "批次数量"},
        {"field_id": "actual_quantity", "data_type": "FLOAT", "name": "实际数量"},
        {"field_id": "lot_status", "data_type": "VARCHAR(50)", "name": "批次状态"},
        {"field_id": "queue_start_time", "data_type": "DATETIME", "name": "排队开始时间"},
        {"field_id": "processing_start_time", "data_type": "DATETIME", "name": "加工开始时间"},
        {"field_id": "completed_time", "data_type": "DATETIME", "name": "完工时间"},
        {"field_id": "hold_reason", "data_type": "VARCHAR(200)", "name": "Hold原因"},
        {"field_id": "priority", "data_type": "INTEGER", "name": "优先级"},
        {"field_id": "created_at", "data_type": "DATETIME", "name": "创建时间"},
    ],
    "production_task": [
        {"field_id": "task_id", "data_type": "VARCHAR(50)", "name": "任务ID"},
        {"field_id": "wo_op_id", "data_type": "VARCHAR(50)", "name": "工单工序ID"},
        {"field_id": "work_order_id", "data_type": "VARCHAR(50)", "name": "工单ID"},
        {"field_id": "machine_id", "data_type": "VARCHAR(50)", "name": "机台ID"},
        {"field_id": "lot_id", "data_type": "VARCHAR(50)", "name": "批次ID"},
        {"field_id": "planned_start_time", "data_type": "DATETIME", "name": "计划开始时间"},
        {"field_id": "planned_end_time", "data_type": "DATETIME", "name": "计划结束时间"},
        {"field_id": "actual_start_time", "data_type": "DATETIME", "name": "实际开始时间"},
        {"field_id": "actual_end_time", "data_type": "DATETIME", "name": "实际结束时间"},
        {"field_id": "planned_quantity", "data_type": "FLOAT", "name": "计划数量"},
        {"field_id": "actual_quantity", "data_type": "FLOAT", "name": "实际数量"},
        {"field_id": "scrap_quantity", "data_type": "FLOAT", "name": "报废数量"},
        {"field_id": "actual_efficiency", "data_type": "FLOAT", "name": "实际效率"},
        {"field_id": "actual_yield", "data_type": "FLOAT", "name": "实际良率"},
        {"field_id": "setup_time_actual", "data_type": "FLOAT", "name": "实际换线时间"},
        {"field_id": "wait_time_actual", "data_type": "FLOAT", "name": "实际等待时间"},
        {"field_id": "shift_id", "data_type": "VARCHAR(50)", "name": "班次ID"},
        {"field_id": "is_night_shift", "data_type": "BOOLEAN", "name": "是否夜班"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
    ],
    "material_transfer": [
        {"field_id": "transfer_id", "data_type": "VARCHAR(50)", "name": "调拨ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "from_work_order_id", "data_type": "VARCHAR(50)", "name": "来源工单ID"},
        {"field_id": "to_work_order_id", "data_type": "VARCHAR(50)", "name": "目标工单ID"},
        {"field_id": "from_location", "data_type": "VARCHAR(100)", "name": "来源仓库"},
        {"field_id": "to_location", "data_type": "VARCHAR(100)", "name": "目标仓库"},
        {"field_id": "from_wom_id", "data_type": "VARCHAR(50)", "name": "来源工单物料需求ID"},
        {"field_id": "to_wom_id", "data_type": "VARCHAR(50)", "name": "目标工单物料需求ID"},
        {"field_id": "quantity", "data_type": "FLOAT", "name": "调拨数量"},
        {"field_id": "transfer_reason", "data_type": "VARCHAR(100)", "name": "调拨原因"},
        {"field_id": "trigger_source", "data_type": "VARCHAR(50)", "name": "触发来源"},
        {"field_id": "requested_time", "data_type": "DATETIME", "name": "申请时间"},
        {"field_id": "executed_time", "data_type": "DATETIME", "name": "执行时间"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "approved_by", "data_type": "VARCHAR(50)", "name": "批准人"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
    ],
    "work_calendar": [
        {"field_id": "calendar_id", "data_type": "VARCHAR(50)", "name": "日历ID"},
        {"field_id": "calendar_date", "data_type": "DATE", "name": "日期"},
        {"field_id": "work_center_id", "data_type": "VARCHAR(50)", "name": "工作中心ID"},
        {"field_id": "shift_id", "data_type": "VARCHAR(50)", "name": "班次ID"},
        {"field_id": "is_workday", "data_type": "BOOLEAN", "name": "是否工作日"},
        {"field_id": "available_hours", "data_type": "FLOAT", "name": "可用工时"},
        {"field_id": "planned_capacity", "data_type": "FLOAT", "name": "计划产能"},
        {"field_id": "note", "data_type": "VARCHAR(200)", "name": "备注"},
    ],
    "inventory": [
        {"field_id": "inventory_id", "data_type": "VARCHAR(50)", "name": "库存ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "location", "data_type": "VARCHAR(100)", "name": "仓库位置"},
        {"field_id": "total_quantity", "data_type": "FLOAT", "name": "总数量"},
        {"field_id": "available_quantity", "data_type": "FLOAT", "name": "可用数量"},
        {"field_id": "reserved_quantity", "data_type": "FLOAT", "name": "预留数量"},
        {"field_id": "in_transit_quantity", "data_type": "FLOAT", "name": "在途数量"},
        {"field_id": "last_updated", "data_type": "DATETIME", "name": "最后更新时间"},
    ],
    "inventory_transaction": [
        {"field_id": "transaction_id", "data_type": "VARCHAR(50)", "name": "事务ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "transaction_type", "data_type": "VARCHAR(50)", "name": "事务类型"},
        {"field_id": "quantity", "data_type": "FLOAT", "name": "变动数量"},
        {"field_id": "balance_after", "data_type": "FLOAT", "name": "变动后总库存"},
        {"field_id": "available_balance_after", "data_type": "FLOAT", "name": "变动后可用库存"},
        {"field_id": "reserved_balance_after", "data_type": "FLOAT", "name": "变动后预留库存"},
        {"field_id": "related_document_type", "data_type": "VARCHAR(50)", "name": "关联单据类型"},
        {"field_id": "related_document_id", "data_type": "VARCHAR(50)", "name": "关联单据ID"},
        {"field_id": "from_work_order_id", "data_type": "VARCHAR(50)", "name": "来源工单ID"},
        {"field_id": "to_work_order_id", "data_type": "VARCHAR(50)", "name": "目标工单ID"},
        {"field_id": "transaction_time", "data_type": "DATETIME", "name": "事务时间"},
        {"field_id": "description", "data_type": "VARCHAR(500)", "name": "事务说明"},
        {"field_id": "created_by", "data_type": "VARCHAR(50)", "name": "创建者"},
    ],
    "finished_goods_inventory": [
        {"field_id": "fg_inv_id", "data_type": "VARCHAR(50)", "name": "成品库存ID"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "产品ID"},
        {"field_id": "location", "data_type": "VARCHAR(100)", "name": "仓库位置"},
        {"field_id": "total_quantity", "data_type": "FLOAT", "name": "总数量"},
        {"field_id": "available_quantity", "data_type": "FLOAT", "name": "可用数量"},
        {"field_id": "reserved_quantity", "data_type": "FLOAT", "name": "预留数量"},
        {"field_id": "shipped_quantity", "data_type": "FLOAT", "name": "已发货数量"},
        {"field_id": "last_updated", "data_type": "DATETIME", "name": "最后更新时间"},
    ],
    "quality_inspection": [
        {"field_id": "inspection_id", "data_type": "VARCHAR(50)", "name": "检验ID"},
        {"field_id": "inspection_type", "data_type": "VARCHAR(50)", "name": "检验类型"},
        {"field_id": "wo_op_id", "data_type": "VARCHAR(50)", "name": "工单工序ID"},
        {"field_id": "lot_id", "data_type": "VARCHAR(50)", "name": "批次ID"},
        {"field_id": "machine_id", "data_type": "VARCHAR(50)", "name": "机台ID"},
        {"field_id": "po_id", "data_type": "VARCHAR(50)", "name": "采购订单ID"},
        {"field_id": "material_id", "data_type": "VARCHAR(50)", "name": "物料ID"},
        {"field_id": "related_doc_type", "data_type": "VARCHAR(50)", "name": "关联单据类型"},
        {"field_id": "related_doc_id", "data_type": "VARCHAR(50)", "name": "关联单据ID"},
        {"field_id": "inspection_time", "data_type": "DATETIME", "name": "检验时间"},
        {"field_id": "inspect_qty", "data_type": "FLOAT", "name": "检验数量"},
        {"field_id": "pass_qty", "data_type": "FLOAT", "name": "合格数量"},
        {"field_id": "rework_qty", "data_type": "FLOAT", "name": "返工数量"},
        {"field_id": "scrap_qty", "data_type": "FLOAT", "name": "报废数量"},
        {"field_id": "concession_qty", "data_type": "FLOAT", "name": "让步接收数量"},
        {"field_id": "result", "data_type": "VARCHAR(50)", "name": "结果"},
        {"field_id": "disposition", "data_type": "VARCHAR(200)", "name": "处置说明"},
        {"field_id": "is_hold", "data_type": "BOOLEAN", "name": "是否Hold"},
        {"field_id": "inspector", "data_type": "VARCHAR(50)", "name": "检验员"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
    ],
    "schedule": [
        {"field_id": "schedule_id", "data_type": "VARCHAR(50)", "name": "排程ID"},
        {"field_id": "schedule_date", "data_type": "DATE", "name": "排程日期"},
        {"field_id": "total_load_hours", "data_type": "FLOAT", "name": "总负荷工时"},
        {"field_id": "utilization_rate", "data_type": "FLOAT", "name": "设备利用率"},
        {"field_id": "bottleneck_machine_id", "data_type": "VARCHAR(50)", "name": "瓶颈机台ID"},
        {"field_id": "bottleneck_work_center_id", "data_type": "VARCHAR(50)", "name": "瓶颈工作中心ID"},
        {"field_id": "total_orders", "data_type": "INTEGER", "name": "总订单数"},
        {"field_id": "completed_orders", "data_type": "INTEGER", "name": "完成订单数"},
        {"field_id": "created_at", "data_type": "DATETIME", "name": "创建时间"},
    ],
    "machine_status_log": [
        {"field_id": "log_id", "data_type": "VARCHAR(50)", "name": "日志ID"},
        {"field_id": "machine_id", "data_type": "VARCHAR(50)", "name": "机台ID"},
        {"field_id": "status_time", "data_type": "DATETIME", "name": "状态时间"},
        {"field_id": "status", "data_type": "VARCHAR(50)", "name": "状态"},
        {"field_id": "product_id", "data_type": "VARCHAR(50)", "name": "生产产品ID"},
        {"field_id": "running_wo_id", "data_type": "VARCHAR(50)", "name": "运行工单ID"},
        {"field_id": "running_task_id", "data_type": "VARCHAR(50)", "name": "运行任务ID"},
        {"field_id": "oee", "data_type": "FLOAT", "name": "OEE指标"},
        {"field_id": "note", "data_type": "VARCHAR(500)", "name": "备注"},
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
        
        print(f"\n{'='*60}")
        print(f"字段导入完成")
        print(f"{'='*60}")
        print(f"✅ 成功导入: {imported}")
        print(f"❌ 失败: {failed}")
        print(f"总计: {imported + failed}/{total_fields}")
        print(f"{'='*60}\n")


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
        
        print(f"\n业务关系:")
        print(f"  ✅ 成功: {self.stats['links']['success']}")
        print(f"  ❌ 失败: {self.stats['links']['failed']}")
        if self.stats['links']['errors']:
            print(f"\n  错误详情:")
            for error in self.stats['links']['errors']:
                print(f"    - {error['link_id']}: {error['error']}")
        
        total_success = self.stats['models']['success'] + self.stats['links']['success']
        total_failed = self.stats['models']['failed'] + self.stats['links']['failed']
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
