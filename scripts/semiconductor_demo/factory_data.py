"""
半导体演示工厂静态配置数据
定义产品、BOM、工艺路线、机台、供应商等基础主数据
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Any

# ============================================================================
# 产品定义
# ============================================================================

PRODUCTS = [
    {
        "product_id": "PROD-A",
        "product_name": "智能传感器模块A",
        "product_type": "成品",
        "standard_cycle_time": 2.5,
        "routing_steps": 4,
        "setup_group": "SENSOR-A",
        "unit_of_measure": "PCS"
    },
    {
        "product_id": "PROD-B",
        "product_name": "功率控制芯片B",
        "product_type": "成品",
        "standard_cycle_time": 3.0,
        "routing_steps": 4,
        "setup_group": "POWER-B",
        "unit_of_measure": "PCS"
    },
    {
        "product_id": "PROD-C",
        "product_name": "高端射频芯片C",
        "product_type": "成品",
        "standard_cycle_time": 4.5,
        "routing_steps": 5,
        "setup_group": "RF-C",
        "unit_of_measure": "PCS"
    }
]

# ============================================================================
# 物料定义
# ============================================================================

MATERIALS = [
    {
        "material_id": "MAT-X",
        "material_name": "高精度晶圆基板X",
        "material_type": "原材料",
        "unit_of_measure": "片",
        "safety_stock_level": 30.0,
        "reorder_point": 50.0,
        "lot_size": 100.0,
        "eoq": 80.0,          # P2-13: 经济订购量
        "annual_demand": 1200.0,   # 年需求量（用于EOQ计算）
        "holding_cost_rate": 0.25, # 持有成本率
    },
    {
        "material_id": "MAT-Y",
        "material_name": "传感器封装材料Y",
        "material_type": "原材料",
        "unit_of_measure": "KG",
        "safety_stock_level": 20.0,
        "reorder_point": 40.0,
        "lot_size": 80.0,
        "eoq": 60.0,
        "annual_demand": 800.0,
        "holding_cost_rate": 0.20,
    },
    {
        "material_id": "MAT-Z",
        "material_name": "功率模块散热片Z",
        "material_type": "原材料",
        "unit_of_measure": "PCS",
        "safety_stock_level": 25.0,
        "reorder_point": 45.0,
        "lot_size": 90.0,
        "eoq": 70.0,
        "annual_demand": 900.0,
        "holding_cost_rate": 0.22,
    },
    {
        "material_id": "MAT-COMMON",
        "material_name": "通用清洗溶剂",
        "material_type": "辅料",
        "unit_of_measure": "L",
        "safety_stock_level": 100.0,
        "reorder_point": 200.0,
        "lot_size": 500.0,
        "eoq": 400.0,
        "annual_demand": 5000.0,
        "holding_cost_rate": 0.15,
    },
    {
        "material_id": "MAT-W",
        "material_name": "RF射频胶W",
        "material_type": "原材料",
        "unit_of_measure": "ML",
        "safety_stock_level": 15.0,
        "reorder_point": 30.0,
        "lot_size": 50.0,
        "eoq": 45.0,
        "annual_demand": 600.0,
        "holding_cost_rate": 0.30,
    },
    {
        "material_id": "MAT-V",
        "material_name": "导电银浆V",
        "material_type": "原材料",
        "unit_of_measure": "G",
        "safety_stock_level": 20.0,
        "reorder_point": 35.0,
        "lot_size": 60.0,
        "eoq": 50.0,
        "annual_demand": 700.0,
        "holding_cost_rate": 0.28,
    }
]

# ============================================================================
# BOM定义（含工序关联）
# ============================================================================

BOMS = [
    # PROD-A 的BOM
    {"bom_id": "BOM-A-001", "product_id": "PROD-A", "material_id": "MAT-X", "step_id": "STEP-A-20", "quantity_per_unit": 1.0, "is_critical": True, "consumption_pattern": "工序开始时消耗"},
    {"bom_id": "BOM-A-002", "product_id": "PROD-A", "material_id": "MAT-Y", "step_id": "STEP-A-30", "quantity_per_unit": 0.5, "is_critical": True, "consumption_pattern": "工序开始时消耗"},
    {"bom_id": "BOM-A-003", "product_id": "PROD-A", "material_id": "MAT-COMMON", "step_id": "STEP-A-10", "quantity_per_unit": 0.1, "is_critical": False, "consumption_pattern": "按比例消耗"},
    
    # PROD-B 的BOM（共享MAT-X）
    {"bom_id": "BOM-B-001", "product_id": "PROD-B", "material_id": "MAT-X", "step_id": "STEP-B-20", "quantity_per_unit": 1.0, "is_critical": True, "consumption_pattern": "工序开始时消耗"},
    {"bom_id": "BOM-B-002", "product_id": "PROD-B", "material_id": "MAT-Z", "step_id": "STEP-B-30", "quantity_per_unit": 2.0, "is_critical": True, "consumption_pattern": "工序开始时消耗"},
    {"bom_id": "BOM-B-003", "product_id": "PROD-B", "material_id": "MAT-COMMON", "step_id": "STEP-B-10", "quantity_per_unit": 0.15, "is_critical": False, "consumption_pattern": "按比例消耗"},

    # PROD-C 的BOM（高端射频芯片，5道工序，进口料）
    {"bom_id": "BOM-C-001", "product_id": "PROD-C", "material_id": "MAT-X",      "step_id": "STEP-C-10", "quantity_per_unit": 1.2, "is_critical": True,  "consumption_pattern": "工序开始时消耗"},
    {"bom_id": "BOM-C-002", "product_id": "PROD-C", "material_id": "MAT-W",      "step_id": "STEP-C-20", "quantity_per_unit": 2.0, "is_critical": True,  "consumption_pattern": "工序开始时消耗"},
    {"bom_id": "BOM-C-003", "product_id": "PROD-C", "material_id": "MAT-Z",      "step_id": "STEP-C-30", "quantity_per_unit": 1.5, "is_critical": True,  "consumption_pattern": "工序开始时消耗"},
    {"bom_id": "BOM-C-004", "product_id": "PROD-C", "material_id": "MAT-V",      "step_id": "STEP-C-40", "quantity_per_unit": 3.0, "is_critical": True,  "consumption_pattern": "工序开始时消耗"},
    {"bom_id": "BOM-C-005", "product_id": "PROD-C", "material_id": "MAT-COMMON",  "step_id": "STEP-C-10", "quantity_per_unit": 0.2, "is_critical": False, "consumption_pattern": "按比例消耗"},
]

# ============================================================================
# 工艺路线与工序
# ============================================================================

PROCESS_ROUTES = [
    {"route_id": "RT-PROD-A-v1", "product_id": "PROD-A", "route_name": "传感器模块标准工艺", "version": "v1.0", "is_active": True},
    {"route_id": "RT-PROD-B-v1", "product_id": "PROD-B", "route_name": "功率芯片标准工艺", "version": "v1.0", "is_active": True},
    {"route_id": "RT-PROD-C-v1", "product_id": "PROD-C", "route_name": "高端射频芯片工艺", "version": "v1.0", "is_active": True},
]

ROUTE_STEPS = [
    # PROD-A 工艺路线：清洗(10)→光刻(20)→封装(30)→测试(40)
    {"step_id": "STEP-A-10", "route_id": "RT-PROD-A-v1", "sequence_no": 10, "step_name": "晶圆清洗", "operation_type": "加工", "standard_time_hours": 0.5, "machine_type_required": "WC-CLEAN-01", "setup_time_minutes": 15, "material_ready_offset_hours": 1.0, "yield_rate_standard": 0.99,
     "wait_time_hours": 0.5, "transport_time_hours": 0.25, "min_batch_qty": 25, "max_batch_qty": 100},
    {"step_id": "STEP-A-20", "route_id": "RT-PROD-A-v1", "sequence_no": 20, "step_name": "光刻图形化", "operation_type": "加工", "standard_time_hours": 1.5, "machine_type_required": "WC-LITHO-01", "setup_time_minutes": 30, "material_ready_offset_hours": 2.0, "yield_rate_standard": 0.97, "is_critical": True,
     "wait_time_hours": 1.0, "transport_time_hours": 0.5, "min_batch_qty": 25, "max_batch_qty": 50},
    {"step_id": "STEP-A-30", "route_id": "RT-PROD-A-v1", "sequence_no": 30, "step_name": "传感器封装", "operation_type": "加工", "standard_time_hours": 0.8, "machine_type_required": "WC-ASSY-01", "setup_time_minutes": 20, "material_ready_offset_hours": 1.5, "yield_rate_standard": 0.98,
     "wait_time_hours": 0.0, "transport_time_hours": 0.25, "min_batch_qty": 25, "max_batch_qty": 100},
    {"step_id": "STEP-A-40", "route_id": "RT-PROD-A-v1", "sequence_no": 40, "step_name": "功能测试", "operation_type": "检验", "standard_time_hours": 0.3, "machine_type_required": "WC-TEST-01", "setup_time_minutes": 10, "material_ready_offset_hours": 0.5, "yield_rate_standard": 0.99,
     "wait_time_hours": 0.0, "transport_time_hours": 0.0, "min_batch_qty": 25, "max_batch_qty": 200},
    
    # PROD-B 工艺路线：清洗(10)→蜍刻(20)→贴片(30)→测试(40)
    {"step_id": "STEP-B-10", "route_id": "RT-PROD-B-v1", "sequence_no": 10, "step_name": "晶圆清洗", "operation_type": "加工", "standard_time_hours": 0.5, "machine_type_required": "WC-CLEAN-01", "setup_time_minutes": 15, "material_ready_offset_hours": 1.0, "yield_rate_standard": 0.99,
     "wait_time_hours": 0.5, "transport_time_hours": 0.25, "min_batch_qty": 25, "max_batch_qty": 100},
    {"step_id": "STEP-B-20", "route_id": "RT-PROD-B-v1", "sequence_no": 20, "step_name": "等离子蚀刻", "operation_type": "加工", "standard_time_hours": 2.0, "machine_type_required": "WC-ETCH-01", "setup_time_minutes": 45, "material_ready_offset_hours": 2.0, "yield_rate_standard": 0.96, "is_critical": True,
     "wait_time_hours": 1.5, "transport_time_hours": 0.5, "min_batch_qty": 25, "max_batch_qty": 50},
    {"step_id": "STEP-B-30", "route_id": "RT-PROD-B-v1", "sequence_no": 30, "step_name": "功率模块贴片", "operation_type": "加工", "standard_time_hours": 1.0, "machine_type_required": "WC-ASSY-01", "setup_time_minutes": 25, "material_ready_offset_hours": 1.5, "yield_rate_standard": 0.97,
     "wait_time_hours": 0.0, "transport_time_hours": 0.25, "min_batch_qty": 25, "max_batch_qty": 100},
    {"step_id": "STEP-B-40", "route_id": "RT-PROD-B-v1", "sequence_no": 40, "step_name": "电性能测试", "operation_type": "检验", "standard_time_hours": 0.4, "machine_type_required": "WC-TEST-01", "setup_time_minutes": 10, "material_ready_offset_hours": 0.5, "yield_rate_standard": 0.98,
     "wait_time_hours": 0.0, "transport_time_hours": 0.0, "min_batch_qty": 25, "max_batch_qty": 200},

    # PROD-C 工艺路线：清洗(10)→RF溺陈(20)→蜍刻(30)→封徣(40)→RF测试(50)
    {"step_id": "STEP-C-10", "route_id": "RT-PROD-C-v1", "sequence_no": 10, "step_name": "晶圆清洗", "operation_type": "加工", "standard_time_hours": 0.6, "machine_type_required": "WC-CLEAN-01", "setup_time_minutes": 20, "material_ready_offset_hours": 1.0, "yield_rate_standard": 0.99,
     "wait_time_hours": 0.5, "transport_time_hours": 0.25, "min_batch_qty": 25, "max_batch_qty": 75},
    {"step_id": "STEP-C-20", "route_id": "RT-PROD-C-v1", "sequence_no": 20, "step_name": "RF淀积平坦化", "operation_type": "加工", "standard_time_hours": 2.0, "machine_type_required": "WC-LITHO-01", "setup_time_minutes": 60, "material_ready_offset_hours": 3.0, "yield_rate_standard": 0.95, "is_critical": True,
     "wait_time_hours": 1.5, "transport_time_hours": 0.5, "min_batch_qty": 25, "max_batch_qty": 50},
    {"step_id": "STEP-C-30", "route_id": "RT-PROD-C-v1", "sequence_no": 30, "step_name": "高精度蚀刻", "operation_type": "加工", "standard_time_hours": 2.5, "machine_type_required": "WC-ETCH-01", "setup_time_minutes": 60, "material_ready_offset_hours": 2.0, "yield_rate_standard": 0.94, "is_critical": True,
     "wait_time_hours": 2.0, "transport_time_hours": 0.5, "min_batch_qty": 25, "max_batch_qty": 50},
    {"step_id": "STEP-C-40", "route_id": "RT-PROD-C-v1", "sequence_no": 40, "step_name": "射频封装涂布", "operation_type": "加工", "standard_time_hours": 1.2, "machine_type_required": "WC-ASSY-01", "setup_time_minutes": 40, "material_ready_offset_hours": 1.5, "yield_rate_standard": 0.96,
     "wait_time_hours": 0.5, "transport_time_hours": 0.25, "min_batch_qty": 25, "max_batch_qty": 75},
    {"step_id": "STEP-C-50", "route_id": "RT-PROD-C-v1", "sequence_no": 50, "step_name": "高频RF测试", "operation_type": "检验", "standard_time_hours": 0.8, "machine_type_required": "WC-TEST-01", "setup_time_minutes": 20, "material_ready_offset_hours": 0.5, "yield_rate_standard": 0.97,
     "wait_time_hours": 0.0, "transport_time_hours": 0.0, "min_batch_qty": 25, "max_batch_qty": 100},
]

# ============================================================================
# 工作中心与机台
# ============================================================================

WORK_CENTERS = [
    {"work_center_id": "WC-CLEAN-01", "work_center_name": "清洗区", "work_center_type": "前道", "capacity_uom": "小时"},
    {"work_center_id": "WC-LITHO-01", "work_center_name": "光刻区", "work_center_type": "前道", "capacity_uom": "小时"},
    {"work_center_id": "WC-ETCH-01", "work_center_name": "蚀刻区", "work_center_type": "前道", "capacity_uom": "小时"},
    {"work_center_id": "WC-ASSY-01", "work_center_name": "封装组装区", "work_center_type": "后道", "capacity_uom": "小时"},
    {"work_center_id": "WC-TEST-01", "work_center_name": "测试区", "work_center_type": "后道", "capacity_uom": "小时"},
]

MACHINES = [
    # 清洗区 1台
    {"machine_id": "MAC-001", "machine_name": "超声波清洗机001", "machine_type": "清洗设备", "work_center_id": "WC-CLEAN-01", "max_capacity_per_hour": 120, "status": "在线"},
    
    # 光刻区 1台（A产品首选）
    {"machine_id": "MAC-002", "machine_name": "步进光刻机002", "machine_type": "光刻设备", "work_center_id": "WC-LITHO-01", "max_capacity_per_hour": 60, "status": "在线"},
    
    # 蚀刻区 1台（B产品专用）
    {"machine_id": "MAC-003", "machine_name": "ICP蚀刻机003", "machine_type": "蚀刻设备", "work_center_id": "WC-ETCH-01", "max_capacity_per_hour": 50, "status": "在线"},
    
    # 封装区 2台（通用，001和002的类比）
    {"machine_id": "MAC-004", "machine_name": "自动贴片机004", "machine_type": "贴片设备", "work_center_id": "WC-ASSY-01", "max_capacity_per_hour": 80, "status": "在线"},
    {"machine_id": "MAC-005", "machine_name": "高精度贴片机005", "machine_type": "贴片设备", "work_center_id": "WC-ASSY-01", "max_capacity_per_hour": 70, "status": "在线"},
    
    # 测试区 1台
    {"machine_id": "MAC-006", "machine_name": "ATE测试机006", "machine_type": "测试设备", "work_center_id": "WC-TEST-01", "max_capacity_per_hour": 100, "status": "在线"},
]

# ============================================================================
# 机台能力矩阵
# ============================================================================

MACHINE_CAPABILITIES = [
    # MAC-001 清洗机（通用）
    {"capability_id": "MC-001-A", "machine_id": "MAC-001", "product_id": "PROD-A", "efficiency_factor": 1.0, "setup_time_minutes": 15, "yield_rate": 0.99, "is_preferred": True, "rated_speed_per_hour": 120},
    {"capability_id": "MC-001-B", "machine_id": "MAC-001", "product_id": "PROD-B", "efficiency_factor": 1.0, "setup_time_minutes": 15, "yield_rate": 0.99, "is_preferred": True, "rated_speed_per_hour": 120},
    
    # MAC-002 光刻机（A产品效率高，B也能做但效率低）
    {"capability_id": "MC-002-A", "machine_id": "MAC-002", "product_id": "PROD-A", "efficiency_factor": 1.2, "setup_time_minutes": 30, "yield_rate": 0.97, "is_preferred": True, "rated_speed_per_hour": 72},
    {"capability_id": "MC-002-B", "machine_id": "MAC-002", "product_id": "PROD-B", "efficiency_factor": 0.8, "setup_time_minutes": 45, "yield_rate": 0.94, "is_preferred": False, "rated_speed_per_hour": 48},
    
    # MAC-003 蚀刻机（B产品效率高，A也能做但效率低）
    {"capability_id": "MC-003-A", "machine_id": "MAC-003", "product_id": "PROD-A", "efficiency_factor": 0.9, "setup_time_minutes": 40, "yield_rate": 0.95, "is_preferred": False, "rated_speed_per_hour": 45},
    {"capability_id": "MC-003-B", "machine_id": "MAC-003", "product_id": "PROD-B", "efficiency_factor": 1.3, "setup_time_minutes": 45, "yield_rate": 0.96, "is_preferred": True, "rated_speed_per_hour": 65},
    
    # MAC-004 贴片机（A效率高）
    {"capability_id": "MC-004-A", "machine_id": "MAC-004", "product_id": "PROD-A", "efficiency_factor": 1.1, "setup_time_minutes": 20, "yield_rate": 0.98, "is_preferred": True, "rated_speed_per_hour": 88},
    {"capability_id": "MC-004-B", "machine_id": "MAC-004", "product_id": "PROD-B", "efficiency_factor": 0.9, "setup_time_minutes": 30, "yield_rate": 0.96, "is_preferred": False, "rated_speed_per_hour": 72},
    
    # MAC-005 贴片机（B效率高）
    {"capability_id": "MC-005-A", "machine_id": "MAC-005", "product_id": "PROD-A", "efficiency_factor": 0.85, "setup_time_minutes": 25, "yield_rate": 0.97, "is_preferred": False, "rated_speed_per_hour": 59.5},
    {"capability_id": "MC-005-B", "machine_id": "MAC-005", "product_id": "PROD-B", "efficiency_factor": 1.25, "setup_time_minutes": 25, "yield_rate": 0.98, "is_preferred": True, "rated_speed_per_hour": 87.5},
    
    # MAC-006 测试机（通用）
    {"capability_id": "MC-006-A", "machine_id": "MAC-006", "product_id": "PROD-A", "efficiency_factor": 1.0, "setup_time_minutes": 10, "yield_rate": 0.99, "is_preferred": True, "rated_speed_per_hour": 100},
    {"capability_id": "MC-006-B", "machine_id": "MAC-006", "product_id": "PROD-B", "efficiency_factor": 1.0, "setup_time_minutes": 10, "yield_rate": 0.98, "is_preferred": True, "rated_speed_per_hour": 100},
    {"capability_id": "MC-006-C", "machine_id": "MAC-006", "product_id": "PROD-C", "efficiency_factor": 0.9, "setup_time_minutes": 20, "yield_rate": 0.97, "is_preferred": True, "rated_speed_per_hour": 90},

    # PROD-C 附加能力
    {"capability_id": "MC-001-C", "machine_id": "MAC-001", "product_id": "PROD-C", "efficiency_factor": 0.95, "setup_time_minutes": 20, "yield_rate": 0.99, "is_preferred": True, "rated_speed_per_hour": 114},
    {"capability_id": "MC-002-C", "machine_id": "MAC-002", "product_id": "PROD-C", "efficiency_factor": 1.1,  "setup_time_minutes": 60, "yield_rate": 0.95, "is_preferred": True, "rated_speed_per_hour": 66},
    {"capability_id": "MC-003-C", "machine_id": "MAC-003", "product_id": "PROD-C", "efficiency_factor": 1.2,  "setup_time_minutes": 60, "yield_rate": 0.94, "is_preferred": True, "rated_speed_per_hour": 60},
    {"capability_id": "MC-004-C", "machine_id": "MAC-004", "product_id": "PROD-C", "efficiency_factor": 0.85, "setup_time_minutes": 40, "yield_rate": 0.96, "is_preferred": False, "rated_speed_per_hour": 68},
    {"capability_id": "MC-005-C", "machine_id": "MAC-005", "product_id": "PROD-C", "efficiency_factor": 1.0,  "setup_time_minutes": 40, "yield_rate": 0.97, "is_preferred": True, "rated_speed_per_hour": 70},
]

# ============================================================================
# 换线矩阵 SetupMatrix
# ============================================================================

SETUP_MATRIX = [
    # MAC-002 光刻机换线矩阵
    {"matrix_id": "SM-002-AA", "machine_id": "MAC-002", "from_product_id": "PROD-A", "to_product_id": "PROD-A", "setup_time_minutes": 0, "setup_type": "无需换线"},
    {"matrix_id": "SM-002-AB", "machine_id": "MAC-002", "from_product_id": "PROD-A", "to_product_id": "PROD-B", "setup_time_minutes": 45, "setup_type": "换模+校准"},
    {"matrix_id": "SM-002-BA", "machine_id": "MAC-002", "from_product_id": "PROD-B", "to_product_id": "PROD-A", "setup_time_minutes": 35, "setup_type": "换模"},
    {"matrix_id": "SM-002-BB", "machine_id": "MAC-002", "from_product_id": "PROD-B", "to_product_id": "PROD-B", "setup_time_minutes": 0, "setup_type": "无需换线"},
    
    # MAC-003 蚀刻机换线矩阵
    {"matrix_id": "SM-003-AA", "machine_id": "MAC-003", "from_product_id": "PROD-A", "to_product_id": "PROD-A", "setup_time_minutes": 0, "setup_type": "无需换线"},
    {"matrix_id": "SM-003-AB", "machine_id": "MAC-003", "from_product_id": "PROD-A", "to_product_id": "PROD-B", "setup_time_minutes": 40, "setup_type": "气体切换"},
    {"matrix_id": "SM-003-BA", "machine_id": "MAC-003", "from_product_id": "PROD-B", "to_product_id": "PROD-A", "setup_time_minutes": 50, "setup_type": "气体切换+清洗"},
    {"matrix_id": "SM-003-BB", "machine_id": "MAC-003", "from_product_id": "PROD-B", "to_product_id": "PROD-B", "setup_time_minutes": 0, "setup_type": "无需换线"},
    
    # MAC-004 贴片机换线矩阵
    {"matrix_id": "SM-004-AA", "machine_id": "MAC-004", "from_product_id": "PROD-A", "to_product_id": "PROD-A", "setup_time_minutes": 0, "setup_type": "无需换线"},
    {"matrix_id": "SM-004-AB", "machine_id": "MAC-004", "from_product_id": "PROD-A", "to_product_id": "PROD-B", "setup_time_minutes": 30, "setup_type": "吸嘴更换"},
    {"matrix_id": "SM-004-BA", "machine_id": "MAC-004", "from_product_id": "PROD-B", "to_product_id": "PROD-A", "setup_time_minutes": 25, "setup_type": "吸嘴更换"},
    {"matrix_id": "SM-004-BB", "machine_id": "MAC-004", "from_product_id": "PROD-B", "to_product_id": "PROD-B", "setup_time_minutes": 0, "setup_type": "无需换线"},
    
    # MAC-005 贴片机换线矩阵
    {"matrix_id": "SM-005-AA", "machine_id": "MAC-005", "from_product_id": "PROD-A", "to_product_id": "PROD-A", "setup_time_minutes": 0,  "setup_type": "无需换线"},
    {"matrix_id": "SM-005-AB", "machine_id": "MAC-005", "from_product_id": "PROD-A", "to_product_id": "PROD-B", "setup_time_minutes": 35, "setup_type": "吸嘴更换+校准"},
    {"matrix_id": "SM-005-BA", "machine_id": "MAC-005", "from_product_id": "PROD-B", "to_product_id": "PROD-A", "setup_time_minutes": 30, "setup_type": "吸嘴更换"},
    {"matrix_id": "SM-005-BB", "machine_id": "MAC-005", "from_product_id": "PROD-B", "to_product_id": "PROD-B", "setup_time_minutes": 0,  "setup_type": "无需换线"},

    # PROD-C 换线矩阵（岄频产品换线时间更长）
    {"matrix_id": "SM-002-AC", "machine_id": "MAC-002", "from_product_id": "PROD-A", "to_product_id": "PROD-C", "setup_time_minutes": 75, "setup_type": "光居对测+全校准"},
    {"matrix_id": "SM-002-CA", "machine_id": "MAC-002", "from_product_id": "PROD-C", "to_product_id": "PROD-A", "setup_time_minutes": 60, "setup_type": "幣片更换"},
    {"matrix_id": "SM-002-BC", "machine_id": "MAC-002", "from_product_id": "PROD-B", "to_product_id": "PROD-C", "setup_time_minutes": 80, "setup_type": "光居对测+全校准"},
    {"matrix_id": "SM-002-CB", "machine_id": "MAC-002", "from_product_id": "PROD-C", "to_product_id": "PROD-B", "setup_time_minutes": 70, "setup_type": "幣片更换"},
    {"matrix_id": "SM-002-CC", "machine_id": "MAC-002", "from_product_id": "PROD-C", "to_product_id": "PROD-C", "setup_time_minutes": 0,  "setup_type": "无需换线"},
    {"matrix_id": "SM-003-AC", "machine_id": "MAC-003", "from_product_id": "PROD-A", "to_product_id": "PROD-C", "setup_time_minutes": 70, "setup_type": "气体切换+清洗"},
    {"matrix_id": "SM-003-CA", "machine_id": "MAC-003", "from_product_id": "PROD-C", "to_product_id": "PROD-A", "setup_time_minutes": 60, "setup_type": "气体切换"},
    {"matrix_id": "SM-003-BC", "machine_id": "MAC-003", "from_product_id": "PROD-B", "to_product_id": "PROD-C", "setup_time_minutes": 55, "setup_type": "气体切换+公差调整"},
    {"matrix_id": "SM-003-CB", "machine_id": "MAC-003", "from_product_id": "PROD-C", "to_product_id": "PROD-B", "setup_time_minutes": 50, "setup_type": "公差调整"},
    {"matrix_id": "SM-003-CC", "machine_id": "MAC-003", "from_product_id": "PROD-C", "to_product_id": "PROD-C", "setup_time_minutes": 0,  "setup_type": "无需换线"},
    {"matrix_id": "SM-004-AC", "machine_id": "MAC-004", "from_product_id": "PROD-A", "to_product_id": "PROD-C", "setup_time_minutes": 50, "setup_type": "吸嘴更换+校准"},
    {"matrix_id": "SM-004-CA", "machine_id": "MAC-004", "from_product_id": "PROD-C", "to_product_id": "PROD-A", "setup_time_minutes": 45, "setup_type": "吸嘴更换"},
    {"matrix_id": "SM-004-BC", "machine_id": "MAC-004", "from_product_id": "PROD-B", "to_product_id": "PROD-C", "setup_time_minutes": 55, "setup_type": "吸嘴更换+校准"},
    {"matrix_id": "SM-004-CB", "machine_id": "MAC-004", "from_product_id": "PROD-C", "to_product_id": "PROD-B", "setup_time_minutes": 50, "setup_type": "吸嘴更换"},
    {"matrix_id": "SM-004-CC", "machine_id": "MAC-004", "from_product_id": "PROD-C", "to_product_id": "PROD-C", "setup_time_minutes": 0,  "setup_type": "无需换线"},
    {"matrix_id": "SM-005-AC", "machine_id": "MAC-005", "from_product_id": "PROD-A", "to_product_id": "PROD-C", "setup_time_minutes": 55, "setup_type": "吸嘴更换+校准"},
    {"matrix_id": "SM-005-CA", "machine_id": "MAC-005", "from_product_id": "PROD-C", "to_product_id": "PROD-A", "setup_time_minutes": 48, "setup_type": "吸嘴更换"},
    {"matrix_id": "SM-005-BC", "machine_id": "MAC-005", "from_product_id": "PROD-B", "to_product_id": "PROD-C", "setup_time_minutes": 50, "setup_type": "吸嘴更换+校准"},
    {"matrix_id": "SM-005-CB", "machine_id": "MAC-005", "from_product_id": "PROD-C", "to_product_id": "PROD-B", "setup_time_minutes": 45, "setup_type": "吸嘴更换"},
    {"matrix_id": "SM-005-CC", "machine_id": "MAC-005", "from_product_id": "PROD-C", "to_product_id": "PROD-C", "setup_time_minutes": 0,  "setup_type": "无需换线"},
]

# ============================================================================
# 供应商定义
# ============================================================================

SUPPLIERS = [
    {"supplier_id": "SUP-001", "supplier_name": "晶圆科技(苏州)", "supplier_type": "直供", "avg_lead_time_days": 3, "reliability_score": 0.95, "min_order_quantity": 50.0,
     "lead_time_stddev_days": 0.5},   # P0-3: 交期标准差（扩张属）
    {"supplier_id": "SUP-002", "supplier_name": "新材料贸易(深圳)", "supplier_type": "代理商", "avg_lead_time_days": 5, "reliability_score": 0.88, "min_order_quantity": 30.0,
     "lead_time_stddev_days": 1.5},   # P0-3: 代理商交期波动更大
    {"supplier_id": "SUP-003", "supplier_name": "TechMat国际(进口)", "supplier_type": "进口商", "avg_lead_time_days": 15, "reliability_score": 0.80, "min_order_quantity": 20.0,
     "lead_time_stddev_days": 3.0},   # 进口料交期长、波动大、风险高
]

SUPPLIER_MATERIALS = [
    # MAT-X 晶圆基板
    {"sm_id": "SM-001-X", "supplier_id": "SUP-001", "material_id": "MAT-X", "unit_price": 150.0, "lead_time_days": 3, "min_order_qty": 50.0, "is_preferred": True},
    {"sm_id": "SM-002-X", "supplier_id": "SUP-002", "material_id": "MAT-X", "unit_price": 135.0, "lead_time_days": 5, "min_order_qty": 30.0, "is_preferred": False},
    
    # MAT-Y 封装材料
    {"sm_id": "SM-001-Y", "supplier_id": "SUP-001", "material_id": "MAT-Y", "unit_price": 80.0, "lead_time_days": 2, "min_order_qty": 40.0, "is_preferred": True},
    
    # MAT-Z 散热片
    {"sm_id": "SM-002-Z", "supplier_id": "SUP-002", "material_id": "MAT-Z", "unit_price": 25.0, "lead_time_days": 4, "min_order_qty": 60.0, "is_preferred": True},
    
    # MAT-COMMON 通用溶剂
    {"sm_id": "SM-001-C", "supplier_id": "SUP-001", "material_id": "MAT-COMMON", "unit_price": 15.0, "lead_time_days": 1, "min_order_qty": 100.0, "is_preferred": True},

    # MAT-W RF射频胶（进口料）
    {"sm_id": "SM-003-W", "supplier_id": "SUP-003", "material_id": "MAT-W", "unit_price": 320.0, "lead_time_days": 15, "min_order_qty": 20.0, "is_preferred": True},
    {"sm_id": "SM-002-W", "supplier_id": "SUP-002", "material_id": "MAT-W", "unit_price": 380.0, "lead_time_days": 8,  "min_order_qty": 15.0, "is_preferred": False},

    # MAT-V 导电銀浆（进口料）
    {"sm_id": "SM-003-V", "supplier_id": "SUP-003", "material_id": "MAT-V", "unit_price": 450.0, "lead_time_days": 15, "min_order_qty": 20.0, "is_preferred": True},
]

MATERIAL_SUBSTITUTES = [
    {"ms_id": "MS-001", "material_id": "MAT-X", "substitute_material_id": "MAT-Y", "substitute_priority": 2, "quality_grade": "降规使用", "approval_status": "客户批准", "cost_delta_percent": -10.0},
]

# ============================================================================
# 班次定义
# ============================================================================

SHIFT_PATTERNS = [
    {"shift_id": "SHIFT-DAY", "shift_name": "白班", "start_time": "08:00", "end_time": "20:00", "available_hours": 12.0, "efficiency_factor": 1.0},
    {"shift_id": "SHIFT-NIGHT", "shift_name": "夜班", "start_time": "20:00", "end_time": "08:00", "available_hours": 12.0, "efficiency_factor": 0.92},
]

# ============================================================================
# 初始库存
# ============================================================================

INITIAL_INVENTORY = [
    {"material_id": "MAT-X", "location": "原材料仓A", "total_quantity": 80.0, "available_quantity": 80.0, "reserved_quantity": 0.0},
    {"material_id": "MAT-Y", "location": "原材料仓A", "total_quantity": 60.0, "available_quantity": 60.0, "reserved_quantity": 0.0},
    {"material_id": "MAT-Z", "location": "原材料仓B", "total_quantity": 55.0, "available_quantity": 55.0, "reserved_quantity": 0.0},
    {"material_id": "MAT-COMMON", "location": "辅料仓",  "total_quantity": 250.0, "available_quantity": 250.0, "reserved_quantity": 0.0},
    {"material_id": "MAT-W", "location": "进口料仓",  "total_quantity": 25.0, "available_quantity": 25.0, "reserved_quantity": 0.0},
    {"material_id": "MAT-V", "location": "进口料仓",  "total_quantity": 30.0, "available_quantity": 30.0, "reserved_quantity": 0.0},
]

# ============================================================================
# 仿真参数
# ============================================================================

SIMULATION_CONFIG = {
    "duration_days": 60,
    "day_start_hour": 8,
    "day_end_hour": 20,
    "order_arrival_lambda": 2.5,  # 每天平均2.5个客户订单（泊松分布）
    "order_quantity_min": 5,
    "order_quantity_max": 80,
    "lead_time_commitment_days": 7,  # 承诺交期（客户下单后7天交付）
    "wip_lot_size": 25,  # 每个Lot 25片
    "maintenance_frequency_hours": 168,  # 每周维护一次
    "maintenance_duration_hours": 4,
    # P2-11: 安全库存补4小时检查一次
    "safety_stock_check_interval_hours": 4,
    # P1-8: 排程算法参数
    "setup_cost_weight": 2.0,       # 换线成本权重（相对于1小时加工时间）
    "critical_ratio_threshold": 1.1, # 关键比阈値（<1.1访紧急处理）
    # P2-12: CTP产能负荷参数
    "ctp_capacity_buffer": 0.15,    # 产能缓冲系数（15%保留给算法排程不确定性）
    # Task3: 机台随机故障参数
    "breakdown_mtbf_hours": 96,    # 平均无故障时间(MTBF)
    "breakdown_mttr_hours": 4,     # 平均修复时间(MTTR)
    "breakdown_probability": 0.70, # 机台产生随机故障的基础概率
    # Task5: 订单取消参数
    "order_cancel_daily_prob": 0.20,         # 每天对未开工订单的取消概率（20%确保场景触发）
    # Task6: 分批到货参数
    "split_delivery_prob": 0.30,             # 分批到货概率
    # Task10: 订单优先级动态升级
    "priority_escalation_daily_prob": 0.08,  # 每天紧急插单概率
}


def generate_work_calendar(start_date: datetime, days: int) -> List[Dict]:
    """生成班次日历（简化：周一到周六工作，周日休息）"""
    calendar = []
    shift_ids = ["SHIFT-DAY", "SHIFT-NIGHT"]
    work_centers = [wc["work_center_id"] for wc in WORK_CENTERS]
    
    for i in range(days):
        date = (start_date + timedelta(days=i)).date()
        is_workday = date.weekday() < 6  # 周一到周六工作
        
        for wc_id in work_centers:
            for shift_id in shift_ids:
                cal_id = f"CAL-{date.strftime('%Y%m%d')}-{wc_id}-{shift_id}"
                calendar.append({
                    "calendar_id": cal_id,
                    "calendar_date": date,
                    "work_center_id": wc_id,
                    "shift_id": shift_id,
                    "is_workday": is_workday,
                    "available_hours": 12.0 if is_workday else 0.0,
                    "planned_capacity": 100.0 if is_workday else 0.0,
                    "note": "周末休息" if not is_workday else None
                })
    return calendar
