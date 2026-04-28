"""
通富微电风格封装测试工厂静态配置数据 v2.0
100个产品 / 80-120道工序 / 2-3层BOM / 25个工作中心
OSAT封装测试代工：BGA/QFN/SOP/QFP/WLCSP/Fan-out/SiP/LGA/CSP/SOT
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

# ============================================================================
# 通用工序类型定义 (短代码 -> 工作中心, 标准时间小时, 良率)
# 修正：改为Lot批量加工时间（lot_size=25），贴合OSAT真实生产模式
PT = {
    # 前段（批量加工，时间÷25）
    "RECV":  ("WC-RECV",     0.5,  1.00),  # 保持不变（收货是批次操作）
    "GRIND": ("WC-GRIND",    0.08, 0.99),  # 2.0/25=0.08
    "DICE":  ("WC-DICE",     0.06, 0.98),  # 1.5/25=0.06
    "DA":    ("WC-DA",       0.04, 0.99),  # 1.0/25=0.04
    "CURE":  ("WC-DA",       0.08, 1.00),  # 2.0/25=0.08
    # 中段（键合是逐个的，但机台多线并行）
    "WB":    ("WC-WB",       0.4,  0.97),  # 2.0/5线=0.4（5线并行）
    "FC":    ("WC-FC",       0.3,  0.98),  # 1.5/5=0.3
    "RDL":   ("WC-RDL",      0.4,  0.98),  # 2.0/5=0.4
    # 塑封（批量）
    "MOLD":  ("WC-MOLD",     0.12, 0.98),  # 3.0/25=0.12
    "PMC":   ("WC-PMC",      0.16, 1.00),  # 4.0/25=0.16
    "MARK":  ("WC-MARK",     0.01, 1.00),  # 0.3/25=0.012
    # 植球（批量）
    "BALL":  ("WC-BALL",     0.06, 0.99),  # 1.5/25=0.06
    "REFL":  ("WC-BALL",     0.04, 1.00),  # 1.0/25=0.04
    "SING":  ("WC-SING",     0.04, 0.99),  # 1.0/25=0.04
    # 检测（逐件但高速）
    "AOI":   ("WC-AOI",      0.02, 1.00),  # 0.5/25=0.02
    "VISUAL":("WC-VISUAL",   0.02, 0.99),  # 0.5/25=0.02
    "XRAY":  ("WC-XRAY",     0.02, 1.00),  # 0.5/25=0.02
    "SAM":   ("WC-SAM",      0.04, 1.00),  # 1.0/25=0.04
    # 测试（并行测试）
    "CP":    ("WC-TEST-CP",  0.4,  0.95),  # 2.0/5并行=0.4
    "DC":    ("WC-TEST-FT",  0.3,  0.96),  # 1.5/5=0.3
    "AC":    ("WC-TEST-FT",  0.3,  0.96),  # 1.5/5=0.3
    "FUNC":  ("WC-TEST-FT",  0.4,  0.95),  # 2.0/5=0.4
    "BI":    ("WC-TEST-BI",  0.96, 0.98),  # 24.0/25并行=0.96（关键修正！）
    "BIT":   ("WC-TEST-FT",  0.4,  0.97),  # 2.0/5=0.4
    "FINAL": ("WC-TEST-FT",  0.1,  0.97),  # 2.5/25=0.1
    "SYS":   ("WC-TEST-SYS", 0.8,  0.95),  # 4.0/5=0.8
    # 辅助（批量）
    "CLEAN": ("WC-CLEAN",    0.01, 1.00),  # 0.3/25=0.012
    "DRY":   ("WC-CLEAN",    0.02, 1.00),  # 0.5/25=0.02
    "BAKE":  ("WC-BAKE",     0.16, 1.00),  # 4.0/25=0.16
    "WAIT":  ("WC-WAIT",     0.04, 1.00),  # 1.0/25=0.04
    "TRANS": ("WC-TRANS",    0.01, 1.00),  # 0.2/25=0.008
    # 出货（批量）
    "OQC":   ("WC-PACK",     0.02, 0.99),  # 0.5/25=0.02
    "PACK":  ("WC-PACK",     0.02, 1.00),  # 0.5/25=0.02
    "LABEL": ("WC-PACK",     0.01, 1.00),  # 0.2/25=0.008
    "STORE": ("WC-PACK",     0.01, 1.00),  # 0.2/25=0.008
}

# ============================================================================
# 封装类型配置
# ============================================================================

PKG_CFG = {
    "BGA":    {"name": "球栅阵列封装",      "bond": 5, "ball": True,  "rdl": False, "test": 5, "steps": 92},
    "QFN":    {"name": "方形扁平无引脚",     "bond": 3, "ball": False, "rdl": False, "test": 4, "steps": 78},
    "SOP":    {"name": "小外形封装",         "bond": 2, "ball": False, "rdl": False, "test": 3, "steps": 65},
    "QFP":    {"name": "方形扁平封装",       "bond": 4, "ball": False, "rdl": False, "test": 4, "steps": 72},
    "WLCSP":  {"name": "晶圆级CSP",          "bond": 0, "ball": True,  "rdl": True,  "test": 4, "steps": 85},
    "FANOUT": {"name": "扇出型封装",         "bond": 0, "ball": True,  "rdl": True,  "test": 5, "steps": 95},
    "SIP":    {"name": "系统级封装",         "bond": 6, "ball": True,  "rdl": False, "test": 6, "steps": 105},
    "LGA":    {"name": "平面网格阵列",       "bond": 4, "ball": False, "rdl": False, "test": 4, "steps": 80},
    "CSP":    {"name": "芯片尺寸封装",       "bond": 3, "ball": True,  "rdl": False, "test": 3, "steps": 75},
    "SOT":    {"name": "小外形晶体管",       "bond": 1, "ball": False, "rdl": False, "test": 2, "steps": 58},
}

CHIP_TYPES = ["CPU", "GPU", "MEM", "RF", "ASIC", "MCU", "SENSOR", "PMIC", "FPGA", "NET"]
CHIP_NAMES = {"CPU": "处理器", "GPU": "图形芯片", "MEM": "存储芯片", "RF": "射频芯片",
              "ASIC": "专用集成电路", "MCU": "微控制器", "SENSOR": "传感器",
              "PMIC": "电源管理", "FPGA": "可编程逻辑", "NET": "网络芯片"}

# ============================================================================
# 工序流构建函数
# ============================================================================

def _front_end() -> List[str]:
    """前段：晶圆处理 (13道)"""
    return ["RECV", "RECV", "RECV", "BAKE", "WAIT", "GRIND", "AOI", "CLEAN", "DRY", "AOI", "DICE", "DICE", "DICE"]

def _die_attach() -> List[str]:
    """贴片 (5道)"""
    return ["DA", "CURE", "AOI", "CLEAN", "TRANS"]

def _wire_bond(positions: int) -> List[str]:
    """引线键合：每位置4道"""
    out = []
    for _ in range(positions):
        out += ["WB", "AOI", "CLEAN", "TRANS"]
    return out

def _rdl_flow() -> List[str]:
    """RDL/UBM流程 (WLCSP/Fan-out) 8道"""
    return ["RDL", "AOI", "CLEAN", "TRANS", "RDL", "AOI", "CLEAN", "TRANS"]

def _molding() -> List[str]:
    """塑封段 (10道)"""
    return ["AOI", "CLEAN", "TRANS", "BAKE", "WAIT", "MOLD", "PMC", "WAIT", "CLEAN", "TRANS"]

def _marking() -> List[str]:
    """打标 (3道)"""
    return ["MARK", "CLEAN", "TRANS"]

def _ball_attach() -> List[str]:
    """植球 (4道)"""
    return ["BALL", "REFL", "CLEAN", "TRANS"]

def _inspection_singulation(has_sam: bool) -> List[str]:
    """检测与分选 (9-10道)"""
    out = ["XRAY", "TRANS"]
    out += ["SAM", "TRANS"] if has_sam else ["TRANS", "TRANS"]
    out += ["SING", "CLEAN", "TRANS", "VISUAL", "TRANS"]
    return out

def _test_flow(test_stations: int) -> List[str]:
    """测试段 (2*test_stations 道)"""
    test_types = ["CP", "DC", "AC", "FUNC", "FINAL", "FINAL", "FINAL", "SYS", "BI"]
    out = []
    for i in range(min(test_stations, len(test_types))):
        out += [test_types[i], "TRANS"]
    return out

def _burn_in(has_bi: bool) -> List[str]:
    """老化测试 (3道或0道)"""
    return ["BI", "BIT", "TRANS"] if has_bi else []

def _final_extra(extra: int) -> List[str]:
    """补充最终测试"""
    out = []
    for _ in range(extra):
        out += ["FINAL", "TRANS"]
    return out

def _sys_test(has_sys: bool) -> List[str]:
    """系统测试 (2道或0道)"""
    return ["SYS", "TRANS"] if has_sys else []

def _shipping(has_xray: bool) -> List[str]:
    """出货前 (8-9道)"""
    out = ["VISUAL", "TRANS"]
    out += ["XRAY", "TRANS"] if has_xray else ["TRANS", "TRANS"]
    out += ["OQC", "PACK", "LABEL", "STORE", "TRANS"]
    return out

def build_flow(cfg: dict) -> List[str]:
    """根据封装配置构建完整工序流（含大量辅助工序以达到80-120道）"""
    flow = []
    # 前段 + 辅助
    flow += _front_end() + ["TRANS", "WAIT"]
    flow += _die_attach() + ["TRANS", "WAIT"]
    # 中段：键合/RDL + 辅助
    if cfg["rdl"]:
        flow += _rdl_flow() + ["BAKE", "WAIT", "CLEAN", "TRANS"]
    elif cfg["bond"] > 0:
        flow += _wire_bond(cfg["bond"]) + ["BAKE", "WAIT", "CLEAN", "TRANS"]
    # 塑封段 + 辅助
    flow += _molding() + ["CLEAN", "TRANS", "WAIT", "CLEAN", "TRANS"]
    # 打标 + 辅助
    flow += _marking() + ["TRANS", "WAIT"]
    # 植球 + 辅助
    if cfg["ball"]:
        flow += _ball_attach() + ["CLEAN", "TRANS", "BAKE", "WAIT"]
    # 检测分选 + 辅助
    flow += _inspection_singulation(cfg["steps"] > 80) + ["TRANS", "WAIT", "CLEAN", "TRANS"]
    # 测试段 + 辅助
    flow += _test_flow(cfg["test"]) + ["TRANS", "WAIT", "CLEAN", "TRANS"]
    # 老化 + 辅助
    flow += _burn_in(cfg["steps"] > 70) + ["TRANS", "WAIT"]
    # 补充测试 + 辅助
    flow += _final_extra(max(0, cfg["test"] - 5))
    flow += _sys_test(cfg["test"] >= 5 and cfg["steps"] > 85)
    flow += ["TRANS", "WAIT", "CLEAN", "TRANS"]
    # 出货前处理 + 出货
    flow += ["CLEAN", "TRANS", "BAKE", "WAIT", "CLEAN", "TRANS"]
    flow += _shipping(cfg["steps"] > 70)
    return flow

# ============================================================================
# 产品生成
# ============================================================================

def generate_products() -> List[Dict]:
    products = []
    for pkg, cfg in PKG_CFG.items():
        for chip in CHIP_TYPES:
            pid = f"{pkg}-{chip}"
            products.append({
                "product_id": pid,
                "product_name": f"{cfg['name']}-{CHIP_NAMES[chip]}",
                "product_type": "成品",
                "standard_cycle_time": round(cfg["steps"] * 0.08, 2),
                "routing_steps": cfg["steps"],
                "setup_group": pkg,
                "unit_of_measure": "PCS"
            })
    return products

# ============================================================================
# 工艺路线和工序生成 (每个产品独立路线)
# ============================================================================

def generate_routes_and_steps() -> Tuple[List[Dict], List[Dict]]:
    routes, steps = [], []
    for pkg, cfg in PKG_CFG.items():
        flow = build_flow(cfg)
        for chip in CHIP_TYPES:
            pid = f"{pkg}-{chip}"
            rid = f"RT-{pid}-v1"
            routes.append({
                "route_id": rid,
                "product_id": pid,
                "route_name": f"{cfg['name']}标准工艺-{CHIP_NAMES[chip]}",
                "version": "v1.0",
                "is_active": True
            })
            seq = 10
            for code in flow:
                wc, time, yield_rate = PT[code]
                sid = f"STEP-{pid}-{seq:03d}"
                optype = "检验" if code in ("AOI","VISUAL","XRAY","SAM","CP","DC","AC","FUNC","BI","BIT","FINAL","SYS","OQC") else "加工"
                steps.append({
                    "step_id": sid,
                    "route_id": rid,
                    "sequence_no": seq,
                    "step_name": f"{code}-{seq}",
                    "operation_type": optype,
                    "standard_time_hours": time,
                    "machine_type_required": wc,
                    "setup_time_minutes": 20,
                    "material_ready_offset_hours": 1.0,
                    "yield_rate_standard": yield_rate,
                    "wait_time_hours": 0.0,
                    "transport_time_hours": 0.0,
                    "min_batch_qty": 25,
                    "max_batch_qty": 100,
                })
                seq += 10
    return routes, steps

# ============================================================================
# BOM生成 (2-3层)
# ============================================================================

def _bom_l1(pkg: str, chip: str, cfg: dict) -> List[Dict]:
    """BOM第1层：成品直接用料 + 第2层：基板/框架组成材料"""
    pid = f"{pkg}-{chip}"
    boms = []
    # === 第1层：成品直接用料 ===
    # Die
    boms.append({"bom_id": f"BOM-{pid}-DIE", "product_id": pid, "material_id": f"MAT-DIE-{pkg}",
                 "step_id": f"STEP-{pid}-060", "quantity_per_unit": 1.0, "is_critical": True,
                 "consumption_pattern": "工序开始时消耗"})
    # Substrate/Leadframe
    sub_mat = f"MAT-SUB-{pkg}" if pkg in ("BGA","WLCSP","FANOUT","LGA","CSP","SIP") else f"MAT-LF-{pkg}"
    boms.append({"bom_id": f"BOM-{pid}-SUB", "product_id": pid, "material_id": sub_mat,
                 "step_id": f"STEP-{pid}-060", "quantity_per_unit": 1.0, "is_critical": True,
                 "consumption_pattern": "工序开始时消耗"})
    # EMC塑封料
    boms.append({"bom_id": f"BOM-{pid}-EMC", "product_id": pid, "material_id": f"MAT-EMC-{pkg}",
                 "step_id": f"STEP-{pid}-100", "quantity_per_unit": 2.0, "is_critical": True,
                 "consumption_pattern": "按比例消耗"})
    # Ball/Solder (仅部分封装)
    if cfg["ball"]:
        boms.append({"bom_id": f"BOM-{pid}-BALL", "product_id": pid, "material_id": f"MAT-BALL-{pkg}",
                     "step_id": f"STEP-{pid}-120", "quantity_per_unit": 50.0, "is_critical": True,
                     "consumption_pattern": "工序开始时消耗"})
    # Wire (仅需要键合的)
    if cfg["bond"] > 0:
        boms.append({"bom_id": f"BOM-{pid}-WIRE", "product_id": pid, "material_id": f"MAT-WIRE-{pkg}",
                     "step_id": f"STEP-{pid}-080", "quantity_per_unit": 0.5, "is_critical": True,
                     "consumption_pattern": "按比例消耗"})
    # Die Attach Paste (通用)
    boms.append({"bom_id": f"BOM-{pid}-DA", "product_id": pid, "material_id": "MAT-DA-PASTE",
                 "step_id": f"STEP-{pid}-060", "quantity_per_unit": 0.1, "is_critical": False,
                 "consumption_pattern": "按比例消耗"})
    # === 第2层：基板/引线框架的组成材料（虚拟层级，step_id=None表示外购件不绑定具体工序） ===
    if pkg in ("BGA","WLCSP","FANOUT","LGA","CSP","SIP"):
        boms.append({"bom_id": f"BOM-{pid}-CU", "product_id": pid, "material_id": "MAT-CU-FOIL",
                     "step_id": None, "quantity_per_unit": 0.5, "is_critical": False,
                     "consumption_pattern": "按比例消耗"})
        boms.append({"bom_id": f"BOM-{pid}-RESIN", "product_id": pid, "material_id": "MAT-RESIN",
                     "step_id": None, "quantity_per_unit": 0.3, "is_critical": False,
                     "consumption_pattern": "按比例消耗"})
        boms.append({"bom_id": f"BOM-{pid}-GF", "product_id": pid, "material_id": "MAT-GLASS-FIBER",
                     "step_id": None, "quantity_per_unit": 0.2, "is_critical": False,
                     "consumption_pattern": "按比例消耗"})
    else:
        boms.append({"bom_id": f"BOM-{pid}-CU", "product_id": pid, "material_id": "MAT-CU-FOIL",
                     "step_id": None, "quantity_per_unit": 0.8, "is_critical": False,
                     "consumption_pattern": "按比例消耗"})
        boms.append({"bom_id": f"BOM-{pid}-RESIN", "product_id": pid, "material_id": "MAT-RESIN",
                     "step_id": None, "quantity_per_unit": 0.1, "is_critical": False,
                     "consumption_pattern": "按比例消耗"})
    return boms

def generate_boms() -> List[Dict]:
    boms = []
    for pkg, cfg in PKG_CFG.items():
        for chip in CHIP_TYPES:
            boms += _bom_l1(pkg, chip, cfg)
    return boms

# ============================================================================
# 物料定义 (含BOM第2层原材料)
# ============================================================================

def generate_materials() -> List[Dict]:
    materials = []
    # 通用Die材料（按封装类型）
    for pkg in PKG_CFG:
        materials.append({"material_id": f"MAT-DIE-{pkg}", "material_name": f"{PKG_CFG[pkg]['name']}芯片Die",
                          "material_type": "原材料", "unit_of_measure": "片", "safety_stock_level": 50.0,
                          "reorder_point": 100.0, "lot_size": 200.0, "eoq": 150.0})
    # 基板/引线框架
    for pkg in PKG_CFG:
        if pkg in ("BGA","WLCSP","FANOUT","LGA","CSP","SIP"):
            materials.append({"material_id": f"MAT-SUB-{pkg}", "material_name": f"{PKG_CFG[pkg]['name']}基板",
                              "material_type": "原材料", "unit_of_measure": "片", "safety_stock_level": 40.0,
                              "reorder_point": 80.0, "lot_size": 150.0, "eoq": 120.0})
        else:
            materials.append({"material_id": f"MAT-LF-{pkg}", "material_name": f"{PKG_CFG[pkg]['name']}引线框架",
                              "material_type": "原材料", "unit_of_measure": "片", "safety_stock_level": 40.0,
                              "reorder_point": 80.0, "lot_size": 150.0, "eoq": 120.0})
    # EMC塑封料
    for pkg in PKG_CFG:
        materials.append({"material_id": f"MAT-EMC-{pkg}", "material_name": f"{PKG_CFG[pkg]['name']}塑封料EMC",
                          "material_type": "原材料", "unit_of_measure": "KG", "safety_stock_level": 30.0,
                          "reorder_point": 60.0, "lot_size": 100.0, "eoq": 80.0})
    # 锡球
    for pkg in ("BGA","WLCSP","FANOUT","CSP","SIP"):
        materials.append({"material_id": f"MAT-BALL-{pkg}", "material_name": f"{PKG_CFG[pkg]['name']}锡球",
                          "material_type": "原材料", "unit_of_measure": "KPCS", "safety_stock_level": 20.0,
                          "reorder_point": 40.0, "lot_size": 80.0, "eoq": 60.0})
    # 金线/铜线
    for pkg in ("BGA","QFN","SOP","QFP","SIP","LGA","CSP","SOT"):
        materials.append({"material_id": f"MAT-WIRE-{pkg}", "material_name": f"{PKG_CFG[pkg]['name']}键合线",
                          "material_type": "原材料", "unit_of_measure": "米", "safety_stock_level": 500.0,
                          "reorder_point": 1000.0, "lot_size": 2000.0, "eoq": 1500.0})
    # 通用材料
    materials.append({"material_id": "MAT-DA-PASTE", "material_name": "贴片银浆",
                      "material_type": "辅料", "unit_of_measure": "G", "safety_stock_level": 200.0,
                      "reorder_point": 400.0, "lot_size": 800.0, "eoq": 600.0})
    materials.append({"material_id": "MAT-DA-PASTE-ALT", "material_name": "贴片银浆（替代品牌）",
                      "material_type": "辅料", "unit_of_measure": "G", "safety_stock_level": 100.0,
                      "reorder_point": 200.0, "lot_size": 400.0, "eoq": 300.0})
    
    # 替代物料（EMC/键合线/基板的替代品）
    materials.append({"material_id": "MAT-EMC-BGA-ALT", "material_name": "BGA塑封料（替代型号）",
                      "material_type": "原材料", "unit_of_measure": "KG", "safety_stock_level": 20.0,
                      "reorder_point": 40.0, "lot_size": 80.0, "eoq": 60.0})
    materials.append({"material_id": "MAT-EMC-QFN-ALT", "material_name": "QFN塑封料（替代型号）",
                      "material_type": "原材料", "unit_of_measure": "KG", "safety_stock_level": 20.0,
                      "reorder_point": 40.0, "lot_size": 80.0, "eoq": 60.0})
    materials.append({"material_id": "MAT-WIRE-BGA-CU", "material_name": "BGA铜键合线（替代金线）",
                      "material_type": "原材料", "unit_of_measure": "米", "safety_stock_level": 300.0,
                      "reorder_point": 600.0, "lot_size": 1200.0, "eoq": 900.0})
    materials.append({"material_id": "MAT-SUB-BGA-V2", "material_name": "BGA基板（供应商B）",
                      "material_type": "原材料", "unit_of_measure": "片", "safety_stock_level": 30.0,
                      "reorder_point": 60.0, "lot_size": 120.0, "eoq": 90.0})
    # BOM第2层：基板原材料
    materials += [
        {"material_id": "MAT-CU-FOIL", "material_name": "电解铜箔", "material_type": "原材料",
         "unit_of_measure": "平米", "safety_stock_level": 100.0, "reorder_point": 200.0, "lot_size": 500.0, "eoq": 400.0},
        {"material_id": "MAT-RESIN", "material_name": "环氧树脂", "material_type": "原材料",
         "unit_of_measure": "KG", "safety_stock_level": 100.0, "reorder_point": 200.0, "lot_size": 500.0, "eoq": 400.0},
        {"material_id": "MAT-GLASS-FIBER", "material_name": "玻纤布", "material_type": "原材料",
         "unit_of_measure": "卷", "safety_stock_level": 50.0, "reorder_point": 100.0, "lot_size": 200.0, "eoq": 150.0},
    ]
    return materials

MATERIALS = generate_materials()

# ============================================================================
# 工作中心和机台生成
# ============================================================================

WORK_CENTERS = [
    {"work_center_id": "WC-RECV",     "work_center_name": "来料接收",       "work_center_type": "接收", "capacity_uom": "小时"},
    {"work_center_id": "WC-GRIND",    "work_center_name": "晶圆研磨",       "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-DICE",     "work_center_name": "晶圆切割",       "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-DA",       "work_center_name": "Die Attach",     "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-WB",       "work_center_name": "引线键合",       "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-FC",       "work_center_name": "倒装焊",         "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-RDL",      "work_center_name": "RDL重构",        "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-MOLD",     "work_center_name": "塑封成型",       "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-PMC",      "work_center_name": "后固化",         "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-MARK",     "work_center_name": "激光打标",       "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-BALL",     "work_center_name": "植球回流",       "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-SING",     "work_center_name": "切割分选",       "work_center_type": "加工", "capacity_uom": "小时"},
    {"work_center_id": "WC-AOI",      "work_center_name": "光学检测",       "work_center_type": "检验", "capacity_uom": "小时"},
    {"work_center_id": "WC-VISUAL",   "work_center_name": "外观检查",       "work_center_type": "检验", "capacity_uom": "小时"},
    {"work_center_id": "WC-XRAY",     "work_center_name": "X-Ray检测",      "work_center_type": "检验", "capacity_uom": "小时"},
    {"work_center_id": "WC-SAM",      "work_center_name": "超声波扫描",     "work_center_type": "检验", "capacity_uom": "小时"},
    {"work_center_id": "WC-TEST-CP",  "work_center_name": "CP测试站",       "work_center_type": "测试", "capacity_uom": "小时"},
    {"work_center_id": "WC-TEST-FT",  "work_center_name": "最终测试站",     "work_center_type": "测试", "capacity_uom": "小时"},
    {"work_center_id": "WC-TEST-BI",  "work_center_name": "老化测试站",     "work_center_type": "测试", "capacity_uom": "小时"},
    {"work_center_id": "WC-TEST-SYS", "work_center_name": "系统测试站",     "work_center_type": "测试", "capacity_uom": "小时"},
    {"work_center_id": "WC-CLEAN",    "work_center_name": "清洗站",         "work_center_type": "辅助", "capacity_uom": "小时"},
    {"work_center_id": "WC-BAKE",     "work_center_name": "烘烤站",         "work_center_type": "辅助", "capacity_uom": "小时"},
    {"work_center_id": "WC-WAIT",     "work_center_name": "暂存区",         "work_center_type": "辅助", "capacity_uom": "小时"},
    {"work_center_id": "WC-TRANS",    "work_center_name": "转运站",         "work_center_type": "辅助", "capacity_uom": "小时"},
    {"work_center_id": "WC-PACK",     "work_center_name": "包装出货",       "work_center_type": "出货", "capacity_uom": "小时"},
]

# 机台：根据瓶颈分析优化配置（从145台优化到96台）
MACHINE_CFG = {
    "WC-RECV":     2,  # 3→2（负荷4%，减1台）
    "WC-GRIND":    3,  # 4→3（负荷13%，减1台）
    "WC-DICE":     4,  # 6→4（负荷适中，减2台）
    "WC-DA":       5,  # 8→5（负荷3%，减3台）
    "WC-WB":      12,  # 20→12（负荷5-25%，减8台）
    "WC-FC":       3,  # 4→3（仅部分产品使用，减1台）
    "WC-RDL":      3,  # 4→3（仅部分产品使用，减1台）
    "WC-MOLD":     4,  # 保持不变（瓶颈工序之一）
    "WC-PMC":      5,  # 4→5（单工序最长4h，增加1台）
    "WC-MARK":     3,  # 4→3（单工序0.3h极快，减1台）
    "WC-BALL":     3,  # 4→3（仅BGA/WLCSP使用，减1台）
    "WC-SING":     4,  # 6→4（减2台）
    "WC-AOI":      3,  # 4→3（减1台）
    "WC-VISUAL":   4,  # 6→4（减2台）
    "WC-XRAY":     2,  # 保持不变
    "WC-SAM":      2,  # 保持不变
    "WC-TEST-CP":  6,  # 10→6（负荷5%，减4台）
    "WC-TEST-FT":  6,  # 12→6（负荷3%，减6台）
    "WC-TEST-BI":  6,  # 4→6（瓶颈工序！增加2台，降低利用率到94%）
    "WC-TEST-SYS": 3,  # 4→3（减1台）
    "WC-CLEAN":    4,  # 6→4（减2台）
    "WC-BAKE":     6,  # 4→6（负荷50-75%，增加2台）
    "WC-WAIT":     6,  # 8→6（排队由排程算法管理，减2台）
    "WC-TRANS":    4,  # 6→4（减2台）
    "WC-PACK":     3,  # 4→3（减1台）
}

def generate_machines() -> List[Dict]:
    machines = []
    for wc_id, count in MACHINE_CFG.items():
        for i in range(1, count + 1):
            mid = f"{wc_id}-{i:02d}"
            machines.append({
                "machine_id": mid,
                "machine_name": f"机台-{mid}",
                "machine_type": "自动",
                "work_center_id": wc_id,
                "max_capacity_per_hour": 100.0,
                "status": "在线",
                "is_active": True,
            })
    return machines

MACHINES = generate_machines()

# ============================================================================
# 机台能力矩阵 (程序化生成)
# ============================================================================

def generate_capabilities() -> List[Dict]:
    caps = []
    for pkg, cfg in PKG_CFG.items():
        for chip in CHIP_TYPES:
            pid = f"{pkg}-{chip}"
            for m in MACHINES:
                mid = m["machine_id"]
                wc = m["work_center_id"]
                # 基础效率
                base_eff = 0.95
                # 根据封装类型与工作中心匹配度调整
                if wc == "WC-WB" and cfg["bond"] > 0:
                    base_eff = 1.0
                elif wc == "WC-BALL" and cfg["ball"]:
                    base_eff = 1.0
                elif wc == "WC-RDL" and cfg["rdl"]:
                    base_eff = 1.0
                elif wc == "WC-TEST-CP" and cfg["test"] >= 4:
                    base_eff = 1.05
                elif wc == "WC-TEST-BI" and cfg["steps"] > 80:
                    base_eff = 1.0
                elif wc in ("WC-FC",) and cfg["bond"] == 0 and not cfg["rdl"]:
                    base_eff = 0.5  # 不匹配
                elif wc in ("WC-TRANS", "WC-WAIT", "WC-CLEAN", "WC-BAKE"):
                    base_eff = 1.1  # 辅助站效率高
                caps.append({
                    "capability_id": f"MCAP-{mid}-{pid}",
                    "machine_id": mid,
                    "product_id": pid,
                    "efficiency_factor": round(base_eff, 2),
                    "yield_rate": round(0.95 + (hash(pid + mid) % 10) / 100, 2),
                    "setup_time_minutes": 20,
                    "is_preferred": base_eff >= 1.0,
                    "rated_speed_per_hour": 100.0,
                    "sample_count": 0,
                })
    return caps

MACHINE_CAPABILITIES = generate_capabilities()

# ============================================================================
# 换线矩阵 (按Setup Group = 封装类型)
# ============================================================================

def generate_setup_matrix() -> List[Dict]:
    """生成换线矩阵（按setup_group级别，为关键机台生成）"""
    matrix = []
    groups = list(PKG_CFG.keys())
    # 每个setup_group的代表产品（用CPU芯片）
    rep = {g: f"{g}-CPU" for g in groups}
    # 不需要换线的辅助站
    no_setup_wc = {"WC-RECV","WC-CLEAN","WC-BAKE","WC-WAIT","WC-TRANS","WC-PACK","WC-AOI","WC-XRAY","WC-SAM","WC-VISUAL","WC-TEST-CP","WC-TEST-FT","WC-TEST-BI","WC-TEST-SYS"}
    idx = 0
    for m in MACHINES:
        mid = m["machine_id"]
        wc = m["work_center_id"]
        if wc in no_setup_wc:
            continue
        for i, g1 in enumerate(groups):
            for j, g2 in enumerate(groups):
                if g1 == g2:
                    t = 15
                elif abs(i - j) <= 2:
                    t = 30
                else:
                    t = 60
                matrix.append({
                    "matrix_id": f"SM-{idx:05d}",
                    "machine_id": mid,
                    "from_product_id": rep[g1],
                    "to_product_id": rep[g2],
                    "setup_time_minutes": t,
                    "setup_type": "换模",
                    "is_active": True,
                })
                idx += 1
    return matrix

SETUP_MATRIX = generate_setup_matrix()

# ============================================================================
# 班次定义
# ============================================================================

SHIFT_PATTERNS = [
    {"shift_id": "SHIFT-DAY", "shift_name": "日班", "start_time": "08:00", "end_time": "20:00",
     "available_hours": 12.0, "efficiency_factor": 1.0, "is_active": True},
    {"shift_id": "SHIFT-NIGHT", "shift_name": "夜班", "start_time": "20:00", "end_time": "08:00",
     "available_hours": 12.0, "efficiency_factor": 0.92, "is_active": True},
]

# ============================================================================
# 供应商定义
# ============================================================================

SUPPLIERS = [
    # 主供应商（5个）
    {"supplier_id": "SUP-001", "supplier_name": "本地基板供应商", "supplier_type": "直供", "avg_lead_time_days": 3, "reliability_score": 0.95, "min_order_quantity": 100.0, "lead_time_stddev_days": 0.5},
    {"supplier_id": "SUP-002", "supplier_name": "区域塑封料供应商", "supplier_type": "直供", "avg_lead_time_days": 5, "reliability_score": 0.88, "min_order_quantity": 50.0, "lead_time_stddev_days": 1.0},
    {"supplier_id": "SUP-003", "supplier_name": "TechMat国际进口商", "supplier_type": "进口", "avg_lead_time_days": 15, "reliability_score": 0.80, "min_order_quantity": 200.0, "lead_time_stddev_days": 3.0},
    {"supplier_id": "SUP-004", "supplier_name": "键合线供应商", "supplier_type": "直供", "avg_lead_time_days": 2, "reliability_score": 0.97, "min_order_quantity": 500.0, "lead_time_stddev_days": 0.3},
    {"supplier_id": "SUP-005", "supplier_name": "锡球供应商", "supplier_type": "直供", "avg_lead_time_days": 4, "reliability_score": 0.92, "min_order_quantity": 50.0, "lead_time_stddev_days": 0.8},
    
    # 备选供应商（8个）- 真实OSAT供应链策略
    {"supplier_id": "SUP-006", "supplier_name": "备选基板供应商（中国台湾）", "supplier_type": "进口", "avg_lead_time_days": 7, "reliability_score": 0.90, "min_order_quantity": 150.0, "lead_time_stddev_days": 1.5},
    {"supplier_id": "SUP-007", "supplier_name": "备选塑封料供应商（日本）", "supplier_type": "进口", "avg_lead_time_days": 12, "reliability_score": 0.93, "min_order_quantity": 80.0, "lead_time_stddev_days": 2.0},
    {"supplier_id": "SUP-008", "supplier_name": "国产Die供应商（中国大陆）", "supplier_type": "直供", "avg_lead_time_days": 10, "reliability_score": 0.85, "min_order_quantity": 300.0, "lead_time_stddev_days": 2.0},
    {"supplier_id": "SUP-009", "supplier_name": "备选键合线供应商（韩国）", "supplier_type": "进口", "avg_lead_time_days": 5, "reliability_score": 0.91, "min_order_quantity": 600.0, "lead_time_stddev_days": 1.0},
    {"supplier_id": "SUP-010", "supplier_name": "备选锡球供应商（东南亚）", "supplier_type": "进口", "avg_lead_time_days": 8, "reliability_score": 0.87, "min_order_quantity": 80.0, "lead_time_stddev_days": 1.5},
    {"supplier_id": "SUP-011", "supplier_name": "辅料供应商（本地）", "supplier_type": "直供", "avg_lead_time_days": 2, "reliability_score": 0.94, "min_order_quantity": 50.0, "lead_time_stddev_days": 0.5},
    {"supplier_id": "SUP-012", "supplier_name": "基板原材料供应商（中国台湾）", "supplier_type": "进口", "avg_lead_time_days": 10, "reliability_score": 0.88, "min_order_quantity": 300.0, "lead_time_stddev_days": 2.0},
    {"supplier_id": "SUP-013", "supplier_name": "特种材料供应商（欧洲）", "supplier_type": "进口", "avg_lead_time_days": 18, "reliability_score": 0.82, "min_order_quantity": 100.0, "lead_time_stddev_days": 3.5},
]

# ============================================================================
# 供应商-物料关系
# ============================================================================

def generate_supplier_materials() -> List[Dict]:
    sms = []
    # 基板由SUP-001供应
    for pkg in ("BGA","WLCSP","FANOUT","LGA","CSP","SIP"):
        sms.append({"sm_id": f"SM-001-{pkg}", "supplier_id": "SUP-001", "material_id": f"MAT-SUB-{pkg}",
                    "unit_price": 2.5, "lead_time_days": 3, "min_order_qty": 100.0, "is_preferred": True})
    # 引线框架由SUP-001供应
    for pkg in ("QFN","SOP","QFP","SOT"):
        sms.append({"sm_id": f"SM-001-LF-{pkg}", "supplier_id": "SUP-001", "material_id": f"MAT-LF-{pkg}",
                    "unit_price": 1.5, "lead_time_days": 3, "min_order_qty": 100.0, "is_preferred": True})
    # 塑封料由SUP-002供应
    for pkg in PKG_CFG:
        sms.append({"sm_id": f"SM-002-{pkg}", "supplier_id": "SUP-002", "material_id": f"MAT-EMC-{pkg}",
                    "unit_price": 8.0, "lead_time_days": 5, "min_order_qty": 50.0, "is_preferred": True})
    # 进口Die由SUP-003供应
    for pkg in PKG_CFG:
        sms.append({"sm_id": f"SM-003-DIE-{pkg}", "supplier_id": "SUP-003", "material_id": f"MAT-DIE-{pkg}",
                    "unit_price": 15.0, "lead_time_days": 15, "min_order_qty": 200.0, "is_preferred": True})
    # 键合线由SUP-004供应
    for pkg in ("BGA","QFN","SOP","QFP","SIP","LGA","CSP","SOT"):
        sms.append({"sm_id": f"SM-004-WIRE-{pkg}", "supplier_id": "SUP-004", "material_id": f"MAT-WIRE-{pkg}",
                    "unit_price": 0.05, "lead_time_days": 2, "min_order_qty": 500.0, "is_preferred": True})
    # 锡球由SUP-005供应
    for pkg in ("BGA","WLCSP","FANOUT","CSP","SIP"):
        sms.append({"sm_id": f"SM-005-BALL-{pkg}", "supplier_id": "SUP-005", "material_id": f"MAT-BALL-{pkg}",
                    "unit_price": 0.02, "lead_time_days": 4, "min_order_qty": 50.0, "is_preferred": True})
    # 贴片银浆
    sms.append({"sm_id": "SM-001-DA", "supplier_id": "SUP-001", "material_id": "MAT-DA-PASTE",
                "unit_price": 0.5, "lead_time_days": 3, "min_order_qty": 100.0, "is_preferred": True})
    
    # 替代物料的供应商（新增）
    # 替代品牌银浆（SUP-002也提供）
    sms.append({"sm_id": "SM-002-DA-ALT", "supplier_id": "SUP-002", "material_id": "MAT-DA-PASTE-ALT",
                "unit_price": 0.55, "lead_time_days": 4, "min_order_qty": 80.0, "is_preferred": False})
    
    # 替代EMC塑封料（原供应商也提供替代型号）
    sms.append({"sm_id": "SM-002-BGA-ALT", "supplier_id": "SUP-002", "material_id": "MAT-EMC-BGA-ALT",
                "unit_price": 8.3, "lead_time_days": 5, "min_order_qty": 50.0, "is_preferred": False})
    sms.append({"sm_id": "SM-002-QFN-ALT", "supplier_id": "SUP-002", "material_id": "MAT-EMC-QFN-ALT",
                "unit_price": 8.3, "lead_time_days": 5, "min_order_qty": 50.0, "is_preferred": False})
    
    # 铜键合线（SUP-004提供铜线替代方案）
    sms.append({"sm_id": "SM-004-WIRE-CU", "supplier_id": "SUP-004", "material_id": "MAT-WIRE-BGA-CU",
                "unit_price": 0.035, "lead_time_days": 2, "min_order_qty": 500.0, "is_preferred": False})
    
    # 供应商B的基板（SUP-001的竞争对手）
    sms.append({"sm_id": "SM-001-SUB-V2", "supplier_id": "SUP-001", "material_id": "MAT-SUB-BGA-V2",
                "unit_price": 2.6, "lead_time_days": 3, "min_order_qty": 100.0, "is_preferred": False})
    
    # BOM第2层：基板原材料供应商（新增）
    # 电解铜箔供应商
    sms.append({"sm_id": "SM-001-CU", "supplier_id": "SUP-001", "material_id": "MAT-CU-FOIL",
                "unit_price": 12.0, "lead_time_days": 7, "min_order_qty": 200.0, "is_preferred": True})
    # 环氧树脂供应商
    sms.append({"sm_id": "SM-002-RESIN", "supplier_id": "SUP-002", "material_id": "MAT-RESIN",
                "unit_price": 5.0, "lead_time_days": 5, "min_order_qty": 100.0, "is_preferred": True})
    # 玻纤布供应商
    sms.append({"sm_id": "SM-001-GLASS", "supplier_id": "SUP-001", "material_id": "MAT-GLASS-FIBER",
                "unit_price": 8.0, "lead_time_days": 7, "min_order_qty": 100.0, "is_preferred": True})
    
    # ========== 备选供应商配置（真实OSAT供应链策略） ==========
    
    # 基板备选供应商（SUP-006 中国台湾）
    for pkg in ("BGA","WLCSP","FANOUT","LGA","CSP","SIP"):
        sms.append({"sm_id": f"SM-006-SUB-{pkg}", "supplier_id": "SUP-006", "material_id": f"MAT-SUB-{pkg}",
                    "unit_price": 2.8, "lead_time_days": 7, "min_order_qty": 150.0, "is_preferred": False})
    
    # 引线框架备选供应商（SUP-006）
    for pkg in ("QFN","SOP","QFP","SOT"):
        sms.append({"sm_id": f"SM-006-LF-{pkg}", "supplier_id": "SUP-006", "material_id": f"MAT-LF-{pkg}",
                    "unit_price": 1.7, "lead_time_days": 7, "min_order_qty": 150.0, "is_preferred": False})
    
    # EMC塑封料备选供应商（SUP-007 日本，质量更好但贵）
    for pkg in PKG_CFG:
        sms.append({"sm_id": f"SM-007-EMC-{pkg}", "supplier_id": "SUP-007", "material_id": f"MAT-EMC-{pkg}",
                    "unit_price": 9.5, "lead_time_days": 12, "min_order_qty": 80.0, "is_preferred": False})
    
    # 国产Die备选供应商（SUP-008 中国大陆，交期短但良率略低）
    for pkg in PKG_CFG:
        sms.append({"sm_id": f"SM-008-DIE-{pkg}", "supplier_id": "SUP-008", "material_id": f"MAT-DIE-{pkg}",
                    "unit_price": 12.0, "lead_time_days": 10, "min_order_qty": 300.0, "is_preferred": False})
    
    # 键合线备选供应商（SUP-009 韩国）
    for pkg in ("BGA","QFN","SOP","QFP","SIP","LGA","CSP","SOT"):
        sms.append({"sm_id": f"SM-009-WIRE-{pkg}", "supplier_id": "SUP-009", "material_id": f"MAT-WIRE-{pkg}",
                    "unit_price": 0.055, "lead_time_days": 5, "min_order_qty": 600.0, "is_preferred": False})
    
    # 锡球备选供应商（SUP-010 东南亚）
    for pkg in ("BGA","WLCSP","FANOUT","CSP","SIP"):
        sms.append({"sm_id": f"SM-010-BALL-{pkg}", "supplier_id": "SUP-010", "material_id": f"MAT-BALL-{pkg}",
                    "unit_price": 0.023, "lead_time_days": 8, "min_order_qty": 80.0, "is_preferred": False})
    
    # 辅料备选供应商（SUP-011 本地）
    sms.append({"sm_id": "SM-011-DA", "supplier_id": "SUP-011", "material_id": "MAT-DA-PASTE",
                "unit_price": 0.52, "lead_time_days": 2, "min_order_qty": 50.0, "is_preferred": False})
    sms.append({"sm_id": "SM-011-DA-ALT", "supplier_id": "SUP-011", "material_id": "MAT-DA-PASTE-ALT",
                "unit_price": 0.57, "lead_time_days": 2, "min_order_qty": 50.0, "is_preferred": False})
    
    # 基板原材料备选供应商（SUP-012 中国台湾）
    sms.append({"sm_id": "SM-012-CU", "supplier_id": "SUP-012", "material_id": "MAT-CU-FOIL",
                "unit_price": 13.5, "lead_time_days": 10, "min_order_qty": 300.0, "is_preferred": False})
    sms.append({"sm_id": "SM-012-GLASS", "supplier_id": "SUP-012", "material_id": "MAT-GLASS-FIBER",
                "unit_price": 9.0, "lead_time_days": 10, "min_order_qty": 200.0, "is_preferred": False})
    
    # 特种材料供应商（SUP-013 欧洲，高端产品用）
    sms.append({"sm_id": "SM-013-RESIN", "supplier_id": "SUP-013", "material_id": "MAT-RESIN",
                "unit_price": 6.5, "lead_time_days": 18, "min_order_qty": 100.0, "is_preferred": False})
    return sms

SUPPLIER_MATERIALS = generate_supplier_materials()

# ============================================================================
# 替代料关系
# ============================================================================

MATERIAL_SUBSTITUTES = [
    # 贴片银浆替代（不同品牌）
    {"ms_id": "MS-001", "material_id": "MAT-DA-PASTE", "substitute_material_id": "MAT-DA-PASTE-ALT",
     "substitute_priority": 1, "quality_grade": "同等级", "approval_status": "已批准", "cost_delta_percent": 5.0},
    
    # EMC塑封料替代（不同型号）
    {"ms_id": "MS-002", "material_id": "MAT-EMC-BGA", "substitute_material_id": "MAT-EMC-BGA-ALT",
     "substitute_priority": 1, "quality_grade": "同等级", "approval_status": "已批准", "cost_delta_percent": 3.0},
    {"ms_id": "MS-003", "material_id": "MAT-EMC-QFN", "substitute_material_id": "MAT-EMC-QFN-ALT",
     "substitute_priority": 1, "quality_grade": "同等级", "approval_status": "已批准", "cost_delta_percent": 3.0},
    
    # 键合线替代（金线→铜线）
    {"ms_id": "MS-004", "material_id": "MAT-WIRE-BGA", "substitute_material_id": "MAT-WIRE-BGA-CU",
     "substitute_priority": 2, "quality_grade": "略低", "approval_status": "已批准", "cost_delta_percent": -30.0},
    
    # 基板替代（不同供应商）
    {"ms_id": "MS-005", "material_id": "MAT-SUB-BGA", "substitute_material_id": "MAT-SUB-BGA-V2",
     "substitute_priority": 1, "quality_grade": "同等级", "approval_status": "已批准", "cost_delta_percent": 2.0},
]

# ============================================================================
# 初始库存
# ============================================================================

def generate_initial_inventory() -> List[Dict]:
    inv = []
    for m in MATERIALS:
        mid = m["material_id"]
        qty = m.get("safety_stock_level", 50.0) * 2
        loc = "原材料仓A" if "SUB" in mid or "LF" in mid or "DIE" in mid else "原材料仓B" if "EMC" in mid else "辅料仓" if "PASTE" in mid else "进口料仓" if "BALL" in mid or "WIRE" in mid else "通用仓"
        inv.append({"material_id": mid, "location": loc, "total_quantity": qty,
                    "available_quantity": qty, "reserved_quantity": 0.0})
    return inv

INITIAL_INVENTORY = generate_initial_inventory()

# ============================================================================
# 仿真参数
# ============================================================================

# ============================================================================
# 仿真配置参数（统一管理所有可调参数）
# ============================================================================

SIMULATION_CONFIG = {
    # ========== 基础时间配置 ==========
    "duration_days": 60,  # 仿真总天数
    "start_date": "2026-02-26 08:00:00",  # 仿真开始时间（ISO 8601格式）
    "day_start_hour": 8,  # 日班开始时间（08:00）
    "day_end_hour": 20,  # 日班结束时间（20:00），夜班自动接续到次日08:00
    
    # ========== 订单生成配置 ==========
    "order_arrival_lambda": 3.0,  # 订单到达率（泊松分布λ，每天平均3张订单）
    "order_quantity_min": 5,  # 订单数量下限（5个芯片）
    "order_quantity_max": 80,  # 订单数量上限（80个芯片）
    "order_priority_weights": [0.2, 0.3, 0.5],  # 订单优先级分布 [P1紧急:20%, P3普通:30%, P5宽松:50%]
    "order_cancel_daily_prob": 0.10,  # 订单每日取消概率（10%）
    "split_delivery_prob": 0.30,  # 拆分发货概率（30%订单会分批交付）
    "priority_escalation_daily_prob": 0.08,  # 订单每日优先级提升概率（8%）
    "lead_time_commitment_days": 7,  # CTP交期承诺最低天数（订单日期+7天）
    
    # ========== Lot批量加工配置 ==========
    "wip_lot_size": 25,  # Lot批量大小（25个芯片/批，OSAT行业标准）
    "batch_process_steps": ["BI", "BAKE", "CURE", "DRY"],  # 批量并行工序代码（这些工序可并行处理整个Lot）
    "batch_capacity": {  # 各批量工序的并行容量（芯片数）
        "WC-TEST-BI": 1000,  # 老化炉容量（一次可老化1000芯片）
        "WC-BAKE": 200,      # 烘烤炉容量（一次可烘烤200芯片）
        "WC-DA": 100,        # 固化工位容量（一次可固化100芯片）
    },
    
    # ========== 工序时间配置 ==========
    "queue_time_hours": 0.5,  # 工序间排队时间（0.5小时，Lot场景下已优化）
    "initial_offset_hours": 4.0,  # 首道工序计划开始偏移（距现在4小时开始）
    "setup_skip_same_group": True,  # 同SetupGroup连续生产免换线（减少换线时间）
    
    # ========== 工序流优化配置 ==========
    "flow_merge_enabled": True,  # 工序流合并开关（合并辅助工序，减少排队）
    "flow_merge_groups": [  # 可合并的工序段（同组工序合并执行）
        ["RECV", "GRIND", "DICE"],  # 前段工序合并（接收→磨片→切割）
        ["CLEAN", "TRANS", "WAIT"],  # 辅助工序合并（清洗→转运→等待）
    ],
    
    # ========== 效率与良率配置 ==========
    "night_shift_efficiency": 0.92,  # 夜班效率因子（20:00-08:00效率降至92%）
    "default_yield_rate": 0.98,  # 默认工序标准良率（98%）
    "yield_random_range": [0.99, 1.01],  # 良率随机扰动范围（±1%）
    "default_efficiency_factor": 1.0,  # 默认机台效率因子（100%）
    "min_efficiency_factor": 0.5,  # 机台效率下限（50%，防止除零）
    
    # ========== 质检配置 ==========
    "ipqc_reject_rate": 0.15,  # IPQC首件检验不合格率（15%）
    "ipqc_inspection_hours": 0.5,  # IPQC首件检验耗时（0.5小时）
    "fqc_reject_rate": 0.05,  # FQC成品检验不合格率（5%）
    "reworkable_rate": 0.80,  # FQC不合格后可重工比例（80%）
    "rework_yield_rate": 0.90,  # 重工良率（90%）
    "iqc_reject_rate": 0.03,  # IQC来料检验不合格率（3%）
    "iqc_scrap_rate_range": [0.03, 0.15],  # IQC来料报废率范围（3%-15%）
    "under_performance_rate_range": [0.05, 0.15],  # 性能不达标率范围（5%-15%）
    
    # ========== 设备维护与故障配置 ==========
    "maintenance_frequency_hours": 168,  # 计划维护周期（168小时=7天）
    "maintenance_duration_hours": 4,  # 计划维护耗时（4小时）
    "breakdown_mtbf_hours": 240,  # 平均无故障时间MTBF（240小时=10天）
    "breakdown_mttr_hours": 4,  # 平均修复时间MTTR（4小时）
    "breakdown_probability": 0.70,  # 机台启用随机故障的概率（70%）
    
    # ========== 排程算法配置 ==========
    "safety_stock_check_interval_hours": 4,  # 安全库存检查间隔（4小时）
    "setup_cost_weight": 2.0,  # 换线成本权重（排程算法中换线时间的权重系数）
    "critical_ratio_threshold": 1.1,  # 关键比阈值（<1.1表示工期紧张）
    "ctp_capacity_buffer": 0.15,  # CTP产能缓冲（15%，预留产能应对突发订单）
    "work_hours_per_day": 12.0,  # 每日工作小时数（白班12小时）
    "scheduler_check_interval_hours": 4.0,  # 排程器检查间隔（4小时，配合实时排程）
    "schedule_cooldown_hours": 0.5,  # 实时排程冷却时间（0.5小时，防抖动）
    "lookahead_horizon_hours": 24.0,  # 前瞻排程预测时间窗口（24小时）
    "lookahead_enabled": True,  # 前瞻排程开关
    
    # ========== CTP优化配置（完整优化版） ==========
    
    # 排队时间配置（基于负荷分级，保守估计）
    "queue_hours_low_load": 4.0,       # 低负荷（<50%）：4小时
    "queue_hours_medium_load": 10.0,   # 中负荷（50-70%）：10小时
    "queue_hours_high_load": 18.0,     # 高负荷（70-85%）：18小时
    "queue_hours_bottleneck": 36.0,    # 瓶颈（>85%）：36小时
    
    # 换线时间配置（基于实际Setup Group逻辑）
    "avg_ipqc_time_hours": 0.33,       # 平均IPQC检验时间（20分钟）
    "ipqc_rework_rate": 0.15,          # IPQC不合格率（15%）
    "ipqc_rework_time_hours": 0.5,     # IPQC不合格返工时间（30分钟）
    
    # 物料等待配置
    "avg_material_delay_hours": 12.0,  # 平均物料等待时间（12小时）
    
    # 其他配置
    "ctp_avg_efficiency": 0.96,        # 日夜班加权平均效率（日班100% + 夜班92%）
    "ctp_buffer_hours": 4.0,           # CTP最终缓冲时间（4小时）
}

# ============================================================================
# 日历生成
# ============================================================================

def generate_work_calendar(start_date: datetime, days: int) -> List[Dict]:
    calendar = []
    shift_ids = ["SHIFT-DAY", "SHIFT-NIGHT"]
    wc_ids = [wc["work_center_id"] for wc in WORK_CENTERS]
    for i in range(days):
        date = (start_date + timedelta(days=i)).date()
        is_workday = date.weekday() < 6
        for wc_id in wc_ids:
            for shift_id in shift_ids:
                cid = f"CAL-{date.strftime('%Y%m%d')}-{wc_id}-{shift_id}"
                calendar.append({
                    "calendar_id": cid,
                    "calendar_date": date,
                    "work_center_id": wc_id,
                    "shift_id": shift_id,
                    "is_workday": is_workday,
                    "available_hours": 12.0 if is_workday else 0.0,
                    "planned_capacity": 100.0 if is_workday else 0.0,
                    "note": "周末休息" if not is_workday else None
                })
    return calendar

# ============================================================================
# 主数据导出
# ============================================================================

PRODUCTS = generate_products()
PROCESS_ROUTES, ROUTE_STEPS = generate_routes_and_steps()
BOMS = generate_boms()