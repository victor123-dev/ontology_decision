"""
半导体制造业APS+MRP演示数据 - 数据库模型定义
包含26个核心实体，支持：
- 工艺路线与工序级物料追踪
- 机台能力矩阵与换线矩阵(SetupMatrix)
- 工作中心(WorkCenter)资源池
- 在制品批次(WIPLot)追踪
- 班次日历(WorkCalendar)
- 物料调拨(MaterialTransfer)
- 库存事务流水(InventoryTransaction)
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Index, create_engine, inspect
)
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship, Session
from datetime import datetime
from typing import List, Dict, Any

Base = declarative_base()

# ============================================================================
# 基础主数据层
# ============================================================================

class Product(Base):
    __tablename__ = "product"
    product_id = Column(String(50), primary_key=True)
    product_name = Column(String(100), nullable=False)
    product_type = Column(String(50), default="成品")
    standard_cycle_time = Column(Float, default=1.0)
    routing_steps = Column(Integer, default=3)
    setup_group = Column(String(50), default="DEFAULT")
    unit_of_measure = Column(String(20), default="PCS")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Material(Base):
    __tablename__ = "material"
    material_id = Column(String(50), primary_key=True)
    material_name = Column(String(100), nullable=False)
    material_type = Column(String(50), default="原材料")
    unit_of_measure = Column(String(20), default="PCS")
    safety_stock_level = Column(Float, default=20.0)
    reorder_point = Column(Float, default=30.0)
    lot_size = Column(Float, default=100.0)
    # P2-13: EOQ相关字段
    eoq = Column(Float, nullable=True)               # 经济订购量
    annual_demand = Column(Float, nullable=True)     # 年需求量
    holding_cost_rate = Column(Float, nullable=True) # 持有成本率
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class BOM(Base):
    __tablename__ = "bom"
    __table_args__ = (
        Index('idx_bom_product', 'product_id'),
        Index('idx_bom_material', 'material_id'),
    )
    bom_id = Column(String(50), primary_key=True)
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    step_id = Column(String(50), ForeignKey("route_step.step_id"), nullable=True)
    quantity_per_unit = Column(Float, default=1.0)
    is_critical = Column(Boolean, default=True)
    consumption_pattern = Column(String(50), default="工序开始时消耗")
    version = Column(String(20), default="v1.0")
    effective_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)

class Supplier(Base):
    __tablename__ = "supplier"
    supplier_id = Column(String(50), primary_key=True)
    supplier_name = Column(String(100), nullable=False)
    supplier_type = Column(String(50), default="直供")
    country = Column(String(50), default="中国")
    industry_position = Column(String(200), default="")
    avg_lead_time_days = Column(Integer, default=3)
    reliability_score = Column(Float, default=0.95)
    min_order_quantity = Column(Float, default=50.0)
    # P0-3: 交期标准差（供应商可靠性扰动）
    lead_time_stddev_days = Column(Float, default=0.5)
    is_active = Column(Boolean, default=True)

class SupplierMaterial(Base):
    __tablename__ = "supplier_material"
    __table_args__ = (
        Index('idx_sm_supplier', 'supplier_id'),
        Index('idx_sm_material', 'material_id'),
    )
    sm_id = Column(String(50), primary_key=True)
    supplier_id = Column(String(50), ForeignKey("supplier.supplier_id"), nullable=False)
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    unit_price = Column(Float, default=1.0)
    lead_time_days = Column(Integer, default=3)
    min_order_qty = Column(Float, default=50.0)
    is_preferred = Column(Boolean, default=True)
    effective_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)

class MaterialSubstitute(Base):
    __tablename__ = "material_substitute"
    ms_id = Column(String(50), primary_key=True)
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    substitute_material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    substitute_priority = Column(Integer, default=1)
    quality_grade = Column(String(50), default="同等级")
    approval_status = Column(String(50), default="已批准")
    cost_delta_percent = Column(Float, default=0.0)

# ============================================================================
# 工艺路线层
# ============================================================================

class ProcessRoute(Base):
    __tablename__ = "process_route"
    route_id = Column(String(50), primary_key=True)
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    route_name = Column(String(100), nullable=False)
    version = Column(String(20), default="v1.0")
    is_active = Column(Boolean, default=True)
    effective_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)

class RouteStep(Base):
    __tablename__ = "route_step"
    __table_args__ = (Index('idx_route_step_route', 'route_id'),)
    step_id = Column(String(50), primary_key=True)
    route_id = Column(String(50), ForeignKey("process_route.route_id"), nullable=False)
    sequence_no = Column(Integer, nullable=False)
    step_name = Column(String(100), nullable=False)
    operation_type = Column(String(50), default="加工")
    standard_time_hours = Column(Float, default=1.0)
    machine_type_required = Column(String(50), nullable=False)
    setup_time_minutes = Column(Integer, default=30)
    material_ready_offset_hours = Column(Float, default=2.0)
    yield_rate_standard = Column(Float, default=0.98)
    is_critical = Column(Boolean, default=False)
    # P1-5: 工序间等待/转运时间
    wait_time_hours = Column(Float, default=0.0)       # 工序完成后强制等待时间（如固化时间）
    transport_time_hours = Column(Float, default=0.0)  # 转运到下一工作中心的时间
    min_batch_qty = Column(Float, default=1.0)         # 最小批量（用于合批排程）
    max_batch_qty = Column(Float, nullable=True)       # 最大批量约束

# ============================================================================
# 资源与能力层
# ============================================================================

class WorkCenter(Base):
    __tablename__ = "work_center"
    work_center_id = Column(String(50), primary_key=True)
    work_center_name = Column(String(100), nullable=False)
    work_center_type = Column(String(50), nullable=False)
    capacity_uom = Column(String(20), default="小时")
    is_active = Column(Boolean, default=True)

class Machine(Base):
    __tablename__ = "machine"
    machine_id = Column(String(50), primary_key=True)
    machine_name = Column(String(100), nullable=False)
    machine_type = Column(String(50), nullable=False)
    work_center_id = Column(String(50), ForeignKey("work_center.work_center_id"), nullable=False)
    max_capacity_per_hour = Column(Float, default=100.0)
    status = Column(String(50), default="在线")
    current_product_id = Column(String(50), ForeignKey("product.product_id"), nullable=True)
    current_setup_group = Column(String(50), nullable=True)
    last_maintenance_date = Column(Date, nullable=True)
    next_maintenance_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)

class MachineCapability(Base):
    __tablename__ = "machine_capability"
    __table_args__ = (
        Index('idx_mc_machine', 'machine_id'),
        Index('idx_mc_product', 'product_id'),
    )
    capability_id = Column(String(50), primary_key=True)
    machine_id = Column(String(50), ForeignKey("machine.machine_id"), nullable=False)
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    efficiency_factor = Column(Float, default=1.0)
    setup_time_minutes = Column(Integer, default=30)
    yield_rate = Column(Float, default=0.98)
    is_preferred = Column(Boolean, default=False)
    rated_speed_per_hour = Column(Float, default=100.0)
    effective_date = Column(Date, nullable=True)
    # P1-9: OEE动态闭环字段
    actual_efficiency_avg = Column(Float, nullable=True)   # 基于历史ProductionTask计算的实际效率均值
    actual_yield_avg = Column(Float, nullable=True)        # 基于历史实际良率均值
    sample_count = Column(Integer, default=0)              # 统计样本数量
    last_updated_at = Column(DateTime, nullable=True)      # 最后更新时间

class SetupMatrix(Base):
    __tablename__ = "setup_matrix"
    __table_args__ = (
        Index('idx_sm_machine', 'machine_id'),
        Index('idx_sm_from', 'from_product_id'),
        Index('idx_sm_to', 'to_product_id'),
    )
    matrix_id = Column(String(50), primary_key=True)
    machine_id = Column(String(50), ForeignKey("machine.machine_id"), nullable=False)
    from_product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    to_product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    setup_time_minutes = Column(Integer, default=30)
    setup_type = Column(String(50), default="换模")
    is_active = Column(Boolean, default=True)

# ============================================================================
# 日历层
# ============================================================================

class ShiftPattern(Base):
    __tablename__ = "shift_pattern"
    shift_id = Column(String(50), primary_key=True)
    shift_name = Column(String(50), nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    available_hours = Column(Float, default=8.0)
    efficiency_factor = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)

class WorkCalendar(Base):
    __tablename__ = "work_calendar"
    __table_args__ = (
        Index('idx_calendar_date', 'calendar_date'),
        Index('idx_calendar_wc', 'work_center_id'),
    )
    calendar_id = Column(String(50), primary_key=True)
    calendar_date = Column(Date, nullable=False)
    work_center_id = Column(String(50), ForeignKey("work_center.work_center_id"), nullable=False)
    shift_id = Column(String(50), ForeignKey("shift_pattern.shift_id"), nullable=False)
    is_workday = Column(Boolean, default=True)
    available_hours = Column(Float, default=8.0)
    planned_capacity = Column(Float, default=100.0)
    note = Column(String(200), nullable=True)

# ============================================================================
# 需求与计划层
# ============================================================================

class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = (
        Index('idx_customer_level', 'customer_level'),
        Index('idx_customer_industry', 'industry'),
    )
    customer_id = Column(String(50), primary_key=True)
    customer_name = Column(String(200), nullable=False)
    customer_level = Column(String(50), default="普通")  # VIP/重要/普通
    industry = Column(String(100), nullable=True)  # 行业类别
    credit_limit = Column(Float, default=0.0)  # 信用额度（万元）
    payment_terms = Column(String(100), default="月结30天")  # 付款条件
    contact_person = Column(String(100), nullable=True)  # 联系人
    contact_phone = Column(String(50), nullable=True)  # 联系电话
    contact_email = Column(String(100), nullable=True)  # 联系邮箱
    address = Column(String(500), nullable=True)  # 地址
    country = Column(String(50), default="中国")  # 国家
    region = Column(String(50), default="大陆")  # 地区：大陆/台湾/欧美/亚太
    status = Column(String(50), default="活跃")  # 活跃/暂停/黑名单
    note = Column(String(500), nullable=True)

class CustomerProduct(Base):
    """客户-产品关系（客户可购买的产品清单、特定价格）"""
    __tablename__ = "customer_product"
    __table_args__ = (
        Index('idx_cp_customer', 'customer_id'),
        Index('idx_cp_product', 'product_id'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), ForeignKey("customer.customer_id"), nullable=False)
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    special_price = Column(Float, nullable=True)  # 客户特定价格
    min_order_qty = Column(Float, default=1.0)  # 最小订单量
    lead_time_days = Column(Integer, default=7)  # 特定交期（天）
    quality_level = Column(String(50), default="标准")  # 质量等级：标准/车规/工规
    status = Column(String(50), default="活跃")

class CustomerOrder(Base):
    __tablename__ = "customer_order"
    __table_args__ = (Index('idx_co_required', 'required_date'),)
    order_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customer.customer_id"), nullable=False)
    customer_name = Column(String(200), nullable=False)
    customer_po_number = Column(String(100), nullable=True)  # 客户采购订单号
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=True)  # 订单单价
    order_date = Column(DateTime, nullable=False)
    required_date = Column(DateTime, nullable=False)
    priority = Column(Integer, default=5)
    status = Column(String(50), default="已确认")
    shipping_address = Column(String(500), nullable=True)  # 发货地址
    quality_requirement = Column(String(100), default="标准")  # 质量要求
    packaging_requirement = Column(String(200), nullable=True)  # 包装要求
    note = Column(String(500), nullable=True)

class WorkOrder(Base):
    __tablename__ = "work_order"
    __table_args__ = (
        Index('idx_wo_status', 'status'),
        Index('idx_wo_product', 'product_id'),
        Index('idx_wo_required', 'planned_completion_date'),
    )
    work_order_id = Column(String(50), primary_key=True)
    customer_order_id = Column(String(50), ForeignKey("customer_order.order_id"), nullable=True)
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    work_order_type = Column(String(50), default="正常", comment="工单类型：正常/重工")
    planned_quantity = Column(Float, nullable=False)  # 计划投入量（含过量）
    expected_output_qty = Column(Float, nullable=True)  # 预期产出量（订单数量）
    planned_start_date = Column(DateTime, nullable=True)
    planned_completion_date = Column(DateTime, nullable=True)
    actual_start_date = Column(DateTime, nullable=True)
    actual_completion_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="已计划")
    priority = Column(Integer, default=5)
    setup_group = Column(String(50), nullable=True)
    current_step_id = Column(String(50), ForeignKey("route_step.step_id"), nullable=True)
    completed_quantity = Column(Float, default=0.0)  # 实际产出量（良品）
    scrapped_quantity = Column(Float, default=0.0)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkOrderOperation(Base):
    __tablename__ = "work_order_operation"
    __table_args__ = (
        Index('idx_woo_wo', 'work_order_id'),
        Index('idx_woo_step', 'step_id'),
        Index('idx_woo_status', 'status'),
    )
    wo_op_id = Column(String(50), primary_key=True)
    work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=False)
    step_id = Column(String(50), ForeignKey("route_step.step_id"), nullable=False)
    sequence_no = Column(Integer, nullable=False)
    planned_start = Column(DateTime, nullable=True)
    planned_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    required_input_qty = Column(Float, nullable=False)
    completed_output_qty = Column(Float, default=0.0)
    scrapped_qty = Column(Float, default=0.0)
    assigned_machine_id = Column(String(50), ForeignKey("machine.machine_id"), nullable=True)
    status = Column(String(50), default="待开工")
    is_rework = Column(Boolean, default=False, comment="是否重工序")
    setup_completed = Column(Boolean, default=False)
    material_issued = Column(Boolean, default=False)

class WorkOrderMaterial(Base):
    __tablename__ = "work_order_material"
    __table_args__ = (
        Index('idx_wom_wo', 'work_order_id'),
        Index('idx_wom_mat', 'material_id'),
        Index('idx_wom_op', 'wo_op_id'),
    )
    wom_id = Column(String(50), primary_key=True)
    work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=False)
    wo_op_id = Column(String(50), ForeignKey("work_order_operation.wo_op_id"), nullable=True)
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    required_quantity = Column(Float, nullable=False)
    allocated_quantity = Column(Float, default=0.0)
    consumed_quantity = Column(Float, default=0.0)
    shortage_quantity = Column(Float, default=0.0)
    required_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="待分配")
    note = Column(String(500), nullable=True)

# ============================================================================
# 采购层
# ============================================================================

class PurchaseOrder(Base):
    __tablename__ = "purchase_order"
    __table_args__ = (Index('idx_po_status', 'status'),)
    po_id = Column(String(50), primary_key=True)
    supplier_id = Column(String(50), ForeignKey("supplier.supplier_id"), nullable=False)
    order_date = Column(DateTime, nullable=False)
    expected_delivery_date = Column(DateTime, nullable=False)
    actual_delivery_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="已创建")
    total_amount = Column(Float, default=0.0)
    created_by = Column(String(50), default="SYSTEM")
    note = Column(String(500), nullable=True)

class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_line"
    __table_args__ = (
        Index('idx_pol_po', 'po_id'),
        Index('idx_pol_mat', 'material_id'),
    )
    line_id = Column(String(50), primary_key=True)
    po_id = Column(String(50), ForeignKey("purchase_order.po_id"), nullable=False)
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, default=0.0)
    received_quantity = Column(Float, default=0.0)
    status = Column(String(50), default="未开始")
    related_work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=True)
    related_wom_id = Column(String(50), ForeignKey("work_order_material.wom_id"), nullable=True)

# ============================================================================
# 执行层
# ============================================================================

class WIPLot(Base):
    __tablename__ = "wip_lot"
    __table_args__ = (
        Index('idx_wip_wo', 'work_order_id'),
        Index('idx_wip_status', 'lot_status'),
    )
    lot_id = Column(String(50), primary_key=True)
    work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=False)
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    lot_size = Column(Float, default=25, comment="批次大小（标准25片/批）")
    current_step_id = Column(String(50), ForeignKey("route_step.step_id"), nullable=True)
    current_machine_id = Column(String(50), ForeignKey("machine.machine_id"), nullable=True)
    lot_quantity = Column(Float, nullable=False)
    actual_quantity = Column(Float, nullable=True)         # P0-2: 经良率损耗后的实际数量
    lot_status = Column(String(50), default="排队中")
    queue_start_time = Column(DateTime, nullable=True)
    processing_start_time = Column(DateTime, nullable=True)
    completed_time = Column(DateTime, nullable=True)       # 完工时间
    hold_reason = Column(String(200), nullable=True)
    priority = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProductionTask(Base):
    __tablename__ = "production_task"
    __table_args__ = (
        Index('idx_pt_wo', 'work_order_id'),
        Index('idx_pt_machine', 'machine_id'),
        Index('idx_pt_woop', 'wo_op_id'),
        Index('idx_pt_status', 'status'),
    )
    task_id = Column(String(50), primary_key=True)
    wo_op_id = Column(String(50), ForeignKey("work_order_operation.wo_op_id"), nullable=False)
    work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=False)
    machine_id = Column(String(50), ForeignKey("machine.machine_id"), nullable=False)
    lot_id = Column(String(50), ForeignKey("wip_lot.lot_id"), nullable=True)  # P1-6: 关联WIPLot
    planned_start_time = Column(DateTime, nullable=False)
    planned_end_time = Column(DateTime, nullable=False)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    planned_quantity = Column(Float, nullable=False)
    actual_quantity = Column(Float, default=0.0)
    scrap_quantity = Column(Float, default=0.0)
    actual_efficiency = Column(Float, nullable=True)
    actual_yield = Column(Float, nullable=True)
    setup_time_actual = Column(Float, nullable=True)
    wait_time_actual = Column(Float, default=0.0)    # P1-5: 实际等待时间（含排队+转运）
    shift_id = Column(String(50), ForeignKey("shift_pattern.shift_id"), nullable=True)  # P2-10: 班次
    is_night_shift = Column(Boolean, default=False)  # P2-10: 是否夜班（用于效率折减）
    status = Column(String(50), default="已排程")
    note = Column(String(500), nullable=True)

class MaterialTransfer(Base):
    __tablename__ = "material_transfer"
    __table_args__ = (
        Index('idx_mt_from', 'from_work_order_id'),
        Index('idx_mt_to', 'to_work_order_id'),
        Index('idx_mt_mat', 'material_id'),
    )
    transfer_id = Column(String(50), primary_key=True)
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    from_work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=True)  # Task11: 仓库间调拨时可为NULL
    to_work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=True)    # Task11: 仓库间调拨时可为NULL
    from_location = Column(String(100), nullable=True)  # Task11: 来源仓库
    to_location = Column(String(100), nullable=True)    # Task11: 目标仓库
    from_wom_id = Column(String(50), ForeignKey("work_order_material.wom_id"), nullable=True)
    to_wom_id = Column(String(50), ForeignKey("work_order_material.wom_id"), nullable=True)
    quantity = Column(Float, nullable=False)
    transfer_reason = Column(String(100), default="缺料挪用")
    trigger_source = Column(String(50), default="MRP运算")
    requested_time = Column(DateTime, nullable=False)
    executed_time = Column(DateTime, nullable=True)
    status = Column(String(50), default="已创建")
    approved_by = Column(String(50), nullable=True)
    note = Column(String(500), nullable=True)

# ============================================================================
# 库存层
# ============================================================================

class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        Index('idx_inv_material', 'material_id'),
        Index('idx_inv_location', 'location'),
    )
    inventory_id = Column(String(50), primary_key=True)
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    location = Column(String(100), default="主仓库")
    total_quantity = Column(Float, default=0.0)
    available_quantity = Column(Float, default=0.0)
    reserved_quantity = Column(Float, default=0.0)
    in_transit_quantity = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

class InventoryTransaction(Base):
    __tablename__ = "inventory_transaction"
    __table_args__ = (
        Index('idx_it_material', 'material_id'),
        Index('idx_it_time', 'transaction_time'),
        Index('idx_it_type', 'transaction_type'),
        Index('idx_it_doc', 'related_document_type', 'related_document_id'),
    )
    transaction_id = Column(String(50), primary_key=True)
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    quantity = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    available_balance_after = Column(Float, nullable=False)
    reserved_balance_after = Column(Float, nullable=False)
    related_document_type = Column(String(50), nullable=True)
    related_document_id = Column(String(50), nullable=True)
    from_work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=True)
    to_work_order_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=True)
    transaction_time = Column(DateTime, nullable=False)
    description = Column(String(500), nullable=True)
    created_by = Column(String(50), default="SYSTEM")

# ============================================================================
# 监控层
# ============================================================================

class MachineStatusLog(Base):
    __tablename__ = "machine_status_log"
    __table_args__ = (
        Index('idx_msl_machine', 'machine_id'),
        Index('idx_msl_time', 'status_time'),
    )
    log_id = Column(String(50), primary_key=True)
    machine_id = Column(String(50), ForeignKey("machine.machine_id"), nullable=False)
    status_time = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=True)
    running_wo_id = Column(String(50), ForeignKey("work_order.work_order_id"), nullable=True)
    running_task_id = Column(String(50), ForeignKey("production_task.task_id"), nullable=True)
    oee = Column(Float, nullable=True)
    note = Column(String(500), nullable=True)

class Schedule(Base):
    __tablename__ = "schedule"
    __table_args__ = (Index('idx_sch_date', 'schedule_date'),)
    schedule_id = Column(String(50), primary_key=True)
    schedule_date = Column(Date, nullable=False)
    total_load_hours = Column(Float, default=0.0)
    utilization_rate = Column(Float, default=0.0)
    bottleneck_machine_id = Column(String(50), ForeignKey("machine.machine_id"), nullable=True)
    bottleneck_work_center_id = Column(String(50), ForeignKey("work_center.work_center_id"), nullable=True)
    total_orders = Column(Integer, default=0)
    completed_orders = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# 成品库存层
# ============================================================================

class FinishedGoodsInventory(Base):
    """成品库存（区别于原材料Inventory）"""
    __tablename__ = "finished_goods_inventory"
    __table_args__ = (
        Index('idx_fgi_product', 'product_id'),
        Index('idx_fgi_location', 'location'),
    )
    fg_inv_id = Column(String(50), primary_key=True)
    product_id = Column(String(50), ForeignKey("product.product_id"), nullable=False)
    location = Column(String(100), default="成品仓")
    total_quantity = Column(Float, default=0.0)
    available_quantity = Column(Float, default=0.0)
    reserved_quantity = Column(Float, default=0.0)   # 已分配给客户订单但未出库
    shipped_quantity = Column(Float, default=0.0)    # 累计已发货数量
    last_updated = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# 质检层
# ============================================================================

class QualityInspection(Base):
    """质量检验记录（含IQC入料检验和过程质检）"""
    __tablename__ = "quality_inspection"
    __table_args__ = (
        Index('idx_qi_wo_op', 'wo_op_id'),
        Index('idx_qi_lot', 'lot_id'),
        Index('idx_qi_type', 'inspection_type'),
    )
    inspection_id = Column(String(50), primary_key=True)
    inspection_type = Column(String(50), nullable=False)   # "过程质检" / "IQC入料" / "完工检验" / "首件检验" / "FQC出货检验"
    wo_op_id = Column(String(50), ForeignKey("work_order_operation.wo_op_id"), nullable=True)
    lot_id = Column(String(50), ForeignKey("wip_lot.lot_id"), nullable=True)
    machine_id = Column(String(50), ForeignKey("machine.machine_id"), nullable=True)
    po_id = Column(String(50), ForeignKey("purchase_order.po_id"), nullable=True)  # IQC用
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=True)  # IQC用
    # Task8/9/11: 通用关联字段（支持IPQC、FQC等新类型）
    related_doc_type = Column(String(50), nullable=True)   # WorkOrderOperation/CustomerOrder/PurchaseOrder
    related_doc_id = Column(String(50), nullable=True)     # 对应文档ID
    inspection_time = Column(DateTime, nullable=False)
    inspect_qty = Column(Float, default=0.0)     # 检验数量
    pass_qty = Column(Float, default=0.0)        # 合格数量
    rework_qty = Column(Float, default=0.0)      # 返工数量（可修复）
    scrap_qty = Column(Float, default=0.0)       # 报废数量（不可修复）
    concession_qty = Column(Float, default=0.0) # 让步接收数量
    result = Column(String(50), default="合格")  # 合格/返工/报废/让步接收/拒收
    disposition = Column(String(200), nullable=True)  # 处置说明
    is_hold = Column(Boolean, default=False)     # 是否处于Hold状态
    inspector = Column(String(50), default="QC-AUTO")
    note = Column(String(500), nullable=True)


# ============================================================================
# 外部供应链风险（舆情监控）
# ============================================================================

class ExternalSupplyChainRisk(Base):
    """外部供应链风险事件（通过舆情监控获取）
    
    设计说明：
    - supplier_id字段：记录风险事件的“主要受影响方”或“直接责任方”（1个）
    - 如需记录多个关联供应商及其影响程度，使用SupplierRiskAssociation表
    - 例如：台湾地震主要影响欣兴电子（SUP-001），但也会间接影响深南电路（SUP-006）
    """
    __tablename__ = "external_supply_chain_risk"
    __table_args__ = (
        Index('idx_risk_supplier', 'supplier_id'),
        Index('idx_risk_customer', 'customer_id'),
        Index('idx_risk_level', 'risk_level'),
        Index('idx_risk_status', 'status'),
        Index('idx_risk_detected_at', 'detected_at'),
    )
    
    risk_id = Column(String(50), primary_key=True)  # 风险事件ID
    
    # 关联对象
    supplier_id = Column(String(50), ForeignKey("supplier.supplier_id"), nullable=True)  # 关联供应商
    customer_id = Column(String(50), ForeignKey("customer.customer_id"), nullable=True)  # 关联客户
    material_id = Column(String(50), ForeignKey("material.material_id"), nullable=True)  # 关联物料
    
    # 风险分类
    risk_category = Column(String(50), nullable=False)  # 风险类别：自然灾害，政治事件，财务风险，质量风险，法律风险，运营风险
    risk_level = Column(String(20), nullable=False)  # 风险等级： 严重，高，中，低
    
    # 风险详情
    title = Column(String(200), nullable=False)  # 风险事件标题
    description = Column(Text, nullable=False)  # 风险事件描述
    source_url = Column(String(500), nullable=True)  # 信息来源URL
    source_name = Column(String(100), nullable=True)  # 信息来源名称（如：Reuters, Bloomberg）
    
    # 影响评估
    impact_scope = Column(String(50), nullable=True)  # 影响范围：全球，区域，局部
    estimated_impact_days = Column(Integer, nullable=True)  # 预估影响天数
    affected_materials = Column(Text, nullable=True)  # 受影响的物料（JSON数组）
    affected_products = Column(Text, nullable=True)  # 受影响的产品（JSON数组）
    
    # 时间信息
    event_date = Column(Date, nullable=True)  # 事件发生日期
    detected_at = Column(DateTime, default=datetime.utcnow)  # 检测时间
    
    # 处理状态
    status = Column(String(20), default="new")  # 状态：新发现，分析中，缓解中，已解决，已忽略
    assigned_to = Column(String(50), nullable=True)  # 负责人
    mitigation_plan = Column(Text, nullable=True)  # 缓解计划
    resolved_at = Column(DateTime, nullable=True)  # 解决时间
    
    # 元数据
    confidence_score = Column(Float, nullable=True)  # AI分析置信度（0-1）
    keywords = Column(Text, nullable=True)  # 关键词（JSON数组）
    raw_content = Column(Text, nullable=True)  # 原始舆情内容
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupplierRiskAssociation(Base):
    """供应商-风险关联表（多对多关系）
    
    设计说明：
    - 用于记录风险事件的“波及影响链”，支持1个风险事件关联N个供应商
    - association_type区分关联性质：direct（直接受影响）、indirect（间接影响）、potential（潜在影响）
    - impact_level记录对该供应商的具体影响程度，可与风险整体等级（risk_level）不同
    - 例如：台湾地震（RISK-001）直接打击SUP-001（critical），但给SUP-006带来转单机会（medium）
    """
    __tablename__ = "supplier_risk_association"
    __table_args__ = (
        Index('idx_sra_supplier', 'supplier_id'),
        Index('idx_sra_risk', 'risk_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(String(50), ForeignKey("supplier.supplier_id"), nullable=False)
    risk_id = Column(String(50), ForeignKey("external_supply_chain_risk.risk_id"), nullable=False)
    association_type = Column(String(50), default="direct")  # 关联类型：直接, 间接, 潜在
    impact_level = Column(String(20), nullable=True)  # 对该供应商的影响程度：严重, 高, 中, 低
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# 数据库工具函数
# ============================================================================

def create_tables(engine_url: str = "sqlite:///data.db"):
    """创建所有表"""
    engine = create_engine(engine_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def drop_tables(engine_url: str = "sqlite:///data.db"):
    """删除所有表（慎用）"""
    engine = create_engine(engine_url, echo=False)
    Base.metadata.drop_all(engine)


def get_session(engine_url: str = "sqlite:///data.db"):
    """获取数据库会话"""
    engine = create_engine(engine_url, echo=False)
    return Session(engine)


def table_exists(engine_url: str, table_name: str) -> bool:
    """检查表是否存在"""
    engine = create_engine(engine_url, echo=False)
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()
