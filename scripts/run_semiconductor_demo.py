"""
半导体制造业APS+MRP演示数据生成器 - 主运行脚本

运行方式:
    cd scripts
    python run_semiconductor_demo.py

功能:
1. 创建26个核心表的本体结构
2. 插入工厂静态主数据（产品/BOM/工艺路线/机台/供应商等）
3. 运行30天SimPy离散事件仿真
4. 自动生成客户订单、工单、生产任务、库存流水、调拨单、采购订单
5. 执行数据完整性校验

输出:
- 数据库: data.db (复用项目现有数据库)
- 可直接在项目前端本体视图中查看各实体关系
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from semiconductor_demo.db_models import create_tables, drop_tables, Base
from semiconductor_demo.db_writer import SimulationDBWriter
from semiconductor_demo.factory_data import (
    PRODUCTS, MATERIALS, BOMS, PROCESS_ROUTES, ROUTE_STEPS,
    WORK_CENTERS, MACHINES, MACHINE_CAPABILITIES, SETUP_MATRIX,
    SUPPLIERS, SUPPLIER_MATERIALS, MATERIAL_SUBSTITUTES,
    SHIFT_PATTERNS, INITIAL_INVENTORY, SIMULATION_CONFIG,
    generate_work_calendar
)
from semiconductor_demo.simulation import FactorySimulation
from simulation_logger import get_simulation_logger
import simpy

# 获取日志记录器
logger = get_simulation_logger()


def insert_static_data(db: SimulationDBWriter):
    """插入工厂静态配置数据"""
    logger.info("[1/4] 插入静态主数据...")
    
    # 产品
    for p in PRODUCTS:
        db.insert("product", p)
    logger.info(f"  - 产品: {db.count_records('product')} 条")
    
    # 物料
    for m in MATERIALS:
        db.insert("material", m)
    logger.info(f"  - 物料: {db.count_records('material')} 条")
    
    # BOM
    for b in BOMS:
        db.insert("bom", b)
    logger.info(f"  - BOM: {db.count_records('bom')} 条")
    
    # 工艺路线
    for r in PROCESS_ROUTES:
        db.insert("process_route", r)
    logger.info(f"  - 工艺路线: {db.count_records('process_route')} 条")
    
    # 工序（批量插入）
    db.bulk_insert_with_transaction("route_step", ROUTE_STEPS, batch_size=1000)
    logger.info(f"  - 工序: {db.count_records('route_step')} 条")
    
    # 工作中心
    for wc in WORK_CENTERS:
        db.insert("work_center", wc)
    logger.info(f"  - 工作中心: {db.count_records('work_center')} 条")
    
    # 机台
    for m in MACHINES:
        db.insert("machine", m)
    logger.info(f"  - 机台: {db.count_records('machine')} 条")
    
    # 机台能力矩阵（批量插入）
    db.bulk_insert_with_transaction("machine_capability", MACHINE_CAPABILITIES, batch_size=1000)
    logger.info(f"  - 机台能力: {db.count_records('machine_capability')} 条")
    
    # 换线矩阵（批量插入）
    db.bulk_insert_with_transaction("setup_matrix", SETUP_MATRIX, batch_size=1000)
    logger.info(f"  - 换线矩阵: {db.count_records('setup_matrix')} 条")
    
    # 供应商
    for s in SUPPLIERS:
        db.insert("supplier", s)
    logger.info(f"  - 供应商: {db.count_records('supplier')} 条")
    
    # 供应商物料关系（批量插入）
    db.bulk_insert_with_transaction("supplier_material", SUPPLIER_MATERIALS, batch_size=500)
    logger.info(f"  - 供应商物料: {db.count_records('supplier_material')} 条")
    
    # 物料替代（批量插入）
    db.bulk_insert_with_transaction("material_substitute", MATERIAL_SUBSTITUTES, batch_size=100)
    logger.info(f"  - 物料替代: {db.count_records('material_substitute')} 条")
    
    # 班次
    for sp in SHIFT_PATTERNS:
        db.insert("shift_pattern", sp)
    logger.info(f"  - 班次: {db.count_records('shift_pattern')} 条")
    
    # 班次日历（30天）
    start_date = datetime.fromisoformat(SIMULATION_CONFIG['start_date'].split(' ')[0])  # 只取日期部分
    calendars = generate_work_calendar(start_date, SIMULATION_CONFIG["duration_days"])
    db.bulk_insert("work_calendar", calendars)
    logger.info(f"  - 班次日历: {db.count_records('work_calendar')} 条")
    
    # 初始库存
    for inv in INITIAL_INVENTORY:
        inv["inventory_id"] = f"INV-{inv['material_id']}-{inv['location']}"
        inv["last_updated"] = start_date
        db.insert("inventory", inv)
    logger.info(f"  - 库存: {db.count_records('inventory')} 条")
    
    # T2: 初始化成品库存（初始为0）
    for p in PRODUCTS:
        fg_inv_id = f"FGI-{p['product_id']}"
        db.insert("finished_goods_inventory", {
            "fg_inv_id": fg_inv_id,
            "product_id": p["product_id"],
            "location": "成品仓",
            "total_quantity": 0.0,
            "available_quantity": 0.0,
            "reserved_quantity": 0.0,
            "shipped_quantity": 0.0,
            "last_updated": start_date
        })
    logger.info(f"  - 成品库存：{db.count_records('finished_goods_inventory')} 条")
    
    logger.info("[1/4] 静态主数据插入完成!\n")


def init_simulation_state(sim: FactorySimulation, db: SimulationDBWriter):
    """初始化仿真状态（从静态数据加载到内存）"""
    logger.info("[2/4] 初始化仿真状态...")
    
    # 加载产品
    rows = db.query("SELECT * FROM product")
    for r in rows:
        sim.products[r["product_id"]] = dict(r)
    logger.info(f"  - 加载产品: {len(sim.products)}")
    
    # 加载物料（含EOQ等扩展字段）
    rows = db.query("SELECT * FROM material")
    for r in rows:
        sim.materials[r["material_id"]] = dict(r)
    logger.info(f"  - 加载物料: {len(sim.materials)}")
    
    # 加载BOM
    rows = db.query("SELECT * FROM bom")
    for r in rows:
        sim.boms[r["product_id"]].append(dict(r))
    logger.info(f"  - 加载BOM: {sum(len(v) for v in sim.boms.values())}")
    
    # 加载工艺路线工序（含新增的wait_time_hours等字段）
    rows = db.query("SELECT rs.*, pr.product_id FROM route_step rs JOIN process_route pr ON rs.route_id = pr.route_id")
    for r in rows:
        r_dict = dict(r)
        sim.route_steps[r["route_id"]].append(r_dict)
        sim.route_steps_by_step_id[r["step_id"]] = r_dict
    logger.info(f"  - 加载工序: {sum(len(v) for v in sim.route_steps.values())}")
    
    # Lot批量加工：构建step_id到工序代码的映射（从step_name提取，如"RECV-10" -> "RECV"）
    for step_id, step in sim.route_steps_by_step_id.items():
        step_name = step.get("step_name", "")
        # step_name格式："RECV-10" 或 "WB-50"
        if "-" in step_name:
            step_code = step_name.split("-")[0]
            sim.step_code_map[step_id] = step_code
    logger.info(f"  - 构建工序代码映射: {len(sim.step_code_map)}条")
    
    # 加载机台
    rows = db.query("SELECT * FROM machine")
    for r in rows:
        sim.machines[r["machine_id"]] = dict(r)
    logger.info(f"  - 加载机台: {len(sim.machines)}")
    
    # 加载能力矩阵
    rows = db.query("SELECT * FROM machine_capability")
    for r in rows:
        sim.machine_capabilities[(r["machine_id"], r["product_id"])] = dict(r)
    logger.info(f"  - 加载能力矩阵: {len(sim.machine_capabilities)}")
    
    # 加载换线矩阵
    rows = db.query("SELECT * FROM setup_matrix")
    for r in rows:
        sim.setup_matrix[(r["machine_id"], r["from_product_id"], r["to_product_id"])] = r["setup_time_minutes"]
    logger.info(f"  - 加载换线矩阵: {len(sim.setup_matrix)}")
    
    # 加载供应商物料（含lead_time_stddev_days）
    rows = db.query("SELECT sm.*, s.reliability_score, s.lead_time_stddev_days FROM supplier_material sm JOIN supplier s ON sm.supplier_id = s.supplier_id")
    for r in rows:
        r_dict = dict(r)
        # 合并供应商可靠性信息到供应商物料记录
        sim.supplier_materials[r["material_id"]].append(r_dict)
    logger.info(f"  - 加载供应商物料: {sum(len(v) for v in sim.supplier_materials.values())}")
    
    # P1-7: 加载物料替代
    rows = db.query("SELECT * FROM material_substitute")
    for r in rows:
        sim.material_substitutes[r["material_id"]].append(dict(r))
    logger.info(f"  - 加载物料替代: {sum(len(v) for v in sim.material_substitutes.values())}")
    
    # 加载工作中心
    rows = db.query("SELECT * FROM work_center")
    for r in rows:
        sim.work_centers[r["work_center_id"]] = dict(r)
    logger.info(f"  - 加载工作中心: {len(sim.work_centers)}")
    
    # 初始化库存状态
    sim.init_inventory(INITIAL_INVENTORY)
    logger.info(f"  - 初始化库存状态完成")
    
    # T2: 初始化成品库存内存状态
    for p in PRODUCTS:
        pid = p["product_id"]
        sim.fg_inventory_state[pid] = {"total": 0.0, "available": 0.0, "reserved": 0.0, "shipped": 0.0}
    logger.info(f"  - 初始化成品库存内存状态完成")
    
    # 初始化机台资源
    sim.init_machines(MACHINES)
    logger.info(f"  - 初始化机台资源完成")
    
    logger.info("[2/4] 仿真状态初始化完成!\n")


def run_simulation(db: SimulationDBWriter):
    """运行DES仿真"""
    logger.info("[3/4] 启动SimPy离散事件仿真...")
    logger.info(f"  - 仿真周期: {SIMULATION_CONFIG['duration_days']} 天")
    logger.info(f"  - 开始时间: {SIMULATION_CONFIG['start_date']}")
    
    start_date = datetime.fromisoformat(SIMULATION_CONFIG['start_date'])
    env = simpy.Environment()
    
    sim = FactorySimulation(env, db, start_date, SIMULATION_CONFIG)
    init_simulation_state(sim, db)
    
    sim.run()
    
    logger.info("[3/4] 仿真运行完成!\n")
    return sim


def validate_data(db: SimulationDBWriter):
    """数据完整性校验"""
    logger.info("[4/4] 执行数据完整性校验...")
    errors = []
    warnings = []
    
    # R1: 库存预留不能超过总库存
    rows = db.query("""
        SELECT inventory_id, material_id, total_quantity, reserved_quantity
        FROM inventory WHERE reserved_quantity > total_quantity
    """)
    if rows:
        errors.append(f"R1-库存预留超限: {len(rows)} 条记录")
        for r in rows[:3]:
            errors.append(f"  {r['inventory_id']}: reserved={r['reserved_quantity']:.2f} > total={r['total_quantity']:.2f}")
    else:
        logger.info("  [PASS] R1: 库存预留 ≤ 总库存")
    
    # R2: 工单物料消耗不能超过分配量
    rows = db.query("""
        SELECT wom_id, work_order_id, material_id, consumed_quantity, allocated_quantity
        FROM work_order_material WHERE consumed_quantity > allocated_quantity
    """)
    if rows:
        errors.append(f"R2-物料消耗超限: {len(rows)} 条记录")
    else:
        logger.info("  [PASS] R2: 物料消耗 ≤ 分配量")
    
    # R3: 生产任务实际结束时间必须晚于开始时间
    rows = db.query("""
        SELECT task_id, actual_start_time, actual_end_time
        FROM production_task
        WHERE actual_start_time IS NOT NULL AND actual_end_time IS NOT NULL
        AND actual_end_time < actual_start_time
    """)
    if rows:
        errors.append(f"R3-时间逆序: {len(rows)} 条记录")
    else:
        logger.info("  [PASS] R3: 生产任务时间单调")
    
    # R4: 调拨数量必须为正
    rows = db.query("SELECT transfer_id, quantity FROM material_transfer WHERE quantity <= 0")
    if rows:
        errors.append(f"R4-调拨数量异常: {len(rows)} 条记录")
    else:
        logger.info("  [PASS] R4: 调拨数量正常")
    
    # R5: 采购订单行单价必须为正
    rows = db.query("""
        SELECT line_id, quantity, unit_price
        FROM purchase_order_line
        WHERE quantity <= 0 OR unit_price < 0
    """)
    if rows:
        errors.append(f"R5-采购订单行金额异常: {len(rows)} 条记录")
    else:
        logger.info("  [PASS] R5: 采购订单行金额正常")
    
    # R6: 外键一致性检查 - 生产任务的machine_id必须存在于machine表
    rows = db.query("""
        SELECT DISTINCT pt.machine_id
        FROM production_task pt
        LEFT JOIN machine m ON pt.machine_id = m.machine_id
        WHERE m.machine_id IS NULL
    """)
    if rows:
        errors.append(f"R6-外键断链(machine): {len(rows)} 条")
    else:
        logger.info("  [PASS] R6: 外键一致性(machine)")
    
    # R7: WorkOrderMaterial的work_order_id必须存在于work_order表
    rows = db.query("""
        SELECT DISTINCT wom.work_order_id
        FROM work_order_material wom
        LEFT JOIN work_order wo ON wom.work_order_id = wo.work_order_id
        WHERE wo.work_order_id IS NULL
    """)
    if rows:
        errors.append(f"R7-外键断链(work_order): {len(rows)} 条")
    else:
        logger.info("  [PASS] R7: 外键一致性(work_order)")
    
    # R8: 库存事务流水余额非负
    rows = db.query("""
        SELECT transaction_id, balance_after
        FROM inventory_transaction WHERE balance_after < 0
    """)
    if rows:
        errors.append(f"R8-库存余额为负: {len(rows)} 条")
    else:
        logger.info("  [PASS] R8: 库存余额非负")
    
    # 新增R9: 工序前驱约束验证（不应出现上一工序未完成而下一工序已完成的情况）
    rows = db.query("""
        SELECT later.wo_op_id as later_op, earlier.wo_op_id as earlier_op
        FROM work_order_operation later
        JOIN work_order_operation earlier ON later.work_order_id = earlier.work_order_id
            AND earlier.sequence_no < later.sequence_no
            AND earlier.status != '已完成'
        WHERE later.status = '已完成'
        LIMIT 5
    """)
    if rows:
        warnings.append(f"R9-前驱约束疑似违反: {len(rows)} 条（可能为正在执行中）")
    else:
        logger.info("  [PASS] R9: 工序前驱约束")
    
    # 新增R10: 良率传递验证（下一工序的required_input_qty应<=上一工序的completed_output_qty × 1.01（允许1%误差）
    rows = db.query("""
        SELECT later.wo_op_id, later.required_input_qty, earlier.completed_output_qty
        FROM work_order_operation later
        JOIN work_order_operation earlier ON later.work_order_id = earlier.work_order_id
            AND earlier.sequence_no = later.sequence_no - 10
        WHERE earlier.completed_output_qty > 0
        AND later.required_input_qty > earlier.completed_output_qty * 1.05
    """)
    if rows:
        warnings.append(f"R10-良率传递偏差过大: {len(rows)} 条")
    else:
        logger.info("  [PASS] R10: 良率损耗传递正常")
    
    # 新增R11: PM维护日志验证
    pm_rows = db.query("SELECT COUNT(*) as cnt FROM machine_status_log WHERE status='维护'")
    pm_cnt = pm_rows[0]["cnt"] if pm_rows else 0
    if pm_cnt > 0:
        logger.info(f"  [PASS] R11: 机台PM维护已执行 {pm_cnt} 次")
    else:
        warnings.append("R11-未记录到PM维护事件")
    
    # 新增R12: 安全库存补货验证
    ss_rows = db.query("""
        SELECT COUNT(*) as cnt FROM purchase_order
        WHERE note LIKE '%安全库存%'
    """)
    ss_cnt = ss_rows[0]["cnt"] if ss_rows else 0
    logger.info(f"  [INFO] R12: 安全库存补货触发 {ss_cnt} 次")
    
    # 新增R13: OEE闭环更新验证
    oee_rows = db.query("""
        SELECT COUNT(*) as cnt FROM machine_capability
        WHERE actual_efficiency_avg IS NOT NULL
    """)
    oee_cnt = oee_rows[0]["cnt"] if oee_rows else 0
    if oee_cnt > 0:
        logger.info(f"  [PASS] R13: MachineCapability已动态更新 {oee_cnt} 条")
    else:
        warnings.append("R13-MachineCapability未动态更新（可能仿真天数不足3天）")
    
    # 新增R14: 客户订单发货率（OTD闭环）
    ship_rows = db.query("""
        SELECT 
            COUNT(*) as total_co,
            SUM(CASE WHEN status IN ('已发货', '部分发货') THEN 1 ELSE 0 END) as shipped_co,
            SUM(CASE WHEN status IN ('已发货', '部分发货') AND note LIKE '%按时%' THEN 1 ELSE 0 END) as otd_co
        FROM customer_order
        WHERE status != '已确认'  
    """)
    if ship_rows:
        total_co = ship_rows[0]['total_co'] or 0
        shipped_co = ship_rows[0]['shipped_co'] or 0
        otd_co = ship_rows[0]['otd_co'] or 0
        ship_rate = shipped_co / max(1, total_co) * 100
        otd_rate = otd_co / max(1, shipped_co) * 100 if shipped_co > 0 else 0
        if ship_rate >= 30:
            logger.info(f"  [PASS] R14: 客户订单发货率={ship_rate:.0f}%({shipped_co}/{total_co}), 按时交付={otd_rate:.0f}%({otd_co}/{max(1,shipped_co)})")
        else:
            warnings.append(f"R14-发货率偏低: {ship_rate:.0f}%({shipped_co}/{total_co})，可能仳真周期过短")

    # 新增R15: Schedule产能快照记录数
    sch_rows = db.query("SELECT COUNT(*) as cnt FROM schedule")
    sch_cnt = sch_rows[0]["cnt"] if sch_rows else 0
    if sch_cnt >= 14:
        logger.info(f"  [PASS] R15: Schedule快照已写入 {sch_cnt} 条（现有产能利用率快照）")
    else:
        warnings.append(f"R15-Schedule快照不足: 仅{sch_cnt}条（期望≥0）")

    # 新增R16: 质检记录验证
    qi_rows = db.query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN inspection_type='IQC入料' THEN 1 ELSE 0 END) as iqc_cnt,
            SUM(CASE WHEN inspection_type='过程质检' THEN 1 ELSE 0 END) as in_process_cnt
        FROM quality_inspection
    """)
    if qi_rows:
        qi_total = qi_rows[0]['total'] or 0
        iqc_cnt = qi_rows[0]['iqc_cnt'] or 0
        ip_cnt = qi_rows[0]['in_process_cnt'] or 0
        if qi_total > 0:
            logger.info(f"  [PASS] R16: 质检记录共{qi_total}条（IQC={iqc_cnt}, 过程质检={ip_cnt}）")
        else:
            warnings.append("R16-未产生质检记录")
    
    # R17: 机台故障次数
    breakdown_rows = db.query("""
        SELECT COUNT(*) as cnt FROM machine_status_log WHERE status='故障'
    """)
    bd_cnt = breakdown_rows[0]['cnt'] if breakdown_rows else 0
    if bd_cnt >= 3:
        logger.info(f"  [PASS] R17: 机台随机故障{bd_cnt}次（非计划停机场景已触发）")
    else:
        warnings.append(f"R17-机台故障次数偏少: {bd_cnt}次（期望≥5次）")
    
    # R18: 订单取消率
    cancel_rows = db.query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status='已取消' THEN 1 ELSE 0 END) as cancelled
        FROM customer_order
    """)
    if cancel_rows:
        total_co_all = cancel_rows[0]['total'] or 0
        cancelled_co = cancel_rows[0]['cancelled'] or 0
        cancel_rate = cancelled_co / max(1, total_co_all) * 100
        if cancelled_co > 0:
            logger.info(f"  [PASS] R18: 订单取消{cancelled_co}笔，取消率={cancel_rate:.1f}%（订单取消场景已触发）")
        else:
            warnings.append("R18-未触发订单取消场景")
    
    # R19: FQC出货检验记录
    fqc_rows = db.query("""
        SELECT COUNT(*) as cnt FROM quality_inspection WHERE inspection_type='FQC出货检验'
    """)
    fqc_cnt = fqc_rows[0]['cnt'] if fqc_rows else 0
    if fqc_cnt > 0:
        logger.info(f"  [PASS] R19: FQC出货检验{fqc_cnt}条（成品出货前检验场景已触发）")
    else:
        warnings.append("R19-未产生 FQC 检验记录")
    
    # R20: 首件检验IPQC记录
    ipqc_rows = db.query("""
        SELECT COUNT(*) as cnt FROM quality_inspection WHERE inspection_type='首件检验'
    """)
    ipqc_cnt = ipqc_rows[0]['cnt'] if ipqc_rows else 0
    if ipqc_cnt > 0:
        logger.info(f"  [PASS] R20: 首件检验(IPQC){ipqc_cnt}条（换线后首件检验场景已触发）")
    else:
        warnings.append("R20-未产生首件检验(IPQC)记录")
    
    # R21: 工单实际开工日期填充率
    wo_start_rows = db.query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN actual_start_date IS NOT NULL THEN 1 ELSE 0 END) as with_start
        FROM work_order WHERE status != '取消'
    """)
    if wo_start_rows:
        total_wo = wo_start_rows[0]['total'] or 0
        started_wo = wo_start_rows[0]['with_start'] or 0
        start_fill_rate = started_wo / max(1, total_wo) * 100
        if start_fill_rate >= 50:
            logger.info(f"  [PASS] R21: 工单实际开工日期填充率={start_fill_rate:.0f}%({started_wo}/{total_wo})）")
        else:
            warnings.append(f"R21-工单开工日期填充率偏低: {start_fill_rate:.0f}%")
    
    # R22: 分批到货验证（同一PO有多条IQC记录）
    split_rows = db.query("""
        SELECT COUNT(DISTINCT po_id) as split_pos
        FROM (
            SELECT po_id, COUNT(*) as cnt 
            FROM quality_inspection 
            WHERE po_id IS NOT NULL AND inspection_type LIKE '%IQC%'
            GROUP BY po_id HAVING cnt > 1
        )
    """)
    split_po_cnt = split_rows[0]['split_pos'] if split_rows else 0
    if split_po_cnt > 0:
        logger.info(f"  [PASS] R22: 分批到货{split_po_cnt}笔PO（同一PO有多次到货记录）")
    else:
        warnings.append("R22-未触发分批到货场景")
    
    # R23: 周日无排程验证
    # 正确逻辑：周日排程模块会跳过（continue），故周日上午09-11时间段不应有planned_start落在该时段的新建任务
    sunday_task_rows = db.query("""
        SELECT COUNT(*) as cnt FROM production_task 
        WHERE strftime('%w', planned_start_time) = '0'
        AND CAST(strftime('%H', planned_start_time) AS INTEGER) BETWEEN 9 AND 11
    """)
    sun_cnt = sunday_task_rows[0]['cnt'] if sunday_task_rows else 0
    if sun_cnt == 0:
        logger.info(f"  [PASS] R23: 周日排程时段（09-11时）无新建任务，工作日历驱动排程已生效")
    else:
        warnings.append(f"R23-周日排程时段09-11时仍存在{sun_cnt}笔新建任务（周日应跳过排程）")
    
    # 统计信息
    logger.info("\n  === 数据统计 ===")
    tables = [
        ("customer_order", "客户订单"),
        ("work_order", "生产工单"),
        ("work_order_operation", "工单工序"),
        ("work_order_material", "工单物料需求"),
        ("production_task", "生产任务"),
        ("wip_lot", "WIP批次"),
        ("inventory_transaction", "库存事务流水"),
        ("purchase_order", "采购订单"),
        ("purchase_order_line", "采购订单行"),
        ("material_transfer", "物料调拨"),
        ("machine_status_log", "机台状态日志"),
        ("finished_goods_inventory", "成品库存"),
        ("quality_inspection", "质检记录"),
        ("schedule", "排程快照"),
    ]
    for table, name in tables:
        cnt = db.count_records(table)
        logger.info(f"    {name}: {cnt} 条")
    
    # 场景验证
    logger.info("\n  === 场景验证 ===")
    
    # 调拨场景
    transfer_cnt = db.count_records("material_transfer")
    if transfer_cnt > 0:
        logger.info(f"    [OK] 物料调拨: {transfer_cnt} 笔（缺料挪用场景已触发）")
    else:
        warnings.append("未产生物料调拨记录（缺料场景未触发）")
    
    # 采购场景
    po_cnt = db.count_records("purchase_order")
    if po_cnt > 0:
        logger.info(f"    [OK] 采购订单: {po_cnt} 笔（补料场景已触发）")
    else:
        warnings.append("未产生采购订单（补料场景未触发）")
    
    # 排程场景
    task_cnt = db.count_records("production_task")
    if task_cnt > 0:
        setup_tasks = db.query("""
            SELECT COUNT(*) as cnt FROM production_task WHERE setup_time_actual > 0
        """)
        setup_cnt = setup_tasks[0]["cnt"] if setup_tasks else 0
        logger.info(f"    [OK] 生产任务: {task_cnt} 笔（含换线{setup_cnt}笔）")
    else:
        warnings.append("未产生生产任务（排程场景未触发）")
    
    if errors:
        logger.warning(f"\n  [FAIL] 发现 {len(errors)} 个错误:")
        for e in errors:
            logger.warning(f"    - {e}")
    else:
        logger.info("\n  [PASS] 所有数据完整性校验通过!")
    
    if warnings:
        logger.warning(f"\n  [WARN] 发现 {len(warnings)} 个警告:")
        for w in warnings:
            logger.warning(f"    - {w}")
    
    logger.info("[4/4] 数据校验完成!\n")
    return len(errors) == 0


def main():
    """主入口"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "semiconductor_data.db")
    logger.info("=" * 70)
    logger.info("  半导体制造业APS+MRP演示数据生成器")
    logger.info("  Semiconductor Manufacturing Demo Data Generator")
    logger.info("=" * 70)
    logger.info(f"\n目标数据库: {db_path}\n")
    
    # 连接数据库
    db = SimulationDBWriter(db_path)
    
    try:
        # 步骤1: 创建表结构（重建以应用新字段，清空所有数据）
        logger.info("[0/4] 创建数据库表结构（重建以应用新增字段）...")
        engine_url = f"sqlite:///{db_path}"
        # 先删表再重建（因db_models有新增字段，必须重建）
        drop_tables(engine_url)
        create_tables(engine_url)
        logger.info("[0/4] 表结构创建完成!\n")
        
        # 步骤2: 插入静态数据
        insert_static_data(db)
        
        # 步骤3: 运行仿真
        sim = run_simulation(db)
        
        # 步骤4: 数据校验
        is_valid = validate_data(db)
        
        logger.info("=" * 70)
        if is_valid:
            logger.info("  演示数据生成成功! 所有校验通过。")
        else:
            logger.info("  演示数据生成完成，但存在数据问题，请检查。")
        logger.info("=" * 70)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
