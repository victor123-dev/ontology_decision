"""
半导体制造业DES离散事件仿真引擎 v2.0
基于SimPy 4.x，完整实现13项真实性改进：

P0 (核心逻辑):
  1. 工序前驱约束强制执行 - 上一工序必须完成才能排下一道
  2. 良率损耗传递 - 每道工序产出×良率→下一工序投入数量缩减
  3. 采购到货触发增量MRP重分配 + 供应商可靠性扰动（正态分布交期）
  4. 机台PM维护事件正式实现（非仅计数判断）

P1 (重要真实感):
  5. 工序间等待/转运时间（wait_time + transport_time）
  6. WIPLot与ProductionTask关联（lot_id字段）
  7. 缺料时优先尝试替代料，再调拨，最后采购
  8. 排程算法升级：Setup成本最小化 + 关键比（Critical Ratio）优先级

P2 (细节真实感):
  9. MachineCapability动态闭环更新（每日从ProductionTask计算OEE）
 10. 夜班效率因子（20:00-08:00效率折减0.92）
 11. 安全库存独立补货触发（每4小时检查，低于reorder_point就补）
 12. 交期承诺基于产能负荷计算（简化CTP）
 13. 经济订购量（EOQ）批量策略
"""

import simpy
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from simulation_logger import get_simulation_logger

# 获取日志记录器
logger = get_simulation_logger()


def poisson_sample(lam: float) -> int:
    """泊松分布采样 (Knuth算法)"""
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def normal_sample(mean: float, std: float, min_val: float = 0.0) -> float:
    """正态分布采样（Box-Muller，用于供应商交期扰动）"""
    u1 = random.random()
    u2 = random.random()
    z = math.sqrt(-2.0 * math.log(max(u1, 1e-10))) * math.cos(2.0 * math.pi * u2)
    return max(min_val, mean + std * z)


def compute_eoq(annual_demand: float, order_cost: float, unit_price: float, holding_rate: float) -> float:
    """P2-13: 计算经济订购量 EOQ = sqrt(2DS/iC)"""
    if unit_price <= 0 or holding_rate <= 0 or annual_demand <= 0:
        return annual_demand / 12.0  # 回退到月需求量
    h = unit_price * holding_rate  # 单位持有成本
    return math.sqrt(2.0 * annual_demand * order_cost / h)


class FactorySimulation:
    """工厂仿真核心类 v2.0"""

    def __init__(self, env: simpy.Environment, db_writer, start_date: datetime, config: dict):
        self.env = env
        self.db = db_writer
        self.start_date = start_date
        self.config = config

        # 仿真时钟转真实时间的偏移（小时）
        self.time_offset = start_date

        # 内存中的动态状态（避免频繁查库）
        self.inventory_state = {}   # material_id -> {total, available, reserved, in_transit}
        self.machine_state = {}     # machine_id -> {status, current_product, current_wo, current_task, next_available_time, ...}
        self.work_order_state = {}  # work_order_id -> {status, current_step, allocated_materials, product_id, quantity}
        self.purchase_order_state = {}  # po_id -> {status, expected_arrival, lines}
        self.wip_lot_state = {}     # lot_id -> {wo_id, product_id, current_step_idx, status, current_qty}

        # T2: 成品库存内存状态
        self.fg_inventory_state = {}  # product_id -> {total, available, reserved, shipped}

        # 机台历史状态（用于SetupMatrix查询）
        self.machine_last_product = {}  # machine_id -> last_product_id

        # 计数器（用于生成ID）
        self.counters = defaultdict(int)

        # 排程队列（待排程的工单工序）
        self.scheduling_queue = []  # [(wo_op_id, priority, ready_time)]

        # 机台资源池（SimPy Resource）
        self.machine_resources = {}

        # P0-4: 机台PM锁 - 正在维护中的机台集合
        self.machines_under_maintenance = set()

        # 记录缓存（批量写入）
        self.transaction_buffer = []
        self.status_log_buffer = []
        self.buffer_flush_size = 50

        # 初始化静态数据引用
        self.products = {}
        self.materials = {}
        self.boms = defaultdict(list)       # product_id -> [bom_items]
        self.route_steps = defaultdict(list)  # route_id -> [steps]
        self.route_steps_by_step_id = {}    # step_id -> step
        self.machines = {}
        self.machine_capabilities = {}      # (machine_id, product_id) -> capability
        self.setup_matrix = {}              # (machine_id, from_product, to_product) -> setup_time
        self.work_centers = {}
        self.supplier_materials = defaultdict(list)   # material_id -> [sm_items]
        self.material_substitutes = defaultdict(list) # material_id -> [substitute_items]
        
        # 【客户管理】
        self.customers = []                  # 客户列表
        self.customer_products = defaultdict(list)  # customer_id -> [customer_product_items]

        # P2-9: 机台OEE统计缓存（每日结算）
        self.machine_daily_stats = defaultdict(lambda: defaultdict(list))
        # machine_id -> product_id -> [(efficiency, yield_rate, process_time)]

        # Lot批量加工：step_id到工序代码的映射（用于批量逻辑判断）
        self.step_code_map = {}  # step_id -> step_code (如"STEP-QFP-PMIC-010" -> "RECV")

        # P2-12: 产能负荷追踪（用于CTP）
        self.work_center_load = defaultdict(float)   # work_center_id -> planned_hours_today

        # P2-11: 安全库存补货防重复创建标记
        self.safety_stock_po_pending = set()   # material_id

        # 优化4: 实时排程防抖动机制（避免短时间内重复排程）
        self.schedule_cooldown = {}  # wo_id -> last_schedule_sim_time
        self.schedule_cooldown_hours = self.config.get("schedule_cooldown_hours", 0.5)  # 冷却时间（小时）
        
        # 优化6: 动态关键比算法（基于产品实际工序时间）
        self.product_avg_op_time = {}  # product_id -> avg_hours（缓存）
        
        # 优化5: 前瞻排程状态缓存（避免重复计算）
        self.lookahead_cache = {}  # cache_key -> {timestamp, result}
        self.lookahead_cache_ttl = 2.0  # 缓存有效期2小时

        # Task4: 工作日历集合 (date, wc_id) -> is_workday
        self.work_calendar_set = set()  # 存储 (date_str, wc_id) 可工作的组合

        # Task4: 订单优先级升级记录（避免同一订单重复升级）
        self.escalated_orders = set()  # order_id set

    # ========================================================================
    # 工具方法
    # ========================================================================

    def calculate_avg_op_time(self, product_id: str) -> float:
        """
        【优化6】计算产品实际工序平均时间（考虑批量调整后的时间）
        
        返回：该产品的平均工序时间（小时/道）
        """
        if product_id in self.product_avg_op_time:
            return self.product_avg_op_time[product_id]
        
        route_id = self.get_route_for_product(product_id)
        if not route_id:
            return 4.0  # 默认值（向后兼容）
        
        steps = self.route_steps.get(route_id, [])
        if not steps:
            return 4.0
        
        # 计算平均标准时间（已经是批量调整后的）
        total_time = sum(step.get("standard_time_hours", 0) for step in steps)
        avg_time = total_time / len(steps)
        
        # 加上平均等待/转运时间
        avg_wait = sum(step.get("wait_time_hours", 0) + step.get("transport_time_hours", 0) 
                      for step in steps) / len(steps)
        
        avg_time += avg_wait
        
        # 缓存结果
        self.product_avg_op_time[product_id] = avg_time
        return avg_time
    
    # ========================================================================
    # 优化5: 前瞻排程（Look-Ahead Scheduling）
    # ========================================================================
    
    def look_ahead_schedule(self, horizon_hours: float = None) -> dict:
        """
        【优化5】前瞻排程：预测未来horizon_hours内的瓶颈和冲突
        
        预测维度：
        1. 物料齐套性预测（哪些工序会缺料）
        2. 机台可用性预测（维护/故障时间段）
        3. 交期风险预测（哪些订单可能延误）
        
        返回：{
            "material_shortages": {...},
            "machine_maintenance": {...},
            "at_risk_orders": [...],
            "capacity_heatmap": {...}
        }
        """
        if horizon_hours is None:
            horizon_hours = self.config.get("lookahead_horizon_hours", 24.0)
        
        # 检查缓存
        cache_key = f"lookahead_{horizon_hours}"
        now = self.env.now
        if cache_key in self.lookahead_cache:
            cache = self.lookahead_cache[cache_key]
            if now - cache["timestamp"] < self.lookahead_cache_ttl:
                return cache["result"]  # 使用缓存
        
        # 执行预测（简化版，避免过度复杂）
        result = {
            "material_shortages": self._predict_material_shortages(horizon_hours),
            "machine_maintenance": self._predict_machine_maintenance(horizon_hours),
            "at_risk_orders": self._predict_delivery_risks(horizon_hours),
        }
        
        # 更新缓存
        self.lookahead_cache[cache_key] = {
            "timestamp": now,
            "result": result
        }
        
        return result
    
    def _predict_material_shortages(self, horizon_hours: float) -> dict:
        """预测未来物料缺口（简化版：只检查当前库存不足）"""
        shortages = {}
        
        # 查询所有生产中的工单物料需求
        active_wos = self.db.query_active_work_orders()
        
        for wo in active_wos:
            wo_id = wo["work_order_id"]
            product_id = wo.get("product_id")
            
            # 获取该工单未完成的工序物料需求
            materials = self.db.get_work_order_materials(wo_id)
            for mat in materials:
                if mat.get("status") != "已齐套":
                    material_id = mat["material_id"]
                    required_qty = mat.get("required_qty", 0)
                    allocated_qty = mat.get("allocated_qty", 0)
                    
                    # 检查缺口
                    gap = required_qty - allocated_qty
                    if gap > 0:
                        if material_id not in shortages:
                            shortages[material_id] = {
                                "total_gap": 0,
                                "affected_wos": []
                            }
                        shortages[material_id]["total_gap"] += gap
                        shortages[material_id]["affected_wos"].append(wo_id)
        
        return shortages
    
    def _predict_machine_maintenance(self, horizon_hours: float) -> dict:
        """预测未来机台维护时间窗口"""
        maintenance_windows = {}
        
        for machine_id, state in self.machine_state.items():
            last_pm = state.get("last_pm_hours", 0)
            maintenance_freq = self.config.get("maintenance_frequency_hours", 168)
            
            # 计算下次维护时间
            next_maintenance = last_pm + maintenance_freq
            
            # 如果在前瞻窗口内，记录维护时间
            if next_maintenance <= self.env.now + horizon_hours:
                maintenance_windows[machine_id] = {
                    "next_maintenance_time": next_maintenance,
                    "maintenance_duration": self.config.get("maintenance_duration_hours", 4)
                }
        
        return maintenance_windows
    
    def _predict_delivery_risks(self, horizon_hours: float) -> list:
        """预测交期风险订单（简化版：检查关键比）"""
        at_risk = []
        
        # 查询所有生产中的工单
        active_wos = self.db.query_active_work_orders()
        
        for wo in active_wos:
            wo_id = wo["work_order_id"]
            due_date = wo.get("planned_completion_date")
            
            if not due_date:
                continue
            
            due_sim = self.datetime_to_sim_hours(due_date)
            now_sim = self.env.now
            remaining_time = due_sim - now_sim
            
            # 如果交期在前瞻窗口内，评估风险
            if 0 < remaining_time <= horizon_hours:
                # 获取剩余工序数
                remaining_ops = wo.get("remaining_op_count", 0)
                product_id = wo.get("product_id")
                
                # 计算预估完成时间
                avg_op_time = self.calculate_avg_op_time(product_id)
                estimated_time = remaining_ops * avg_op_time
                
                # 判断风险等级
                if estimated_time > remaining_time * 1.2:  # 预估超期20%以上
                    risk_level = "HIGH"
                elif estimated_time > remaining_time:
                    risk_level = "MEDIUM"
                else:
                    risk_level = "LOW"
                
                if risk_level in ["HIGH", "MEDIUM"]:
                    at_risk.append({
                        "wo_id": wo_id,
                        "risk_level": risk_level,
                        "delay_hours": estimated_time - remaining_time,
                        "remaining_ops": remaining_ops
                    })
        
        return at_risk

    def sim_time_to_datetime(self, sim_hours: float) -> datetime:
        """仿真小时数转真实时间"""
        return self.time_offset + timedelta(hours=sim_hours)

    def datetime_to_sim_hours(self, dt) -> float:
        """真实时间转仿真小时数（支持datetime或ISO格式字符串）"""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        if dt is None:
            return float('inf')
        return (dt - self.time_offset).total_seconds() / 3600.0

    def get_sim_day(self, sim_hours: float = None) -> int:
        """获取当前仿真天数"""
        if sim_hours is None:
            sim_hours = self.env.now
        return int(sim_hours // 24)

    def is_day_shift(self, sim_hours: float = None) -> bool:
        """判断是否为日班（可配置，默认8:00-20:00）"""
        if sim_hours is None:
            sim_hours = self.env.now
        hour_of_day = sim_hours % 24
        
        # 使用配置的工作时间
        day_start = self.config.get("day_start_hour", 8)
        day_end = self.config.get("day_end_hour", 20)
        
        return day_start <= hour_of_day < day_end

    def is_night_shift(self, sim_hours: float = None) -> bool:
        """P2-10: 判断是否为夜班（可配置，默认20:00-08:00）"""
        if sim_hours is None:
            sim_hours = self.env.now
        hour_of_day = sim_hours % 24
        
        # 使用配置的工作时间
        day_start = self.config.get("day_start_hour", 8)
        day_end = self.config.get("day_end_hour", 20)
        
        # 夜班 = 不在工作时间内
        return hour_of_day < day_start or hour_of_day >= day_end

    def get_shift_efficiency(self, sim_hours: float = None) -> float:
        """P2-10: 获取当前班次效率系数"""
        if self.is_night_shift(sim_hours):
            return self.config.get("night_shift_efficiency", 0.92)  # 夜班效率（默认92%）
        return 1.0

    def wait_until_next_work_start(self):
        """等待到下一个工作日的开始时间（可配置）"""
        current = self.env.now
        day = int(current // 24)
        hour = current % 24
        
        # 使用配置的工作开始时间
        day_start = self.config.get("day_start_hour", 8)
        
        if hour < day_start:
            next_start = day * 24 + day_start
        else:
            next_start = (day + 1) * 24 + day_start
        return self.env.timeout(next_start - current)

    def next_id(self, prefix: str) -> str:
        """生成带前缀的递增ID"""
        self.counters[prefix] += 1
        day = self.get_sim_day()
        return f"{prefix}-{day:03d}-{self.counters[prefix]:03d}"

    def get_route_for_product(self, product_id: str) -> Optional[str]:
        """获取产品的默认工艺路线"""
        for rid, steps in self.route_steps.items():
            if steps and steps[0].get("product_id") == product_id:
                return rid
        return None

    def get_setup_time(self, machine_id: str, from_product: str, to_product: str) -> int:
        """查询换线时间（分钟），默认30分钟"""
        if from_product == to_product:
            return 0
        key = (machine_id, from_product, to_product)
        return self.setup_matrix.get(key, 30)

    def get_machine_efficiency(self, machine_id: str, product_id: str, at_sim_hours: float = None) -> float:
        """P2-10: 查询机台效率系数（含班次折减）"""
        key = (machine_id, product_id)
        cap = self.machine_capabilities.get(key)
        base_efficiency = cap.get("efficiency_factor", 1.0) if cap else 1.0
        shift_factor = self.get_shift_efficiency(at_sim_hours)
        return base_efficiency * shift_factor

    # P2-12: CTP产能可用性估算
    def estimate_available_time(self, machine_id: str, horizon_hours: float = 24.0) -> float:
        """估算机台在未来horizon_hours内的可用加工时间（扣除已排产和维护）"""
        state = self.machine_state.get(machine_id, {})
        next_avail = state.get("next_available_time", self.env.now)
        already_occupied = max(0.0, next_avail - self.env.now)
        # 工作时间 × 班次利用率 - 已占用时间
        work_hours_per_day = self.config.get("work_hours_per_day", 12.0)
        work_hours_in_horizon = horizon_hours * (work_hours_per_day / 24.0)
        buffer = self.config.get("ctp_capacity_buffer", 0.15)
        return max(0.0, work_hours_in_horizon * (1.0 - buffer) - already_occupied)

    # P2-12: CTP交期承诺（完整优化版）
    def estimate_completion_date(self, product_id: str, qty: float) -> datetime:
        """
        基于产能负荷估算工单完工日期（优化版：考虑真实生产约束）
        
        计算公式：
        total_hours = 加工时间 + 等待转运 + 排队时间(动态) + 换线时间 + IPQC检验 
                    + 物料等待 + 周日跳过 + 故障缓冲 + 安全缓冲
        """
        route_id = self.get_route_for_product(product_id)
        if not route_id:
            return self.sim_time_to_datetime(self.env.now) + timedelta(days=self.config["lead_time_commitment_days"])

        steps = sorted(self.route_steps.get(route_id, []), key=lambda x: x["sequence_no"])
        
        # 初始化各项时间
        total_process_hours = 0.0
        total_wait_hours = 0.0
        total_transport_hours = 0.0
        total_queue_hours = 0.0
        total_setup_hours = 0.0
        total_ipqc_hours = 0.0
        
        num_lots = max(1, math.ceil(qty / self.config["wip_lot_size"]))
        
        # 换线相关参数（基于Setup Group配置）
        setup_skip_enabled = self.config.get("setup_skip_same_group", False)
        
        # IPQC相关参数
        ipqc_time = self.config.get("avg_ipqc_time_hours", 0.33)  # 20分钟
        ipqc_fail_rate = self.config.get("ipqc_rework_rate", 0.15)  # 15%不合格
        ipqc_rework_time = self.config.get("ipqc_rework_time_hours", 0.5)  # 返工30分钟
        
        # 日夜班加权效率
        avg_efficiency_factor = self.config.get("ctp_avg_efficiency", 0.96)
        
        # 遍历所有工序
        for step in steps:
            std_time = step["standard_time_hours"]
            wait = step.get("wait_time_hours", 0.0)
            transport = step.get("transport_time_hours", 0.0)
            wc_id = step.get("machine_type_required")
            
            # 1. 加工时间（含夜班效率折减）
            machines_in_wc = [m for m in self.machines.values() 
                              if m.get("work_center_id") == wc_id]
            if machines_in_wc:
                best_efficiency = max(
                    self.machine_capabilities.get((m["machine_id"], product_id), {}).get("efficiency_factor", 1.0)
                    for m in machines_in_wc
                )
                min_eff = self.config.get("min_efficiency_factor", 0.5)
                # 使用加权平均效率（日班100% + 夜班92%）
                process_time = std_time * num_lots / (max(best_efficiency, min_eff) * avg_efficiency_factor)
            else:
                process_time = std_time * num_lots
            
            total_process_hours += process_time
            total_wait_hours += wait
            total_transport_hours += transport
            
            # 2. 排队时间（基于工作中心负荷动态计算）⭐
            avg_load = self.estimate_work_center_load(wc_id)
            
            if avg_load < 0.5:
                queue_time = self.config.get("queue_hours_low_load", 4.0)
            elif avg_load < 0.7:
                queue_time = self.config.get("queue_hours_medium_load", 10.0)
            elif avg_load < 0.85:
                queue_time = self.config.get("queue_hours_high_load", 18.0)
            else:
                queue_time = self.config.get("queue_hours_bottleneck", 36.0)
            
            total_queue_hours += queue_time
            
            # 3. 换线时间估算（基于Setup Group逻辑）
            # 假设：第一道工序需要换线，后续工序如果Setup Group不同则需要换线
            # 保守估计：70%工序需要换线（考虑多工单混合生产）
            if not setup_skip_enabled:
                # 如果未启用Setup Group减免，所有工序都考虑换线
                setup_probability = 1.0
            else:
                # 启用Setup Group减免，估计70%需要换线
                setup_probability = 0.70
            
            # 查询该机台的平均换线时间
            if machines_in_wc:
                # 取第一个机台的换线时间作为代表
                mid = machines_in_wc[0]["machine_id"]
                avg_setup_min = self.get_setup_time(mid, "UNKNOWN", product_id)
                avg_setup_hours = avg_setup_min / 60.0
            else:
                avg_setup_hours = 0.5  # 默认0.5小时
            
            expected_setup = setup_probability * avg_setup_hours
            total_setup_hours += expected_setup
        
        # 4. IPQC检验时间（基于换线次数）
        # 换线次数 = 工序数 × 换线概率
        num_setups = len(steps) * (0.70 if setup_skip_enabled else 1.0)
        expected_ipqc_per_setup = ipqc_time + ipqc_fail_rate * ipqc_rework_time
        total_ipqc_hours = num_setups * expected_ipqc_per_setup
        
        # 5. 物料等待时间（简化估算）
        material_delay = self.config.get("avg_material_delay_hours", 12.0)
        
        # 6. 故障缓冲（加工时间的5%）
        breakdown_buffer = total_process_hours * 0.05
        
        # 7. 总计（不含周日跳过）
        total_hours = (total_process_hours + total_wait_hours + 
                      total_transport_hours + total_queue_hours +
                      total_setup_hours + total_ipqc_hours +
                      material_delay + breakdown_buffer +
                      self.config.get("ctp_buffer_hours", 4.0))
        
        # 8. 计算周日跳过 ⭐
        current_dt = self.sim_time_to_datetime(self.env.now)
        estimated_end_dt = current_dt + timedelta(hours=total_hours)
        sunday_delay = self.calculate_sunday_delay(current_dt, estimated_end_dt)
        
        total_hours += sunday_delay
        
        # 9. 最终日期
        completion_date = current_dt + timedelta(hours=total_hours)
        
        # 10. 与最低承诺交期比较（不低于7天）
        committed_date = current_dt + timedelta(
            days=self.config.get("lead_time_commitment_days", 7)
        )
        required_date = max(completion_date, committed_date)
        
        # 打印CTP分解（便于调试）
        logger.debug(f"  [CTP计算] {product_id}×{qty}: 加工{total_process_hours:.1f}h + 排队{total_queue_hours:.1f}h + 换线{total_setup_hours:.1f}h + IPQC{total_ipqc_hours:.1f}h + 周日{sunday_delay:.1f}h = {total_hours:.1f}h ({total_hours/24:.1f}天)")
        
        return required_date
    
    def estimate_work_center_load(self, wc_id: str) -> float:
        """
        估算工作中心当前负荷（0.0-1.0+）
        
        计算方法：
        - 统计该机台未来24小时已排程任务
        - 负荷 = 已排程时间 / 可用时间
        - 负荷>1.0表示已超负荷
        """
        machines_in_wc = [m for m in self.machines.values() 
                          if m.get("work_center_id") == wc_id]
        
        if not machines_in_wc:
            return 0.0
        
        total_load_hours = 0.0
        total_available_hours = len(machines_in_wc) * 24.0  # 24小时窗口
        
        for machine in machines_in_wc:
            mid = machine["machine_id"]
            state = self.machine_state.get(mid, {})
            
            # 机台下次可用时间
            next_avail = state.get("next_available_time", self.env.now)
            
            # 已占用时间（从当前到下次可用）
            occupied = max(0.0, next_avail - self.env.now)
            
            # 限制在24小时内
            occupied = min(occupied, 24.0)
            
            total_load_hours += occupied
        
        return total_load_hours / total_available_hours
    
    def calculate_sunday_delay(self, start_dt: datetime, end_dt: datetime) -> float:
        """
        计算两个日期之间的周日延迟时间
        
        规则：
        - 周日不生产（24小时）
        - 如果跨周日，加24小时延迟
        """
        # 快速计算（避免循环）
        total_days = (end_dt - start_dt).days
        if total_days <= 0:
            return 0.0
        
        start_weekday = start_dt.weekday()
        
        # 完整周数
        full_weeks = total_days // 7
        
        # 剩余天数
        remaining_days = total_days % 7
        
        # 周日数量 = 完整周数 + 剩余天数中是否包含周日
        sunday_count = full_weeks
        
        # 检查剩余天数是否跨越周日
        if start_weekday <= 6 < start_weekday + remaining_days:
            sunday_count += 1
        
        return sunday_count * 24.0

    # ========================================================================
    # 库存管理
    # ========================================================================

    def init_inventory(self, initial_data: List[dict]):
        """初始化库存状态"""
        for item in initial_data:
            mid = item["material_id"]
            self.inventory_state[mid] = {
                "total": item["total_quantity"],
                "available": item["available_quantity"],
                "reserved": item["reserved_quantity"],
                "in_transit": 0.0
            }

    def record_inventory_transaction(self, material_id: str, trans_type: str, quantity: float,
                                     related_doc_type: str = None, related_doc_id: str = None,
                                     from_wo: str = None, to_wo: str = None, description: str = "") -> str:
        """记录库存事务并更新状态"""
        inv = self.inventory_state.get(material_id)
        if not inv:
            return None

        trans_id = self.next_id("IT")

        # 更新库存状态
        if trans_type in ["采购入库", "IQC入库", "生产入库", "调拨入库"]:
            inv["total"] += quantity
            if trans_type == "调拨入库":
                inv["reserved"] += quantity
            else:
                inv["available"] += quantity
        elif trans_type in ["生产领料", "预留"]:
            inv["available"] -= quantity
            inv["reserved"] += quantity
        elif trans_type == "生产消耗":
            # 实际消耗：reserved 减少，total 减少（物料真正出库）
            inv["reserved"] = max(0, inv["reserved"] - quantity)
            inv["total"] = max(0, inv["total"] - quantity)
        elif trans_type == "释放预留":
            inv["reserved"] -= quantity
            inv["available"] += quantity
        elif trans_type == "调拨出库":
            inv["reserved"] -= quantity
            inv["total"] -= quantity
        elif trans_type == "出库":
            inv["total"] -= quantity
            inv["available"] -= quantity

        # 确保非负
        inv["total"] = max(0, inv["total"])
        inv["available"] = max(0, inv["available"])
        inv["reserved"] = max(0, inv["reserved"])

        trans_data = {
            "transaction_id": trans_id,
            "material_id": material_id,
            "transaction_type": trans_type,
            "quantity": quantity,
            "balance_after": inv["total"],
            "available_balance_after": inv["available"],
            "reserved_balance_after": inv["reserved"],
            "related_document_type": related_doc_type,
            "related_document_id": related_doc_id,
            "from_work_order_id": from_wo,
            "to_work_order_id": to_wo,
            "transaction_time": self.sim_time_to_datetime(self.env.now),
            "description": description,
            "created_by": "DES仿真"
        }

        self.transaction_buffer.append(trans_data)
        if len(self.transaction_buffer) >= self.buffer_flush_size:
            self.flush_transactions()

        return trans_id

    def flush_transactions(self):
        """批量刷新库存事务到数据库"""
        if self.transaction_buffer:
            self.db.bulk_insert("inventory_transaction", self.transaction_buffer)
            self.transaction_buffer.clear()
    
    def _sync_inventory_to_db(self):
        """
        仿真结束时将内存中的库存状态同步到数据库
        
        解决原问题：仿真过程中只在内存更新库存，结束后inventory表仍是初始数据
        现在会在仿真结束时将所有物料的最新库存状态写入数据库
        """
        print(f"\n[数据同步] 正在将库存状态同步到数据库...")
        sync_count = 0
        current_time = self.sim_time_to_datetime(self.env.now)
        
        for material_id, inv in self.inventory_state.items():
            self.db.update(
                "inventory",
                {"material_id": material_id},
                {
                    "total_quantity": inv["total"],
                    "available_quantity": inv["available"],
                    "reserved_quantity": inv["reserved"],
                    "in_transit_quantity": inv.get("in_transit", 0),
                    "last_updated": current_time
                }
            )
            sync_count += 1
        
        print(f"  ✅ 已同步 {sync_count} 个物料的库存状态到数据库")
    
    def _sync_fg_inventory_to_db(self):
        """
        仿真结束时将内存中的成品库存状态同步到数据库
        
        与 _sync_inventory_to_db 类似，但针对成品库存（finished_goods_inventory）
        """
        print(f"[数据同步] 正在将成品库存状态同步到数据库...")
        sync_count = 0
        current_time = self.sim_time_to_datetime(self.env.now)
        
        for product_id, fg_inv in self.fg_inventory_state.items():
            fg_inv_id = f"FGI-{product_id}"
            self.db.update(
                "finished_goods_inventory",
                {"fg_inv_id": fg_inv_id},
                {
                    "total_quantity": fg_inv["total"],
                    "available_quantity": fg_inv["available"],
                    "reserved_quantity": fg_inv["reserved"],
                    "shipped_quantity": fg_inv.get("shipped", 0),
                    "last_updated": current_time
                }
            )
            sync_count += 1
        
        print(f"  ✅ 已同步 {sync_count} 个产品的成品库存状态到数据库")

    # ========================================================================
    # 机台状态管理
    # ========================================================================

    def init_machines(self, machines_data: List[dict]):
        """初始化机台资源和状态"""
        for m in machines_data:
            mid = m["machine_id"]
            self.machine_resources[mid] = simpy.Resource(self.env, capacity=1)
            self.machine_state[mid] = {
                "status": "空闲",
                "current_product": None,
                "current_wo": None,
                "current_task": None,
                "next_available_time": self.env.now,
                "total_run_hours": 0.0,
                "total_setup_hours": 0.0,
                "total_idle_hours": 0.0,
                "last_pm_hours": 0.0,    # P0-4: 上次PM的运行时间点
            }
            self.machine_last_product[mid] = None

    def log_machine_status(self, machine_id: str, status: str, product_id: str = None,
                           wo_id: str = None, task_id: str = None, oee: float = None):
        """记录机台状态日志"""
        log_data = {
            "log_id": self.next_id("MSL"),
            "machine_id": machine_id,
            "status_time": self.sim_time_to_datetime(self.env.now),
            "status": status,
            "product_id": product_id,
            "running_wo_id": wo_id,
            "running_task_id": task_id,
            "oee": oee,
            "note": f"Simulation day {self.get_sim_day()}"
        }
        self.status_log_buffer.append(log_data)
        if len(self.status_log_buffer) >= self.buffer_flush_size:
            self.flush_status_logs()

    def flush_status_logs(self):
        """批量刷新机台状态日志"""
        if self.status_log_buffer:
            self.db.bulk_insert("machine_status_log", self.status_log_buffer)
            self.status_log_buffer.clear()

    # ========================================================================
    # 核心仿真事件：客户订单生成
    # ========================================================================

    def order_generator(self):
        """每天生成客户订单（泊松分布）"""
        while True:
            yield self.wait_until_next_work_start()

            # 每天订单数 ~ Poisson(lambda)
            n_orders = poisson_sample(self.config["order_arrival_lambda"])

            for _ in range(n_orders):
                product = random.choice(list(self.products.values()))
                qty = random.randint(self.config["order_quantity_min"], self.config["order_quantity_max"])
                priority_weights = self.config.get("order_priority_weights", [0.2, 0.3, 0.5])
                priority = random.choices([1, 3, 5], weights=priority_weights)[0]

                order_id = self.next_id("CO")
                order_date = self.sim_time_to_datetime(self.env.now)
                
                # 【客户管理】从真实客户中选择
                customer = random.choice(self.customers)
                
                # 查询该客户是否购买此产品
                customer_products = self.customer_products.get(customer["customer_id"], [])
                valid_products = [cp["product_id"] for cp in customer_products]
                
                # 如果客户不购买此产品，重新选择
                if valid_products and product["product_id"] not in valid_products:
                    product_id = random.choice(valid_products)
                    product = self.products[product_id]
                
                # 查询客户特定价格和交期
                cp_info = next((cp for cp in customer_products if cp["product_id"] == product["product_id"]), None)
                unit_price = cp_info.get("special_price", 10.0) if cp_info else 10.0
                lead_time_days = cp_info.get("lead_time_days", 7) if cp_info else 7
                quality_level = cp_info.get("quality_level", "标准") if cp_info else "标准"

                # P2-12: 基于产能负荷计算真实交期承诺
                ctp_date = self.estimate_completion_date(product["product_id"], qty)
                committed_date = order_date + timedelta(days=self.config["lead_time_commitment_days"])
                required_date = max(ctp_date, committed_date)
                
                # 客户PO号
                customer_po = f"PO-{customer['customer_id']}-{order_date.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

                order_data = {
                    "order_id": order_id,
                    "customer_id": customer["customer_id"],
                    "customer_name": customer["customer_name"],
                    "customer_po_number": customer_po,
                    "product_id": product["product_id"],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "order_date": order_date,
                    "required_date": required_date,
                    "priority": priority,
                    "status": "已确认",
                    "shipping_address": customer.get("address", ""),
                    "quality_requirement": quality_level,
                    "packaging_requirement": "标准包装" if customer["customer_level"] == "普通" else "防静电包装",
                    "note": f"客户等级:{customer['customer_level']}, 行业:{customer.get('industry', '')}"
                }
                self.db.insert("customer_order", order_data)
                
                logger.info(f"  [订单] {order_id}: {customer['customer_name']}({customer['customer_id']}) → {product['product_id']}×{qty}, "
                           f"单价={unit_price}, 优先级=P{priority}")

                # 自动创建WorkOrder
                self.create_work_order(order_data)

            # 等待到下一天
            yield self.env.timeout(24)

    def create_work_order(self, order_data: dict):
        """基于客户订单创建生产工单（投入过量方案）"""
        product_id = order_data["product_id"]
        order_qty = order_data["quantity"]  # 客户订单数量（需要的良品数）
        order_id = order_data["order_id"]
        priority = order_data.get("priority", 5)

        wo_id = self.next_id("WO")
        now_dt = self.sim_time_to_datetime(self.env.now)
        planned_start = now_dt + timedelta(hours=4)
        
        # 【投入过量方案】根据工序总良率反推需要投入的数量
        planned_qty = self.calculate_required_input_qty(product_id, order_qty)
        
        logger.info(f"  [工单创建] {wo_id}: 订单{order_qty}个 → 计划投入{planned_qty:.1f}个（良率补偿）")

        # P2-12: 用CTP估算计划完工日期（使用投入量计算）
        planned_completion = self.estimate_completion_date(product_id, planned_qty)

        wo_data = {
            "work_order_id": wo_id,
            "customer_order_id": order_id,
            "product_id": product_id,
            "planned_quantity": planned_qty,  # 计划投入量（过量）
            "planned_start_date": planned_start,
            "planned_completion_date": planned_completion,
            "status": "已下达",
            "work_order_type": "正常",
            "priority": priority,
            "setup_group": self.products.get(product_id, {}).get("setup_group", "DEFAULT"),
            "completed_quantity": 0.0,
            "scrapped_quantity": 0.0,
            "expected_output_qty": order_qty,  # 预期产出量（订单数量）
            "created_at": now_dt
        }
        self.db.insert("work_order", wo_data)
        self.work_order_state[wo_id] = {
            "status": "已下达",
            "current_step_idx": 0,
            "allocated_materials": {},
            "product_id": product_id,
            "quantity": planned_qty,  # 使用投入量
            "order_quantity": order_qty  # 保存订单数量
        }

        # 展开工单工序（使用投入量）
        self.expand_work_order_operations(wo_id, product_id, planned_qty, priority)

        # 展开工单物料需求（使用投入量）
        self.expand_work_order_materials(wo_id, product_id, planned_qty, planned_start)

        # 创建WIP Lot（使用投入量）
        self.create_wip_lots(wo_id, product_id, planned_qty)

        return wo_id
    
    def calculate_required_input_qty(self, product_id: str, required_output_qty: float) -> float:
        """
        根据工序总良率反推需要投入的数量
        
        公式：投入量 = 需求产出量 / 总良率
        总良率 = 工序1良率 × 工序2良率 × ... × 工序N良率
        
        参数：
        - product_id: 产品ID
        - required_output_qty: 需要的良品数量（订单数量）
        
        返回：
        - required_input_qty: 需要投入的数量
        """
        route_id = self.get_route_for_product(product_id)
        if not route_id:
            # 无工艺路线，直接返回订单数量
            return required_output_qty
        
        steps = self.route_steps.get(route_id, [])
        if not steps:
            return required_output_qty
        
        # 计算总良率
        total_yield_rate = 1.0
        for step in steps:
            # 每道工序的良率 = 工序标准良率
            step_yield = step.get("yield_rate_standard", self.config.get("default_yield_rate", 0.98))
            total_yield_rate *= step_yield
        
        # 反推投入量
        required_input_qty = required_output_qty / total_yield_rate
        
        # 向上取整到Lot大小的倍数
        lot_size = self.config.get("wip_lot_size", 25)
        required_input_qty = math.ceil(required_input_qty / lot_size) * lot_size
        
        return required_input_qty

    def expand_work_order_operations(self, wo_id: str, product_id: str, qty: float, priority: int):
        """按工艺路线展开工单工序"""
        route_id = self.get_route_for_product(product_id)
        if not route_id:
            return

        steps = self.route_steps.get(route_id, [])
        steps = sorted(steps, key=lambda x: x["sequence_no"])

        # P0-2: 计算每道工序的预估投入数量（考虑良率逐步损耗）
        input_qty = qty
        now_dt = self.sim_time_to_datetime(self.env.now)
        cumulative_offset = self.config.get("initial_offset_hours", 4.0)  # 距现在4小时开始

        for i, step in enumerate(steps):
            wo_op_id = f"{wo_id}-OP{step['sequence_no']:02d}"

            std_time = step["standard_time_hours"]
            wait = step.get("wait_time_hours", 0.0)
            transport = step.get("transport_time_hours", 0.0)

            # 计算各工序计划时间（累积偏移）
            planned_start = now_dt + timedelta(hours=cumulative_offset)
            # Lot批量加工：std_time已经按批量调整过，直接使用
            planned_duration = std_time
            planned_end = planned_start + timedelta(hours=planned_duration + wait + transport)

            op_data = {
                "wo_op_id": wo_op_id,
                "work_order_id": wo_id,
                "step_id": step["step_id"],
                "sequence_no": step["sequence_no"],
                "planned_start": planned_start,
                "planned_end": planned_end,
                "required_input_qty": round(input_qty, 4),  # P0-2: 实际投入量（含良率损耗）
                "status": "待开工",
                "setup_completed": False,
                "material_issued": False
            }
            self.db.insert("work_order_operation", op_data)

            # P0-2: 下一道工序的投入 = 本道工序产出（×良率）
            yield_rate = step.get("yield_rate_standard", self.config.get("default_yield_rate", 0.98))
            input_qty *= yield_rate  # 传递给下一道工序
            # 累积偏移：加工时间 + 等待/转运 + 排队时间（批量加工后排对时间应减少）
            queue_time = self.config.get("queue_time_hours", 0.5)  # 工序间排队时间
            cumulative_offset += planned_duration + wait + transport + queue_time

    def expand_work_order_materials(self, wo_id: str, product_id: str, qty: float, base_date: datetime):
        """按BOM展开工单物料需求（P2-C7: 过滤BOM有效期）"""
        all_boms = self.boms.get(product_id, [])
        # P2-C7: 过滤有效期
        order_date = base_date.date() if hasattr(base_date, 'date') else base_date
        boms = [
            b for b in all_boms
            if (b.get("effective_date") is None or b["effective_date"] <= order_date)
            and (b.get("expiry_date") is None or b["expiry_date"] >= order_date)
        ]

        for bom in boms:
            material_id = bom["material_id"]
            required_qty = bom["quantity_per_unit"] * qty
            step_id = bom.get("step_id")

            required_date = base_date
            if step_id:
                route_id = self.get_route_for_product(product_id)
                steps = self.route_steps.get(route_id, [])
                for step in steps:
                    if step["step_id"] == step_id:
                        offset = (step["sequence_no"] // 10 - 1) * 24
                        required_date = base_date + timedelta(hours=offset - step.get("material_ready_offset_hours", 2))
                        break

            wom_id = self.next_id("WOM")
            seq = step_id.split("-")[-1] if step_id else "10"  # 从step_id提取序号
            try:
                seq_no = int(seq)
            except Exception:
                seq_no = 10

            wom_data = {
                "wom_id": wom_id,
                "work_order_id": wo_id,
                "wo_op_id": f"{wo_id}-OP{seq_no:02d}" if step_id else None,
                "material_id": material_id,
                "required_quantity": required_qty,
                "allocated_quantity": 0.0,
                "consumed_quantity": 0.0,
                "shortage_quantity": 0.0,
                "required_date": required_date,
                "status": "待分配"
            }
            self.db.insert("work_order_material", wom_data)

    def create_wip_lots(self, wo_id: str, product_id: str, total_qty: float):
        """将工单分解为WIP Lot"""
        lot_size = self.config["wip_lot_size"]
        num_lots = int(total_qty // lot_size)
        remainder = total_qty % lot_size

        lots = []
        for i in range(num_lots):
            lots.append(lot_size)
        if remainder > 0:
            lots.append(remainder)

        for i, lqty in enumerate(lots):
            lot_id = f"{wo_id}-LOT{i+1:02d}"
            lot_data = {
                "lot_id": lot_id,
                "work_order_id": wo_id,
                "product_id": product_id,
                "lot_quantity": lqty,
                "actual_quantity": lqty,  # P0-2: 初始actual_quantity = lot_quantity
                "lot_status": "排队中",
                "queue_start_time": self.sim_time_to_datetime(self.env.now),
                "priority": self.work_order_state[wo_id].get("priority", 5)
            }
            self.db.insert("wip_lot", lot_data)
            self.wip_lot_state[lot_id] = {
                "wo_id": wo_id,
                "product_id": product_id,
                "current_step_idx": 0,
                "status": "排队中",
                "current_qty": lqty   # P0-2: 追踪当前Lot实际数量
            }

    # ========================================================================
    # 核心仿真事件：MRP运算与缺料处理
    # ========================================================================

    def daily_mrp_processor(self):
        """每天运行MRP：检查缺料、执行调拨、创建采购"""
        while True:
            yield self.wait_until_next_work_start()
            yield self.env.timeout(0.5)  # 8:30 运行MRP

            logger.info(f"[Day {self.get_sim_day()} 08:30] 运行MRP运算...")

            # 获取所有待分配物料
            pending_woms = self.db.query_pending_woms()

            for wom in pending_woms:
                self.process_material_allocation(wom)

            # 检查缺料：优先替代料 → 调拨 → 采购
            shortage_woms = self.db.query_shortage_woms()
            for wom in shortage_woms:
                # P1-7: 先尝试替代料
                remaining = self.try_substitute_material(wom)
                if remaining > 0:
                    # 再尝试调拨
                    self.try_material_transfer(wom)

            # 对仍缺料的创建采购订单（含EOQ策略）
            remaining_shortage = self.db.query_shortage_woms()
                    
            # 【合并采购】按供应商分组，同一供应商的物料合并为一个PO
            supplier_groups = self.group_shortage_by_supplier(remaining_shortage)
                    
            for supplier_id, shortage_list in supplier_groups.items():
                self.create_merged_purchase_order(supplier_id, shortage_list)

            yield self.env.timeout(23.5)  # 等待到下一天

    def process_material_allocation(self, wom: dict):
        """处理物料分配"""
        material_id = wom["material_id"]
        required = wom["required_quantity"]
        wom_id = wom["wom_id"]
        wo_id = wom["work_order_id"]

        inv = self.inventory_state.get(material_id)
        if not inv:
            return

        available = inv["available"]
        if available >= required:
            inv["available"] -= required
            inv["reserved"] += required

            self.db.update("work_order_material", {"wom_id": wom_id}, {
                "allocated_quantity": required,
                "shortage_quantity": 0.0,
                "status": "已齐套"
            })

            self.record_inventory_transaction(
                material_id, "预留", required,
                related_doc_type="WorkOrderMaterial", related_doc_id=wom_id,
                to_wo=wo_id, description=f"工单{wo_id}物料预留"
            )
        else:
            if available > 0:
                inv["available"] -= available
                inv["reserved"] += available

                self.db.update("work_order_material", {"wom_id": wom_id}, {
                    "allocated_quantity": available,
                    "shortage_quantity": required - available,
                    "status": "部分分配"
                })

                self.record_inventory_transaction(
                    material_id, "预留", available,
                    related_doc_type="WorkOrderMaterial", related_doc_id=wom_id,
                    to_wo=wo_id, description=f"工单{wo_id}物料部分预留"
                )
            else:
                self.db.update("work_order_material", {"wom_id": wom_id}, {
                    "shortage_quantity": required,
                    "status": "缺料"
                })

    def try_substitute_material(self, shortage_wom: dict) -> float:
        """P1-7: 尝试使用替代料满足缺料需求
        返回：剩余缺料量（0表示已完全满足）
        """
        material_id = shortage_wom["material_id"]
        shortage_qty = shortage_wom.get("shortage_quantity", 0)
        wom_id = shortage_wom["wom_id"]
        wo_id = shortage_wom["work_order_id"]

        if shortage_qty <= 0:
            return 0.0

        substitutes = self.material_substitutes.get(material_id, [])
        # 按优先级排序
        substitutes = sorted(substitutes, key=lambda x: x.get("substitute_priority", 99))

        for sub in substitutes:
            if sub.get("approval_status") not in ("已批准", "客户批准"):
                continue

            sub_mat_id = sub["substitute_material_id"]
            sub_inv = self.inventory_state.get(sub_mat_id)
            
            # 【完整替代料策略】如果替代料库存不足，触发采购
            available = sub_inv["available"] if sub_inv else 0
            if available <= 0:
                # 替代料也没库存，创建缺料记录（由MRP主流程统一合并采购）
                logger.info(f"  [替代料缺料] {sub_mat_id}库存不足，创建缺料记录")
                sub_shortage_wom = {
                    "wom_id": self.next_id("WOM"),
                    "work_order_id": wo_id,
                    "wo_op_id": shortage_wom.get("wo_op_id"),
                    "material_id": sub_mat_id,
                    "required_quantity": shortage_qty,
                    "allocated_quantity": 0,
                    "consumed_quantity": 0.0,
                    "shortage_quantity": shortage_qty,
                    "required_date": shortage_wom.get("required_date"),
                    "status": "缺料",
                    "note": f"替代{material_id}，需采购"
                }
                self.db.insert("work_order_material", sub_shortage_wom)
                # 不立即创建PO，而是让MRP主流程在查询shortage_woms时统一处理
                continue
            
            use_qty = min(shortage_qty, available)

            # 从替代料库存扣减
            sub_inv["available"] -= use_qty
            sub_inv["reserved"] += use_qty

            # 创建替代料WOM（新增一行替代料需求）
            sub_wom_id = self.next_id("WOM")
            sub_wom_data = {
                "wom_id": sub_wom_id,
                "work_order_id": wo_id,
                "wo_op_id": shortage_wom.get("wo_op_id"),
                "material_id": sub_mat_id,
                "required_quantity": use_qty,
                "allocated_quantity": use_qty,
                "consumed_quantity": 0.0,
                "shortage_quantity": 0.0,
                "required_date": shortage_wom.get("required_date"),
                "status": "已齐套",
                "note": f"替代{material_id}，来自MaterialSubstitute"
            }
            self.db.insert("work_order_material", sub_wom_data)

            # 更新原始缺料WOM
            shortage_qty -= use_qty
            new_shortage = max(0, shortage_qty)
            new_allocated = shortage_wom.get("allocated_quantity", 0) + use_qty
            new_required = shortage_wom.get("required_quantity", 0)
            new_status = "已齐套" if new_shortage == 0 else "部分分配"

            self.db.update("work_order_material", {"wom_id": wom_id}, {
                "allocated_quantity": new_allocated,
                "shortage_quantity": new_shortage,
                "status": new_status
            })

            self.record_inventory_transaction(
                sub_mat_id, "预留", use_qty,
                related_doc_type="WorkOrderMaterial", related_doc_id=sub_wom_id,
                to_wo=wo_id, description=f"替代料{sub_mat_id}预留给工单{wo_id}"
            )

            logger.info(f"  [替代料] {material_id}→{sub_mat_id}: 工单{wo_id}, 数量={use_qty:.1f}, 剩余缺料={shortage_qty:.1f}")

            if shortage_qty <= 0:
                break

        return shortage_qty

    def try_material_transfer(self, shortage_wom: dict):
        """尝试从其他工单调拨物料"""
        material_id = shortage_wom["material_id"]
        shortage_qty = shortage_wom.get("shortage_quantity", 0)
        wom_id = shortage_wom["wom_id"]
        to_wo_id = shortage_wom["work_order_id"]

        if shortage_qty <= 0:
            return

        candidates = self.db.find_transfer_candidates(material_id, to_wo_id)

        for cand in candidates:
            from_wo_id = cand["work_order_id"]
            from_wom_id = cand["wom_id"]
            available_reserved = cand["allocated_quantity"] - cand.get("consumed_quantity", 0)

            from_wo = self.db.get_work_order(from_wo_id)
            if not from_wo:
                continue

            is_delayed = self.env.now > self.datetime_to_sim_hours(from_wo["planned_completion_date"])
            from_priority = from_wo.get("priority", 5)
            to_wo = self.db.get_work_order(to_wo_id)
            to_priority = to_wo.get("priority", 5) if to_wo else 5

            if not (is_delayed or from_priority > to_priority):
                continue

            transfer_qty = min(shortage_qty, available_reserved)
            if transfer_qty <= 0:
                continue

            self.execute_material_transfer(
                material_id, from_wo_id, to_wo_id, from_wom_id, wom_id, transfer_qty,
                is_delayed=is_delayed
            )

            shortage_qty -= transfer_qty
            if shortage_qty <= 0:
                break

    def execute_material_transfer(self, material_id: str, from_wo: str, to_wo: str,
                                  from_wom: str, to_wom: str, qty: float, is_delayed: bool):
        """执行物料调拨"""
        self.db.update("work_order_material", {"wom_id": from_wom}, {
            "allocated_quantity": lambda col: col - qty
        })

        to_wom_data = self.db.get_wom(to_wom)
        if to_wom_data:
            new_alloc = to_wom_data["allocated_quantity"] + qty
            new_req = to_wom_data["required_quantity"]
            new_shortage = max(0, new_req - new_alloc)
            new_status = "已齐套" if new_shortage == 0 else "部分分配"
            self.db.update("work_order_material", {"wom_id": to_wom}, {
                "allocated_quantity": new_alloc,
                "shortage_quantity": new_shortage,
                "status": new_status
            })

        transfer_id = self.next_id("MT")
        reason = "来源工单延期挪用" if is_delayed else "优先级调整挪用"

        transfer_data = {
            "transfer_id": transfer_id,
            "material_id": material_id,
            "from_work_order_id": from_wo,
            "to_work_order_id": to_wo,
            "from_wom_id": from_wom,
            "to_wom_id": to_wom,
            "quantity": qty,
            "transfer_reason": reason,
            "trigger_source": "MRP运算",
            "requested_time": self.sim_time_to_datetime(self.env.now),
            "executed_time": self.sim_time_to_datetime(self.env.now),
            "status": "已执行",
            "note": f"Day {self.get_sim_day()} 自动调拨"
        }
        self.db.insert("material_transfer", transfer_data)

        self.record_inventory_transaction(
            material_id, "调拨出库", qty,
            related_doc_type="MaterialTransfer", related_doc_id=transfer_id,
            from_wo=from_wo, to_wo=to_wo,
            description=f"调拨{qty:.1f}{self.materials.get(material_id, {}).get('unit_of_measure', '')}从{from_wo}到{to_wo}"
        )

        logger.info(f"  [调拨] {material_id}: {from_wo} -> {to_wo}, 数量={qty:.1f}, 原因={reason}")
    
    def get_supplier_performance_from_db(self, supplier_id: str) -> dict:
        """
        从数据库查询供应商历史交货表现（基于采购订单记录）
        
        返回：
        {
            "total_deliveries": 总交货次数,
            "on_time_deliveries": 准时交货次数,
            "recent_delays": 最近10次中的延迟次数,
            "avg_delay_days": 平均延迟天数,
            "on_time_rate": 准时率
        }
        """
        # 查询该供应商的所有已完成采购订单
        sql = """
            SELECT 
                po_id,
                order_date,
                expected_delivery_date,
                actual_delivery_date,
                julianday(actual_delivery_date) - julianday(expected_delivery_date) as delay_days
            FROM purchase_order
            WHERE supplier_id = ?
              AND status = '已入库'
              AND actual_delivery_date IS NOT NULL
            ORDER BY actual_delivery_date DESC
            LIMIT 100
        """
        rows = self.db._conn.execute(sql, (supplier_id,)).fetchall()
        
        if not rows:
            return {
                "total_deliveries": 0,
                "on_time_deliveries": 0,
                "recent_delays": 0,
                "avg_delay_days": 0.0,
                "on_time_rate": 1.0
            }
        
        total = len(rows)
        on_time = 0
        total_delay = 0.0
        recent_delays = 0
        
        for i, row in enumerate(rows):
            delay_days = row["delay_days"] if row["delay_days"] else 0.0
            total_delay += delay_days
            
            # 允许10%误差（1天以内的延迟算准时）
            is_on_time = (delay_days <= 1.0)
            if is_on_time:
                on_time += 1
            
            # 统计最近10次
            if i < 10 and not is_on_time:
                recent_delays += 1
        
        return {
            "total_deliveries": total,
            "on_time_deliveries": on_time,
            "recent_delays": recent_delays,
            "avg_delay_days": total_delay / total if total > 0 else 0.0,
            "on_time_rate": on_time / total if total > 0 else 1.0
        }
    
    def select_supplier_smart(self, material_id: str, suppliers: list, shortage_qty: float, wo_id: str) -> dict:
        """
        【完整供应商策略】智能选择供应商
        
        策略优先级：
        1. 紧急订单：选交期最短的供应商（即使贵20%）
        2. 成本优化：选最便宜的供应商（交期可接受）
        3. 默认策略：70%主供应商 + 30%备选供应商（负载均衡）
        4. 风险评估：避开最近频繁延迟的供应商
        5. 地缘分散：避免过度依赖单一地区
        
        返回：选中的供应商记录
        """
        if not suppliers:
            return None
        
        # 获取工单优先级（用于判断紧急程度）
        wo_info = self.work_order_state.get(wo_id, {})
        wo_priority = wo_info.get("priority", 3)
        
        # 策略1：紧急订单（P1/P2）→ 交期优先
        if wo_priority <= 2:
            # 选交期最短的供应商（即使不是主供应商）
            fastest = min(suppliers, key=lambda s: s.get("lead_time_days", 999))
            logger.info(f"  [紧急采购] {material_id}: 选{fastest['supplier_id']}（交期{fastest['lead_time_days']}天）")
            return fastest
        
        # 策略2：检查供应商近期表现（从数据库查询）
        unreliable_suppliers = set()
        for sup in suppliers:
            sup_id = sup["supplier_id"]
            perf = self.get_supplier_performance_from_db(sup_id)
            delay_count = perf.get("recent_delays", 0)
            if delay_count >= 3:  # 最近10次中延迟3次以上，标记为不可靠
                unreliable_suppliers.add(sup_id)
                logger.info(f"  [供应商评估] {sup_id}: 最近10次交货延迟{delay_count}次，准时率{perf['on_time_rate']:.0%}")
        
        # 过滤掉不可靠供应商（除非所有都不可靠）
        reliable_suppliers = [s for s in suppliers if s["supplier_id"] not in unreliable_suppliers]
        if reliable_suppliers:
            suppliers = reliable_suppliers
        
        # 策略3：默认策略 → 70%主供应商 + 30%备选供应商（负载均衡）
        preferred = [s for s in suppliers if s.get("is_preferred")]
        backup = [s for s in suppliers if not s.get("is_preferred")]
        
        if preferred and backup:
            # 有主供应商和备选供应商，执行负载均衡
            if random.random() < 0.7:
                # 70%概率选主供应商
                supplier = preferred[0]
                strategy = "主供应商"
            else:
                # 30%概率选备选供应商（维持供应商关系）
                supplier = backup[0]
                strategy = "备选供应商（负载均衡）"
            
            logger.info(f"  [智能采购] {material_id}: 选{supplier['supplier_id']}（{strategy}）")
            return supplier
        
        # 策略4：只有主供应商或只有备选供应商 → 选第一个
        if preferred:
            return preferred[0]
        
        return suppliers[0]
    
    def group_shortage_by_supplier(self, shortage_woms: list) -> dict:
        """
        按供应商分组缺料清单
        
        Returns:
            {
                'SUP-001': [wom1, wom2, ...],
                'SUP-002': [wom3, wom4, ...]
            }
        """
        supplier_groups = {}
        
        for wom in shortage_woms:
            material_id = wom["material_id"]
            sms = self.supplier_materials.get(material_id, [])
            
            if not sms:
                continue
            
            # 智能选择供应商
            supplier = self.select_supplier_smart(
                material_id, 
                sms, 
                wom.get("shortage_quantity", 0),
                wom.get("work_order_id", "")
            )
            
            supplier_id = supplier["supplier_id"]
            
            if supplier_id not in supplier_groups:
                supplier_groups[supplier_id] = []
            
            supplier_groups[supplier_id].append(wom)
        
        return supplier_groups
    
    def create_merged_purchase_order(self, supplier_id: str, shortage_list: list):
        """
        创建合并的采购订单（同一供应商的多个物料）
        
        Args:
            supplier_id: 供应商ID
            shortage_list: 缺料清单 [{material_id, shortage_quantity, wom_id, work_order_id, ...}]
        """
        if not shortage_list:
            return
        
        # 获取供应商信息（从第一个物料的供应商物料关系中获取）
        first_material = shortage_list[0]["material_id"]
        sms_list = self.supplier_materials.get(first_material, [])
        supplier = next((sm for sm in sms_list if sm["supplier_id"] == supplier_id), None)
        
        if not supplier:
            return
        
        # 创建PO主单
        po_id = self.next_id("PO")
        now_dt = self.sim_time_to_datetime(self.env.now)
        
        # 计算交期（取最长交期）
        max_lead_time = 0.0
        total_amount = 0.0
        
        for wom in shortage_list:
            material_id = wom["material_id"]
            shortage_qty = wom.get("shortage_quantity", 0)
            
            # 重新查询该物料的供应商信息
            mat_sms = self.supplier_materials.get(material_id, [])
            mat_supplier = next((sm for sm in mat_sms if sm["supplier_id"] == supplier_id), supplier)
            
            # EOQ计算
            mat_info = self.materials.get(material_id, {})
            eoq = mat_info.get("eoq", 0.0)
            min_order = mat_supplier.get("min_order_qty", shortage_qty)
            max_order = mat_supplier.get("max_order_qty", 0.0)
            
            if eoq > 0:
                base_qty = max(shortage_qty, eoq)
                if min_order > 0:
                    po_qty = math.ceil(base_qty / min_order) * min_order
                else:
                    po_qty = base_qty
            else:
                po_qty = max(shortage_qty, min_order)
            
            # 限制最大订购量
            if max_order > 0 and po_qty > max_order:
                po_qty = max_order
            
            # 交期扰动
            lead_time_mean = mat_supplier.get("lead_time_days", 3)
            lead_time_std = mat_supplier.get("lead_time_stddev_days", 0.5)
            actual_lead = normal_sample(lead_time_mean, lead_time_std, min_val=1.0)
            
            # 可靠性扰动
            reliability = mat_supplier.get("reliability_score", 0.95)
            if random.random() > reliability:
                extra_delay = random.randint(1, 3)
                actual_lead += extra_delay
            
            max_lead_time = max(max_lead_time, actual_lead)
            total_amount += po_qty * mat_supplier.get("unit_price", 1.0)
        
        # 创建PO
        expected_delivery = now_dt + timedelta(days=max_lead_time)
        
        po_data = {
            "po_id": po_id,
            "supplier_id": supplier_id,
            "order_date": now_dt,
            "expected_delivery_date": expected_delivery,
            "status": "已创建",
            "total_amount": total_amount,
            "note": f"合并采购，{len(shortage_list)}种物料"
        }
        self.db.insert("purchase_order", po_data)
        
        # 创建多个POL（每行一个物料）
        for idx, wom in enumerate(shortage_list, start=1):
            material_id = wom["material_id"]
            shortage_qty = wom.get("shortage_quantity", 0)
            wom_id = wom["wom_id"]
            wo_id = wom["work_order_id"]
            
            # 重新查询供应商信息
            mat_sms = self.supplier_materials.get(material_id, [])
            mat_supplier = next((sm for sm in mat_sms if sm["supplier_id"] == supplier_id), supplier)
            
            # EOQ计算
            mat_info = self.materials.get(material_id, {})
            eoq = mat_info.get("eoq", 0.0)
            min_order = mat_supplier.get("min_order_qty", shortage_qty)
            max_order = mat_supplier.get("max_order_qty", 0.0)
            
            if eoq > 0:
                base_qty = max(shortage_qty, eoq)
                if min_order > 0:
                    po_qty = math.ceil(base_qty / min_order) * min_order
                else:
                    po_qty = base_qty
            else:
                po_qty = max(shortage_qty, min_order)
            
            # 限制最大订购量
            if max_order > 0 and po_qty > max_order:
                po_qty = max_order
            
            # 创建POL（line_id与po_id关联）
            line_data = {
                "line_id": f"POL-{po_id}-{idx:03d}",
                "po_id": po_id,
                "material_id": material_id,
                "quantity": po_qty,
                "status": "待收货",
                "unit_price": mat_supplier.get("unit_price", 1.0),
                "related_work_order_id": wo_id,
                "related_wom_id": wom_id
            }
            self.db.insert("purchase_order_line", line_data)
            
            # 更新在途库存
            inv = self.inventory_state.get(material_id)
            if inv:
                inv["in_transit"] += po_qty
            
            # 标记安全库存补货进行中
            self.safety_stock_po_pending.discard(material_id)
            
            # 到货事件
            lead_time_mean = mat_supplier.get("lead_time_days", 3)
            lead_time_std = mat_supplier.get("lead_time_stddev_days", 0.5)
            actual_lead = normal_sample(lead_time_mean, lead_time_std, min_val=1.0)
            reliability = mat_supplier.get("reliability_score", 0.95)
            if random.random() > reliability:
                extra_delay = random.randint(1, 3)
                actual_lead += extra_delay
            
            self.env.process(self.purchase_arrival_event(po_id, material_id, po_qty, actual_lead))
        
        logger.info(f"  [合并采购] PO={po_id}, 供应商={supplier_id}, {len(shortage_list)}种物料, "
              f"总金额={total_amount:.0f}, 预计交货={expected_delivery.strftime('%m-%d')}")

    def _second_batch_arrival(self, po_id: str, material_id: str, qty: float, delay_days: float):
        """Task6: 分批到货的第二批"""
        yield self.env.timeout(delay_days * 24.0)
        logger.info(f"  [到货-2批] PO={po_id}, 物料={material_id}, 第二批数量={qty:.1f}")
        yield from self._receive_material_batch(po_id, material_id, qty, batch_no=2)

    def _receive_material_batch(self, po_id: str, material_id: str, qty: float, batch_no: int = 1):
        """Task6: 统一处理一批物料到货（IQC + 入库）"""
        # IQC检验
        qc_id = f"QC-{po_id}-B{batch_no}-{self.counters['qc']:04d}"
        self.counters['qc'] += 1
        sm_list = self.supplier_materials.get(material_id, [])
        supplier_id = sm_list[0]["supplier_id"] if sm_list else "SUP-001"

        inspection_result, scrap_qty, actual_qty = self._run_iqc(qty, material_id)
        self.db.insert("quality_inspection", {
            "inspection_id": qc_id,
            "inspection_type": "IQC来料检验",
            "po_id": po_id,
            "material_id": material_id,
            "related_doc_type": "PurchaseOrder",
            "related_doc_id": po_id,
            "inspect_qty": qty,
            "pass_qty": actual_qty,
            "scrap_qty": scrap_qty,
            "rework_qty": 0.0,
            "result": inspection_result,
            "inspector": "QC-AUTO",
            "inspection_time": self.sim_time_to_datetime(self.env.now),
            "note": f"第{batch_no}批到货IQC"
        })

        if actual_qty > 0:
            # 更新内存库存
            if material_id not in self.inventory_state:
                self.inventory_state[material_id] = {"total": 0, "available": 0, "reserved": 0, "in_transit": 0}
            inv = self.inventory_state[material_id]
            inv["total"] = inv.get("total", 0) + actual_qty
            inv["available"] = inv.get("available", 0) + actual_qty
            inv["in_transit"] = max(0, inv.get("in_transit", 0) - qty)

            # 写入库存事务
            self.record_inventory_transaction(
                material_id, "采购入库", actual_qty,
                related_doc_type="PurchaseOrder", related_doc_id=po_id,
                description=f"采购到货第{batch_no}批入库"
            )
        yield self.env.timeout(0)  # make it a generator

    def purchase_arrival_event(self, po_id: str, material_id: str, qty: float, lead_days: float):
        """P0-3: 采购到货事件（含IQC质检 + 增量MRP重分配）"""
        yield self.env.timeout(lead_days * 24)

        # Task6: 分批到货（30%概率）
        split_prob = self.config.get("split_delivery_prob", 0.30)
        if random.random() < split_prob and qty >= 10:
            batch1_ratio = random.uniform(0.60, 0.80)
            batch1_qty = round(qty * batch1_ratio, 2)
            batch2_qty = round(qty - batch1_qty, 2)
            delay_days = random.uniform(1.0, 3.0)
            logger.info(f"  [分批到货] PO={po_id}, 第1批{batch1_qty:.1f}, 第2批{batch2_qty:.1f}延{delay_days:.1f}天后到")
            # 启动第二批到货进程
            self.env.process(self._second_batch_arrival(po_id, material_id, batch2_qty, delay_days))
            # 本次只处理第一批
            qty = batch1_qty

        now_dt = self.sim_time_to_datetime(self.env.now)

        # T6: IQC入料质检（供应商可靠性越低，收货拒给概率越高）
        supplier = self.db.get_supplier_by_po(po_id)
        reliability = supplier.get("reliability_score", 0.95) if supplier else 0.95
        reject_qty = 0.0
        accepted_qty = qty
        iqc_result = "合格"
        iqc_disposition = "全数入库"

        # IQC失败概率 = 1 - reliability（有概率拒收部分批次）
        if random.random() > reliability:
            under_perf_range = self.config.get("under_performance_rate_range", [0.05, 0.15])
            reject_rate = random.uniform(under_perf_range[0], under_perf_range[1])  # 性能不达标率
            reject_qty = round(qty * reject_rate, 2)
            accepted_qty = qty - reject_qty
            iqc_result = "让步接收" if reject_rate < 0.10 else "拒收部分"
            iqc_disposition = f"拒收{reject_qty:.1f}，实收{accepted_qty:.1f}"
            logger.info(f"  [IQC] PO={po_id} {material_id}: 拒收{reject_qty:.1f}/{qty:.0f}（{reject_rate*100:.0f}%）")

        # 写入IQC质检记录
        insp_id = self.next_id("QI")
        self.db.insert("quality_inspection", {
            "inspection_id": insp_id,
            "inspection_type": "IQC入料",
            "po_id": po_id,
            "material_id": material_id,
            "related_doc_type": "PurchaseOrder",
            "related_doc_id": po_id,
            "inspection_time": now_dt,
            "inspect_qty": qty,
            "pass_qty": accepted_qty,
            "rework_qty": 0.0,
            "scrap_qty": 0.0,
            "concession_qty": reject_qty if iqc_result == "让步接收" else 0.0,
            "result": iqc_result,
            "is_hold": False,
            "disposition": iqc_disposition
        })

        # 更新采购订单状态（以实收数量为准）
        self.db.update("purchase_order", {"po_id": po_id}, {
            "status": "已到货",
            "actual_delivery_date": now_dt
        })
        self.db.update("purchase_order_line", {"po_id": po_id}, {
            "received_quantity": accepted_qty,
            "status": "全部到货" if reject_qty == 0 else "部分到货"
        })

        inv = self.inventory_state.get(material_id)
        if inv:
            inv["in_transit"] = max(0, inv["in_transit"] - qty)

        # 入库实收数量
        self.record_inventory_transaction(
            material_id, "IQC入库", accepted_qty,
            related_doc_type="PurchaseOrder", related_doc_id=po_id,
            description=f"采购订单{po_id}到货，IQC实收{accepted_qty:.1f}({iqc_result})"
        )

        logger.info(f"  [到货] {material_id}: PO={po_id}, 数量={accepted_qty:.0f}")
        
        # 【供应商绩效管理】更新数据库中的实际交货日期
        if supplier:
            supplier_id = supplier.get("supplier_id", "UNKNOWN")
            now_dt = self.sim_time_to_datetime(self.env.now)
            
            # 更新采购订单的实际交货日期
            self.db.update("purchase_order", {"po_id": po_id}, {
                "actual_delivery_date": now_dt,
                "status": "已入库"
            })
            
            # 从数据库查询供应商表现（用于日志输出）
            perf = self.get_supplier_performance_from_db(supplier_id)
            if perf["total_deliveries"] > 0:
                logger.info(f"  [供应商表现] {supplier_id}: 累计交货{perf['total_deliveries']}次，准时率{perf['on_time_rate']:.0%}，平均延迟{perf['avg_delay_days']:.1f}天")

        # P0-3: 到货后触发增量MRP重分配（以实收数量）
        self.incremental_mrp_after_arrival(material_id, accepted_qty)

    def incremental_mrp_after_arrival(self, material_id: str, arrived_qty: float):
        """P0-3: 到货后立即重新分配给等待中的缺料工单"""
        shortage_woms = self.db.query_shortage_woms_by_material(material_id)
        if not shortage_woms:
            return

        print(f"  [增量MRP] {material_id}到货{arrived_qty:.0f}，处理{len(shortage_woms)}个缺料工单...")

        for wom in shortage_woms:
            wom_id = wom["wom_id"]
            wo_id = wom["work_order_id"]
            shortage = wom.get("shortage_quantity", 0)
            if shortage <= 0:
                continue

            inv = self.inventory_state.get(material_id)
            if not inv or inv["available"] <= 0:
                break

            alloc_qty = min(shortage, inv["available"])
            inv["available"] -= alloc_qty
            inv["reserved"] += alloc_qty

            new_allocated = wom.get("allocated_quantity", 0) + alloc_qty
            new_shortage = max(0, shortage - alloc_qty)
            new_status = "已齐套" if new_shortage == 0 else "部分分配"

            self.db.update("work_order_material", {"wom_id": wom_id}, {
                "allocated_quantity": new_allocated,
                "shortage_quantity": new_shortage,
                "status": new_status
            })

            self.record_inventory_transaction(
                material_id, "预留", alloc_qty,
                related_doc_type="WorkOrderMaterial", related_doc_id=wom_id,
                to_wo=wo_id, description=f"到货后增量MRP分配给工单{wo_id}"
            )

    # ========================================================================
    # P2-11: 安全库存独立补货触发
    # ========================================================================

    def warehouse_balance_transfer_process(self):
        """Task11: 每12小时检查是否需要仓库间调拨（A仓有院量、B仓缺货）"""
        yield self.env.timeout(12.0)  # 首次检查延12小时后
        while True:
            for material_id, inv in self.inventory_state.items():
                total = inv.get("total", 0)
                available = inv.get("available", 0)
                # 如果总库存足够但可用量很低，可能存在仓库派别不均衡
                mat_info = self.materials.get(material_id, {})
                safety_stock = mat_info.get("safety_stock_level", 0)
                if total > safety_stock * 2 and available < safety_stock * 0.5 and total - available > safety_stock:
                    # A仓有院量但B仓缺货：模拟仓库间调拨
                    transfer_qty = min(safety_stock, total - available - safety_stock)
                    if transfer_qty > 0:
                        transfer_id = f"MT-WH-{self.next_id('MT')}"
                        self.db.insert("material_transfer", {
                            "transfer_id": transfer_id,
                            "material_id": material_id,
                            "from_work_order_id": None,
                            "to_work_order_id": None,
                            "from_location": "备用仓",
                            "to_location": "生产仓",
                            "quantity": round(transfer_qty, 2),
                            "transfer_reason": "仓库间平衡调拨",
                            "trigger_source": "仓库间平衡",
                            "requested_time": self.sim_time_to_datetime(self.env.now),
                            "executed_time": self.sim_time_to_datetime(self.env.now),
                            "status": "已执行",
                            "note": f"自动平衡调拨{transfer_qty:.1f}"
                        })
                        # 调拨后可用量增加
                        inv["available"] = inv.get("available", 0) + transfer_qty
                        print(f"  [仓库间调拨] {material_id} 调拨{transfer_qty:.1f}，备用仓→生产仓")
            yield self.env.timeout(12.0)

    def safety_stock_monitor(self):
        """每4小时检查一次安全库存，低于再订货点时自动补货"""
        check_interval = self.config.get("safety_stock_check_interval_hours", 4)
        while True:
            yield self.env.timeout(check_interval)

            for material_id, mat_info in self.materials.items():
                if material_id in self.safety_stock_po_pending:
                    continue  # 已有在途补货，跳过

                inv = self.inventory_state.get(material_id)
                if not inv:
                    continue

                reorder_point = mat_info.get("reorder_point", 0)
                safety_stock = mat_info.get("safety_stock_level", 0)

                # 总可用（含在途）低于再订货点时触发
                effective_available = inv["available"] + inv["in_transit"]
                if effective_available < reorder_point:
                    sms = self.supplier_materials.get(material_id, [])
                    preferred = [s for s in sms if s.get("is_preferred")]
                    supplier = preferred[0] if preferred else (sms[0] if sms else None)

                    if not supplier:
                        continue

                    # P2-13: 使用EOQ计算补货量
                    eoq = mat_info.get("eoq", 0.0)
                    min_order = supplier.get("min_order_qty", safety_stock)
                    max_order = supplier.get("max_order_qty", 0.0)
                    if eoq > 0:
                        po_qty = max(eoq, min_order)
                    else:
                        po_qty = max(safety_stock * 2, min_order)
                    
                    # 限制最大订购量
                    if max_order > 0 and po_qty > max_order:
                        po_qty = max_order

                    # P0-3: 供应商可靠性扰动
                    lead_mean = supplier.get("lead_time_days", 3)
                    lead_std = supplier.get("lead_time_stddev_days", 0.5)
                    actual_lead = normal_sample(lead_mean, lead_std, min_val=1.0)

                    po_id = self.next_id("PO")
                    now_dt = self.sim_time_to_datetime(self.env.now)
                    expected_delivery = now_dt + timedelta(days=actual_lead)

                    po_data = {
                        "po_id": po_id,
                        "supplier_id": supplier["supplier_id"],
                        "order_date": now_dt,
                        "expected_delivery_date": expected_delivery,
                        "status": "已创建",
                        "total_amount": po_qty * supplier.get("unit_price", 1.0),
                        "note": f"安全库存补货（再订货点触发），可用={effective_available:.0f}<{reorder_point}"
                    }
                    self.db.insert("purchase_order", po_data)

                    line_data = {
                        "line_id": f"POL-{po_id}-001",
                        "po_id": po_id,
                        "material_id": material_id,
                        "quantity": po_qty,
                        "status": "待收货",
                        "unit_price": supplier.get("unit_price", 1.0),
                        "related_work_order_id": None,
                        "related_wom_id": None
                    }
                    self.db.insert("purchase_order_line", line_data)

                    inv["in_transit"] += po_qty
                    self.safety_stock_po_pending.add(material_id)

                    self.env.process(self.purchase_arrival_event(po_id, material_id, po_qty, actual_lead))

                    print(f"  [安全库存] {material_id}: 触发补货PO={po_id}, 数量={po_qty:.0f}, "
                          f"可用={effective_available:.1f}<再订货点{reorder_point}")

    # ========================================================================
    # 核心仿真事件：排程（P1-8: 升级版）
    # ========================================================================

    def daily_scheduler(self):
        """每天运行排程（增强版：每4小时检查一次，配合实时排程）"""
        while True:
            yield self.wait_until_next_work_start()
            yield self.env.timeout(1.0)  # 9:00 排程

            print(f"[Day {self.get_sim_day()} 09:00] 运行排程...")
            today = self.sim_time_to_datetime(self.env.now).date()

            # Task4: 工作日历驱动 - 周日不排程
            if today.weekday() == 6:  # 0=周一, 6=周日
                print(f"  [日历] {today} 为周日，跳过排程")
                yield self.env.timeout(23.0)
                continue
            
            # 【优化5】前瞻排程：预测未来瓶颈（每天一次）
            lookahead_enabled = self.config.get("lookahead_enabled", True)
            if lookahead_enabled:
                lookahead_result = self.look_ahead_schedule()
                
                # 输出预测结果（只输出有风险的）
                material_shortages = lookahead_result.get("material_shortages", {})
                at_risk_orders = lookahead_result.get("at_risk_orders", [])
                
                if material_shortages:
                    print(f"  [前瞻预警] 发现{len(material_shortages)}种物料缺口")
                    for mat_id, info in list(material_shortages.items())[:3]:  # 只显示前3个
                        print(f"    - {mat_id}: 缺口{info['total_gap']:.0f}，影响{len(info['affected_wos'])}个工单")
                
                if at_risk_orders:
                    high_risk = [o for o in at_risk_orders if o["risk_level"] == "HIGH"]
                    if high_risk:
                        print(f"  [交期预警] {len(high_risk)}个订单高风险延期")
                        for order in high_risk[:3]:  # 只显示前3个
                            print(f"    - {order['wo_id']}: 预计延期{order['delay_hours']:.1f}小时")

            # P0-1: 只获取前驱工序已完成的待开工工序
            ready_ops = self.db.query_ready_operations_with_precedence()

            if not ready_ops:
                # 无可排工序时，4小时后再检查（而不是23小时）
                yield self.env.timeout(4.0)
                continue

            # P1-8: 按关键比（Critical Ratio）+优先级排序（使用动态平均时间）
            now_sim = self.env.now
            scored_ops = []
            for op in ready_ops:
                product_id = op.get("product_id")
                remaining_ops = op.get("remaining_op_count", 1)
                
                # 【优化6】使用产品实际平均时间，而不是硬编码4.0
                avg_op_time = self.calculate_avg_op_time(product_id)
                
                # 计算剩余工期预估
                estimated_remaining_time = remaining_ops * avg_op_time
                
                # 加上排队时间
                queue_time = self.config.get("queue_time_hours", 0.5)
                estimated_remaining_time += remaining_ops * queue_time
                
                # 关键比 = 剩余时间 / 剩余工期预估（越小越紧急）
                due_sim = self.datetime_to_sim_hours(op.get("planned_end"))
                remaining_time = max(1.0, due_sim - now_sim)
                critical_ratio = remaining_time / max(estimated_remaining_time, 0.1)
                
                priority = op.get("priority", 5)
                scored_ops.append((critical_ratio, priority, op))

            # 先按关键比升序（越小越紧急），再按优先级升序（1最紧急）
            scored_ops.sort(key=lambda x: (x[0], x[1]))

            # P1-8: 按工作中心分组，尝试合并同产品批次（减少换线）
            wc_ops_map = defaultdict(list)
            for _, _, op in scored_ops:
                route_id = self.get_route_for_product(op.get("product_id"))
                steps = self.route_steps.get(route_id, [])
                step = next((s for s in steps if s["step_id"] == op["step_id"]), None)
                if step:
                    wc_id = step.get("machine_type_required")
                    wc_ops_map[wc_id].append(op)

            # 对每个工作中心：相同产品的工序合并排在一起
            for wc_id, ops in wc_ops_map.items():
                self.schedule_operations_for_wc(wc_id, ops)

            # T4: 写入每日产能快照（只在09:00的排程中写入）
            self._write_daily_schedule_snapshot(today)

            # 4小时后再检查一次（配合实时排程，提高响应速度）
            yield self.env.timeout(4.0)

    def _write_daily_schedule_snapshot(self, today):
        """T4: 写入当日产能利用率快照到Schedule表"""
        # 计算总负荷小时（当日已排程任务）
        total_load = sum(
            max(0, st.get("next_available_time", self.env.now) - self.env.now)
            for st in self.machine_state.values()
        )
        num_machines = len(self.machine_state)
        utilization = min(1.0, total_load / max(1, num_machines * 12.0))  # 以白班12小时为基准

        # 找出礼食机台（负荷最重）
        bottleneck_id = max(
            self.machine_state,
            key=lambda mid: self.machine_state[mid].get("next_available_time", 0),
            default=None
        )

        # 统计活跃和已完成工单数
        total_orders = sum(
            1 for s in self.work_order_state.values()
            if s.get("status") not in ("\u5df2\u5b8c\u6210", "\u53d6\u6d88")
        )
        completed_orders = sum(
            1 for s in self.work_order_state.values()
            if s.get("status") == "\u5df2\u5b8c\u6210"
        )

        schedule_id = f"SCH-{self.get_sim_day():03d}"
        # 查找瓶颈机台所属工作中心
        bottleneck_wc_id = None
        if bottleneck_id:
            m_info = self.machines.get(bottleneck_id, {})
            bottleneck_wc_id = m_info.get("work_center_id")
        self.db.insert("schedule", {
            "schedule_id": schedule_id,
            "schedule_date": today,
            "total_load_hours": round(total_load, 2),
            "utilization_rate": round(utilization, 4),
            "bottleneck_machine_id": bottleneck_id,
            "bottleneck_work_center_id": bottleneck_wc_id,
            "total_orders": len(self.work_order_state),
            "completed_orders": completed_orders,
            "created_at": self.sim_time_to_datetime(self.env.now)
        })

    def schedule_operations_for_wc(self, wc_id: str, ops: List[dict]):
        """P1-8: 对单个工作中心的工序进行Setup成本优化排程"""
        # 找出该工作中心所有可用机台
        candidate_machines = [m for m in self.machines.values()
                               if m.get("work_center_id") == wc_id
                               and m["machine_id"] not in self.machines_under_maintenance]

        if not candidate_machines:
            return

        for op in ops:
            self.schedule_operation(op, candidate_machines)

    def skip_sunday(self, sim_hours: float) -> float:
        """如果一个仿真时刱08指向周日，则推迟到周一08:00（工作日历约束）"""
        dt = self.sim_time_to_datetime(sim_hours)
        if dt.weekday() == 6:  # 周日
            # 找到周一的 08:00
            days_to_monday = 1
            monday_8am = dt.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=days_to_monday)
            return self.datetime_to_sim_hours(monday_8am)
        return sim_hours

    def schedule_operation(self, op: dict, candidate_machines: List[dict] = None):
        """P1-8: 为单个工序排程（Setup成本最小化）"""
        wo_op_id = op["wo_op_id"]
        wo_id = op["work_order_id"]
        step_id = op["step_id"]
        product_id = op.get("product_id") or self.work_order_state.get(wo_id, {}).get("product_id")
        qty = op.get("required_input_qty", 0)

        if not product_id:
            return

        route_id = self.get_route_for_product(product_id)
        steps = self.route_steps.get(route_id, [])
        step = next((s for s in steps if s["step_id"] == step_id), None)
        if not step:
            return

        wc_id = step.get("machine_type_required")

        if candidate_machines is None:
            candidate_machines = [m for m in self.machines.values()
                                   if m.get("work_center_id") == wc_id
                                   and m["machine_id"] not in self.machines_under_maintenance]
        if not candidate_machines:
            return

        setup_weight = self.config.get("setup_cost_weight", 2.0)
        best_machine = None
        best_score = float('inf')

        for machine in candidate_machines:
            mid = machine["machine_id"]

            # P2-10: 计算加工时间（含班次效率）
            # Lot批量加工：std_time已经按批量调整过（÷25），直接使用，不需要乘以num_lots
            std_time = step["standard_time_hours"]
            raw_start = max(self.env.now, self.machine_state[mid]["next_available_time"])
            start_time = self.skip_sunday(raw_start)  # Task4: 工作日历 - 跳过周日
            efficiency = self.get_machine_efficiency(mid, product_id, at_sim_hours=start_time)
            process_time = std_time / efficiency  # 直接使用批量调整后的时间

            # P1-8: 换线时间（Setup成本）
            last_product = self.machine_last_product.get(mid)
            setup_min = self.get_setup_time(mid, last_product, product_id)
            setup_time = setup_min / 60.0  # 转小时
            
            # Lot批量加工：同Setup Group连续生产免换线
            if self.config.get("setup_skip_same_group", False):
                current_setup_group = self.work_order_state.get(wo_id, {}).get("setup_group")
                last_wo_id = self.machine_state[mid].get("current_wo")
                if last_wo_id:
                    last_setup_group = self.work_order_state.get(last_wo_id, {}).get("setup_group")
                    if current_setup_group and current_setup_group == last_setup_group:
                        setup_time = 0  # 同组免换线

            # P1-5: 工序间等待/转运时间（在上道工序完成后需要等待）
            wait_time = step.get("wait_time_hours", 0.0)
            transport_time = step.get("transport_time_hours", 0.0)

            # P1-8: 综合评分 = 完工时间 + 换线成本惩罚
            end_time = start_time + setup_time + process_time + wait_time + transport_time
            # 换线成本惩罚：用setup_cost_weight倍的换线时间来惩罚
            score = end_time + setup_time * (setup_weight - 1.0)

            if score < best_score:
                best_score = score
                best_machine = machine
                best_end_time = end_time
                best_setup_time = setup_time
                best_process_time = process_time
                best_wait = wait_time + transport_time
                best_start = start_time

        if best_machine:
            mid = best_machine["machine_id"]

            # P1-6: 取工单的第一个Lot来关联（按顺序）
            lot_id = self._get_lot_for_op(wo_id, step_id)

            task_id = self.next_id("PT")
            _is_night = self.is_night_shift(best_start)
            task_data = {
                "task_id": task_id,
                "wo_op_id": wo_op_id,
                "work_order_id": wo_id,
                "machine_id": mid,
                "lot_id": lot_id,   # P1-6
                "planned_start_time": self.sim_time_to_datetime(best_start),
                "planned_end_time": self.sim_time_to_datetime(best_end_time),
                "planned_quantity": qty,
                "wait_time_actual": best_wait,  # P1-5
                "shift_id": "SHIFT-NIGHT" if _is_night else "SHIFT-DAY",  # P2-10: 关联班次
                "is_night_shift": _is_night,  # P2-10
                "status": "已排程"
            }
            self.db.insert("production_task", task_data)

            # 更新机台状态
            self.machine_state[mid]["next_available_time"] = best_end_time
            self.machine_state[mid]["status"] = "已占用"
            self.machine_state[mid]["current_product"] = product_id
            self.machine_state[mid]["current_wo"] = wo_id
            self.machine_state[mid]["current_task"] = task_id

            # 更新工单工序
            self.db.update("work_order_operation", {"wo_op_id": wo_op_id}, {
                "assigned_machine_id": mid,
                "status": "已排程",
                "planned_start": self.sim_time_to_datetime(best_start),
                "planned_end": self.sim_time_to_datetime(best_end_time)
            })

            # 启动生产执行事件
            self.env.process(self.execute_production_task(
                task_id, mid, wo_id, wo_op_id, product_id, qty,
                best_setup_time, best_process_time, step, lot_id
            ))

    def _get_lot_for_op(self, wo_id: str, step_id: str) -> Optional[str]:
        """P1-6: 获取该工单当前工序对应的Lot ID"""
        for lot_id, state in self.wip_lot_state.items():
            if state["wo_id"] == wo_id and state["status"] in ("排队中", "进行中"):
                return lot_id
        return None

    # ========================================================================
    # 核心仿真事件：生产执行
    # ========================================================================

    def execute_production_task(self, task_id: str, machine_id: str, wo_id: str,
                                wo_op_id: str, product_id: str, qty: float,
                                setup_time: float, process_time: float,
                                step: dict, lot_id: str = None):
        """执行生产任务（含所有P0-P2改进）"""
        now = self.env.now
        task = self.db.get_production_task(task_id)
        if task:
            planned_start = self.datetime_to_sim_hours(task["planned_start_time"])
            if planned_start > now:
                yield self.env.timeout(planned_start - now)

        # P1-5: 工序间等待/转运时间（在开始加工前等待）
        wait_before = step.get("transport_time_hours", 0.0)
        if wait_before > 0:
            yield self.env.timeout(wait_before)

        # Task2: 工序开始时，若工单尚未开工则记录实际开工时间
        wo_state = self.work_order_state.get(wo_id, {})
        if wo_state.get("status") in ("已下达", "已计划", "进行中"):
            wo_db = self.db.get("work_order", {"work_order_id": wo_id})
            if wo_db and not wo_db.get("actual_start_date"):
                self.db.update("work_order", {"work_order_id": wo_id}, {
                    "actual_start_date": self.sim_time_to_datetime(self.env.now)
                })
                if wo_id in self.work_order_state:
                    self.work_order_state[wo_id]["actual_started"] = True

        # 机台Setup
        if setup_time > 0:
            self.log_machine_status(machine_id, "换线", product_id, wo_id, task_id)
            yield self.env.timeout(setup_time)
            self.machine_state[machine_id]["total_setup_hours"] += setup_time

            # Task8: 换线首件检验IPQC（换线后第一件必须通过首件检验才能正式开工）
            yield from self._ipqc_first_article(machine_id, wo_op_id, wo_id, product_id)

        # P2-10: 开始加工时检查是否夜班
        is_night = self.is_night_shift()
        actual_start_time = self.env.now

        # T1: 工序开始时执行生产领料（预留→消耗）
        self.consume_materials_for_operation(wo_op_id, wo_id)

        self.log_machine_status(machine_id, "运行", product_id, wo_id, task_id)
        self.machine_state[machine_id]["status"] = "运行中"

        # 更新Lot状态
        if lot_id and lot_id in self.wip_lot_state:
            self.wip_lot_state[lot_id]["status"] = "进行中"
            self.db.update("wip_lot", {"lot_id": lot_id}, {
                "lot_status": "加工中",
                "processing_start_time": self.sim_time_to_datetime(actual_start_time),
                "current_machine_id": machine_id,
                "current_step_id": step["step_id"]
            })

        # 更新工单工序
        self.db.update("work_order_operation", {"wo_op_id": wo_op_id}, {
            "actual_start": self.sim_time_to_datetime(actual_start_time),
            "status": "进行中"
        })

        # Lot批量加工：计算实际加工时间
        # 注：PT中的工序时间已经按批量调整过（÷25或÷并行度），直接使用即可
        actual_process_time = process_time

        # 加工中...（P2-10: 夜班效率已在排程时计入process_time）
        yield self.env.timeout(actual_process_time)

        # 加工完成
        actual_end_time = self.env.now

        # P0-2: 良率损耗计算（每道工序独立扰动）
        base_yield = self.machine_capabilities.get((machine_id, product_id), {}).get("yield_rate", 0.98)
        standard_yield = step.get("yield_rate_standard", 0.98)
        # 综合良率 = 机台良率 × 工序标准良率 × ±1%随机扰动
        actual_yield = min(1.0, base_yield * random.uniform(0.99, 1.01))
        actual_qty = qty * actual_yield
        scrap_qty = qty - actual_qty

        # P2-10: 实际效率（含夜班折减）
        base_efficiency = self.machine_capabilities.get((machine_id, product_id), {}).get("efficiency_factor", 1.0)
        shift_factor = self.get_shift_efficiency(actual_start_time)
        actual_efficiency = base_efficiency * shift_factor * random.uniform(0.97, 1.03)

        # P2-9: 记录到每日OEE统计缓存
        self.machine_daily_stats[machine_id][product_id].append(
            (actual_efficiency, actual_yield, process_time)
        )

        # 更新生产任务
        self.db.update("production_task", {"task_id": task_id}, {
            "actual_start_time": self.sim_time_to_datetime(actual_start_time),
            "actual_end_time": self.sim_time_to_datetime(actual_end_time),
            "actual_quantity": round(actual_qty, 4),
            "scrap_quantity": round(scrap_qty, 4),
            "actual_efficiency": round(actual_efficiency, 4),
            "actual_yield": round(actual_yield, 4),
            "setup_time_actual": setup_time,
            "is_night_shift": is_night,
            "status": "已完成"
        })

        # P0-2: 更新下一道工序的required_input_qty（良率传递）
        self.update_next_op_input_qty(wo_id, wo_op_id, actual_qty, step)

        # 更新机台状态
        self.machine_state[machine_id]["status"] = "空闲"
        self.machine_state[machine_id]["current_product"] = None
        self.machine_state[machine_id]["current_wo"] = None
        self.machine_state[machine_id]["current_task"] = None
        self.machine_state[machine_id]["total_run_hours"] += process_time
        self.machine_last_product[machine_id] = product_id

        self.log_machine_status(machine_id, "空闲", None, None, None)

        # P1-5: 工序完成后的强制等待时间（如固化）
        wait_after = step.get("wait_time_hours", 0.0)
        is_critical_step = step.get("is_critical", False)
        if wait_after > 0:
            # 异步等待，不占用机台
            self.env.process(self._post_operation_wait(
                wo_op_id, lot_id, wo_id, actual_qty, scrap_qty, actual_end_time, wait_after,
                machine_id=machine_id, step_is_critical=is_critical_step
            ))
        else:
            # 直接完成
            self._finalize_operation(wo_op_id, lot_id, wo_id, actual_qty, scrap_qty,
                                     machine_id=machine_id, step_is_critical=is_critical_step)

    def _post_operation_wait(self, wo_op_id: str, lot_id: str, wo_id: str,
                             actual_qty: float, scrap_qty: float, end_time: float, wait_hours: float,
                             machine_id: str = None, step_is_critical: bool = False):
        """P1-5: 工序完成后的强制等待（机台已释放，但Lot处于等待固化状态）"""
        # 更新Lot为等待状态
        if lot_id and lot_id in self.wip_lot_state:
            self.db.update("wip_lot", {"lot_id": lot_id}, {
                "lot_status": "等待中",
                "hold_reason": f"工序后强制等待{wait_hours:.1f}小时"
            })

        yield self.env.timeout(wait_hours)

        # 等待结束，完成工序
        self._finalize_operation(wo_op_id, lot_id, wo_id, actual_qty, scrap_qty,
                                 machine_id=machine_id, step_is_critical=step_is_critical)

    def _finalize_operation(self, wo_op_id: str, lot_id: str, wo_id: str,
                            actual_qty: float, scrap_qty: float, machine_id: str = None,
                            step_is_critical: bool = False):
        """完成工序，更新相关状态"""
        # T5: 关键工序触发质检
        if step_is_critical and (actual_qty + scrap_qty) > 0:
            actual_scrap = self.trigger_quality_inspection(
                wo_op_id, lot_id, machine_id, actual_qty, scrap_qty
            )
            # QC可能改变最终报废数量（若判定返工则报废数归零）
            scrap_qty = actual_scrap
            actual_qty = actual_qty  # pass_qty不变

        self.db.update("work_order_operation", {"wo_op_id": wo_op_id}, {
            "actual_end": self.sim_time_to_datetime(self.env.now),
            "completed_output_qty": round(actual_qty, 4),
            "scrapped_qty": round(scrap_qty, 4),
            "status": "已完成"
        })

        # P0-2: 更新WIPLot实际数量并推进到下一工序
        if lot_id and lot_id in self.wip_lot_state:
            self.wip_lot_state[lot_id]["current_qty"] = actual_qty
            self.wip_lot_state[lot_id]["status"] = "排队中"

        self.update_work_order_status(wo_id)
        self.advance_wip_lots(wo_id, lot_id, actual_qty)
        
        # 【新增】事件驱动实时排程：工序完成后立即检查并排程后续工序
        self.env.process(self.realtime_schedule_after_completion(wo_op_id, wo_id))

    def update_next_op_input_qty(self, wo_id: str, current_wo_op_id: str, actual_output: float, current_step: dict):
        """P0-2: 将当前工序的实际产出数量更新到下一工序的投入数量"""
        seq_no = current_step.get("sequence_no", 10)
        product_id = self.work_order_state.get(wo_id, {}).get("product_id")
        if not product_id:
            return

        route_id = self.get_route_for_product(product_id)
        steps = sorted(self.route_steps.get(route_id, []), key=lambda x: x["sequence_no"])

        # 找到下一道工序
        next_step = None
        for step in steps:
            if step["sequence_no"] > seq_no:
                next_step = step
                break

        if not next_step:
            return  # 已是最后一道工序

        next_wo_op_id = f"{wo_id}-OP{next_step['sequence_no']:02d}"
        self.db.update("work_order_operation", {"wo_op_id": next_wo_op_id}, {
            "required_input_qty": round(actual_output, 4)
        })

    def update_work_order_status(self, wo_id: str):
        """更新工单整体状态"""
        ops = self.db.get_work_order_operations(wo_id)
        if not ops:
            return

        total_ops = len(ops)
        completed_ops = sum(1 for op in ops if op.get("status") == "已完成")

        if completed_ops == 0:
            new_status = "已下达"
        elif completed_ops < total_ops:
            new_status = "生产中"
        else:
            new_status = "已完成"
            # 获取最终工序产出数量
            last_op = max(ops, key=lambda x: x.get("sequence_no", 0))
            completed_qty = last_op.get("completed_output_qty", 0)
            scrap_qty = sum(op.get("scrapped_qty", 0) for op in ops)

            self.db.update("work_order", {"work_order_id": wo_id}, {
                "actual_completion_date": self.sim_time_to_datetime(self.env.now),
                "completed_quantity": round(completed_qty, 4),
                "scrapped_quantity": round(scrap_qty, 4),
                "status": new_status
            })
            # T2: 完工入库 + T3: 触发发货
            self.complete_work_order_and_inbound(wo_id, completed_qty)
            return

        wo = self.db.get_work_order(wo_id)
        if wo and self.env.now > self.datetime_to_sim_hours(wo["planned_completion_date"]):
            if new_status != "已完成":
                new_status = "延期"

        self.db.update("work_order", {"work_order_id": wo_id}, {"status": new_status})
    
    def realtime_schedule_after_completion(self, completed_wo_op_id: str, wo_id: str):
        """【优化4】事件驱动实时排程：工序完成后立即检查并排程后续工序（带防抖动）"""
        now = self.env.now
        
        # 1. 防抖动检查：冷却期内不重复排程
        last_schedule = self.schedule_cooldown.get(wo_id, 0)
        if now - last_schedule < self.schedule_cooldown_hours:
            return  # 冷却期内，跳过排程
        
        # 2. 更新冷却时间
        self.schedule_cooldown[wo_id] = now
        
        # 3. 等待一小段时间，确保数据库更新完成
        yield self.env.timeout(0.1)
        
        # 查询因当前工序完成而变为ready的后续工序
        ready_ops = self.db.query_ready_operations_with_precedence()
        
        if not ready_ops:
            return
        
        # 只排程与当前工单相关的后续工序（避免全局排程开销）
        current_product = self.work_order_state.get(wo_id, {}).get("product_id")
        if not current_product:
            return
        
        # 筛选出当前工单或其他工单中变为ready的工序
        relevant_ops = []
        for op in ready_ops:
            # 检查是否是当前工单的后续工序，或者其他工单的工序也变为ready了
            if op.get("work_order_id") == wo_id or op.get("product_id") == current_product:
                relevant_ops.append(op)
        
        if not relevant_ops:
            return
        
        # 按关键比排序（使用动态平均时间）
        now_sim = self.env.now
        scored_ops = []
        for op in relevant_ops:
            product_id = op.get("product_id")
            remaining_ops = op.get("remaining_op_count", 1)
            
            # 【优化6】使用产品实际平均时间，而不是硬编码4.0
            avg_op_time = self.calculate_avg_op_time(product_id)
            
            # 计算剩余工期预估
            estimated_remaining_time = remaining_ops * avg_op_time
            
            # 加上排队时间
            queue_time = self.config.get("queue_time_hours", 0.5)
            estimated_remaining_time += remaining_ops * queue_time
            
            # 计算关键比（剩余时间/剩余工期）
            due_sim = self.datetime_to_sim_hours(op.get("planned_end"))
            remaining_time = max(1.0, due_sim - now_sim)
            critical_ratio = remaining_time / max(estimated_remaining_time, 0.1)
            
            priority = op.get("priority", 5)
            scored_ops.append((critical_ratio, priority, op))
        
        scored_ops.sort(key=lambda x: (x[0], x[1]))
        
        # 按工作中心分组排程
        wc_ops_map = defaultdict(list)
        for _, _, op in scored_ops:
            route_id = self.get_route_for_product(op.get("product_id"))
            steps = self.route_steps.get(route_id, [])
            step = next((s for s in steps if s["step_id"] == op["step_id"]), None)
            if step:
                wc_id = step.get("machine_type_required")
                wc_ops_map[wc_id].append(op)
        
        # 对每个工作中心进行排程
        scheduled_count = 0
        for wc_id, ops in wc_ops_map.items():
            # 找出该工作中心所有可用机台
            candidate_machines = [m for m in self.machines.values()
                                   if m.get("work_center_id") == wc_id
                                   and m["machine_id"] not in self.machines_under_maintenance]
            
            if not candidate_machines:
                continue
            
            for op in ops:
                self.schedule_operation(op, candidate_machines)
                scheduled_count += 1
        
        if scheduled_count > 0:
            sim_day = self.get_sim_day()
            sim_time = self.sim_time_to_datetime(self.env.now)
            print(f"  [实时排程] Day {sim_day} {sim_time.strftime('%H:%M')}: "
                  f"工序{completed_wo_op_id}完成，立即排程{scheduled_count}个后续工序")

    def advance_wip_lots(self, wo_id: str, current_lot_id: str, actual_qty: float):
        """P0-2: 推进WIP Lot到下一工序（携带实际产出数量，含流转优化）"""
        product_id = self.work_order_state.get(wo_id, {}).get("product_id")
        if not product_id:
            return

        if current_lot_id and current_lot_id in self.wip_lot_state:
            current_idx = self.wip_lot_state[current_lot_id]["current_step_idx"]
            route_id = self.get_route_for_product(product_id)
            steps = sorted(self.route_steps.get(route_id, []), key=lambda x: x["sequence_no"])

            if current_idx + 1 < len(steps):
                next_step = steps[current_idx + 1]
                self.wip_lot_state[current_lot_id]["current_step_idx"] = current_idx + 1
                self.wip_lot_state[current_lot_id]["status"] = "排队中"
                self.wip_lot_state[current_lot_id]["current_qty"] = actual_qty
                
                # Lot批量加工：工序流转优化（减少辅助工序排队时间）
                flow_merge_enabled = self.config.get("flow_merge_enabled", False)
                if flow_merge_enabled:
                    next_step_code = self.step_code_map.get(next_step["step_id"], "UNKNOWN")
                    # 辅助工序免排队：直接合并到下一道主工序
                    if next_step_code in ["TRANS", "WAIT", "CLEAN"]:
                        # 减少等待/转运时间（直接跳过）
                        next_step = next_step.copy()  # 避免修改原始数据
                        next_step["wait_time_hours"] = 0.0
                        next_step["transport_time_hours"] = 0.0

                self.db.update("wip_lot", {"lot_id": current_lot_id}, {
                    "current_step_id": next_step["step_id"],
                    "lot_status": "排队中",
                    "actual_quantity": round(actual_qty, 4),
                    "queue_start_time": self.sim_time_to_datetime(self.env.now),
                    "current_machine_id": None
                })
            else:
                # 最后一道工序完成
                self.wip_lot_state[current_lot_id]["status"] = "已完成"
                self.db.update("wip_lot", {"lot_id": current_lot_id}, {
                    "lot_status": "已完成",
                    "actual_quantity": round(actual_qty, 4),
                    "completed_time": self.sim_time_to_datetime(self.env.now),
                    "current_machine_id": None
                })

    def consume_materials_for_operation(self, wo_op_id: str, wo_id: str):
        """工序开工时，将预留物料转为实际消耗（T1+T7: 含辅料）"""
        woms = self.db.get_woms_for_op(wo_op_id)
        for wom in woms:
            if wom.get('allocated_quantity', 0) > 0 and wom.get('consumed_quantity', 0) == 0:
                material_id = wom['material_id']
                qty = wom['allocated_quantity']

                # 更新WOM消耗量
                self.db.update("work_order_material", {"wom_id": wom['wom_id']}, {
                    "consumed_quantity": qty,
                    "status": "已消耗"
                })

                # 库存：使用"生产消耗"类型，reserved减少，total减少（真正出库）
                # 注：不手动操作 inv，由 record_inventory_transaction 统一处理状态
                self.record_inventory_transaction(
                    material_id, "生产消耗", qty,
                    related_doc_type="WorkOrderOperation", related_doc_id=wo_op_id,
                    from_wo=wo_id,
                    description=f"工序{wo_op_id}实际领料消耗"
                )

    # ========================================================================
    # Task 2+3: 成品完工入库 + 客户发货
    # ========================================================================

    def complete_work_order_and_inbound(self, wo_id: str, completed_qty: float):
        """工单完工：成品入库将成品写入成品库存"""
        product_id = self.work_order_state.get(wo_id, {}).get("product_id")
        if not product_id or completed_qty <= 0:
            return

        # 更新内存中成品库存状态
        fg_state = self.fg_inventory_state.get(product_id)
        if fg_state:
            fg_state["total"] += completed_qty
            fg_state["available"] += completed_qty
        else:
            self.fg_inventory_state[product_id] = {
                "total": completed_qty,
                "available": completed_qty,
                "reserved": 0.0,
                "shipped": 0.0
            }

        # 写入成品库存表
        fg_inv_id = f"FGI-{product_id}"
        existing = self.db.get_finished_goods_inventory(product_id)
        if existing:
            self.db.update("finished_goods_inventory", {"fg_inv_id": fg_inv_id}, {
                "total_quantity": lambda col: (col or 0) + completed_qty,
                "available_quantity": lambda col: (col or 0) + completed_qty,
                "last_updated": self.sim_time_to_datetime(self.env.now)
            })
        else:
            self.db.insert("finished_goods_inventory", {
                "fg_inv_id": fg_inv_id,
                "product_id": product_id,
                "location": "成品仓",
                "total_quantity": completed_qty,
                "available_quantity": completed_qty,
                "reserved_quantity": 0.0,
                "shipped_quantity": 0.0,
                "last_updated": self.sim_time_to_datetime(self.env.now)
            })

        # 注：成品库存独立记录到 finished_goods_inventory 表
        # product_id 不在 material 表中，不写入 inventory_transaction 避免外键断链
        print(f"  [完工入库] 工单{wo_id} -> 成品{product_id} +{completed_qty:.1f} 入成品仓")
        
        # 更新工单的实际产出量和良率统计
        wo_info = self.work_order_state.get(wo_id, {})
        planned_qty = wo_info.get("quantity", 0)  # 计划投入量
        order_qty = wo_info.get("order_quantity", planned_qty)  # 订单数量
        
        # 更新工单的completed_quantity
        self.db.update("work_order", {"work_order_id": wo_id}, {
            "completed_quantity": completed_qty,
            "status": "已完成"
        })
        
        # 计算良率统计信息（用于成本核算）
        actual_yield_rate = completed_qty / planned_qty if planned_qty > 0 else 0
        expected_yield_rate = order_qty / planned_qty if planned_qty > 0 else 0
        
        print(f"  [良率统计] 工单{wo_id}: 投入{planned_qty:.1f} → 产出{completed_qty:.1f} (实际{actual_yield_rate:.2%}, 预期{expected_yield_rate:.2%})")
        
        # 判断是否为重工工单
        wo_info = self.work_order_state.get(wo_id, {})
        is_rework_wo = wo_info.get("work_order_type") == "重工"
        original_order_id = wo_info.get("customer_order_id")
        
        if is_rework_wo and original_order_id:
            # 重工工单完成：需要FQC复检
            print(f"  [重工完成] {wo_id} 完成，等待FQC复检")
            self.rework_fqc_and_reship(original_order_id, product_id, completed_qty, wo_id)
        else:
            # 正常工单完成：直接触发发货
            self.try_ship_customer_order(wo_id, product_id, completed_qty)
    
    def rework_fqc_and_reship(self, order_id: str, product_id: str, rework_qty: float, rework_wo_id: str):
        """
        重工完成后FQC复检并重新发货
        
        流程：
        1. FQC复检（重工后必须再次检验）
        2. 合格 -> 触发发货 -> 更新订单状态为"已发货"
        3. 不合格 -> 报废 -> 更新订单状态为"已取消"
        """
        import random
        
        print(f"  [重工FQC] 开始复检订单{order_id}，数量{rework_qty:.1f}")
        
        # 1. FQC复检
        fqc_passed = self._run_fqc(order_id, product_id, rework_qty)
        
        if not fqc_passed:
            # 复检仍不合格：报废处理
            print(f"  [重工失败] 订单{order_id} FQC复检仍不合格，报废{rework_qty:.1f}")
            
            # 从成品库存中移除（报废）
            fg_state = self.fg_inventory_state.get(product_id, {})
            fg_state["total"] = max(0, fg_state.get("total", 0) - rework_qty)
            fg_state["available"] = max(0, fg_state.get("available", 0) - rework_qty)
            
            # 更新数据库
            fg_inv_id = f"FGI-{product_id}"
            self.db.update("finished_goods_inventory", {"fg_inv_id": fg_inv_id}, {
                "total_quantity": lambda col: max(0, (col or 0) - rework_qty),
                "available_quantity": lambda col: max(0, (col or 0) - rework_qty),
                "last_updated": self.sim_time_to_datetime(self.env.now)
            })
            
            # 更新重工工单状态
            self.db.update("work_order", {"work_order_id": rework_wo_id}, {
                "status": "已取消",
                "note": "重工后FQC复检仍不合格，报废处理"
            })
            
            # 更新原订单状态
            self.db.update("customer_order", {"order_id": order_id}, {
                "status": "已取消",
                "note": "重工失败，订单取消"
            })
            
            return
        
        # 2. 复检合格：触发发货流程
        print(f"  [重工成功] 订单{order_id} FQC复检合格，触发发货")
        
        # 更新重工工单状态
        self.db.update("work_order", {"work_order_id": rework_wo_id}, {
            "status": "已完成",
            "note": f"重工完成，FQC复检合格，数量{rework_qty:.1f}"
        })
        
        # 更新原订单状态为"重工完成"
        self.db.update("customer_order", {"order_id": order_id}, {
            "status": "重工完成",
            "note": f"重工完成，等待发货，数量{rework_qty:.1f}"
        })
        
        # 3. 重新触发发货（使用重工工单ID）
        self.try_ship_customer_order(rework_wo_id, product_id, rework_qty)

    def try_ship_customer_order(self, wo_id: str, product_id: str, available_qty: float):
        """客户订单发货闭环（含Task9: FQC成品出货检验）"""
        co = self.db.get_customer_order_by_wo(wo_id)
        if not co or co.get("status") in ("已发货", "已取消"):
            return

        order_qty = co.get("quantity", 0)
        fg_state = self.fg_inventory_state.get(product_id, {})
        fg_avail = fg_state.get("available", 0)

        # 发货数量 = min(订单数量, 库存可用数量)
        ship_qty = min(order_qty, fg_avail)
        if ship_qty <= 0:
            return

        # 扮减成品库存
        fg_state["available"] = max(0, fg_state.get("available", 0) - ship_qty)
        fg_state["total"] = max(0, fg_state.get("total", 0) - ship_qty)
        fg_state["shipped"] = fg_state.get("shipped", 0) + ship_qty

        # 更新成品库存表
        fg_inv_id = f"FGI-{product_id}"
        self.db.update("finished_goods_inventory", {"fg_inv_id": fg_inv_id}, {
            "total_quantity": lambda col: max(0, (col or 0) - ship_qty),
            "available_quantity": lambda col: max(0, (col or 0) - ship_qty),
            "shipped_quantity": lambda col: (col or 0) + ship_qty,
            "last_updated": self.sim_time_to_datetime(self.env.now)
        })

        # Task9: FQC成品出货检验
        fqc_passed = self._run_fqc(co["order_id"], product_id, ship_qty)
        if not fqc_passed:
            # FQC不合格：启动完整重工流程
            print(f"  [FQC不合格] 订单{co['order_id']}出货检验不合格，启动重工流程")
            
            # 1. 从成品库存中移除（转入重工区）
            fg_state["available"] = max(0, fg_state.get("available", 0) - ship_qty)
            fg_state["total"] = max(0, fg_state.get("total", 0) - ship_qty)
            
            # 2. 创建重工工单
            rework_wo_id = self.create_fqc_rework_order(co["order_id"], product_id, ship_qty)
            
            # 3. 更新客户订单状态
            self.db.update("customer_order", {"order_id": co["order_id"]}, {
                "status": "重工中",
                "note": f"FQC不合格，已创建重工工单{rework_wo_id}"
            })
            return

        # 计算OTD
        now_dt = self.sim_time_to_datetime(self.env.now)
        required_dt = co.get("required_date")
        if isinstance(required_dt, str):
            try:
                required_dt = datetime.fromisoformat(required_dt.replace('Z', '+00:00'))
            except Exception:
                required_dt = None
        is_on_time = required_dt is None or now_dt <= required_dt
        otd_note = f"按时交付" if is_on_time else f"迟交{(now_dt - required_dt).days}天"

        # 更新客户订单状态（区分全量发货和部分发货）
        order_qty = co.get("quantity", 0)
        new_co_status = "已发货" if ship_qty >= order_qty * 0.99 else "部分发货"
        self.db.update("customer_order", {"order_id": co["order_id"]}, {
            "status": new_co_status,
            "note": f"实际发货{ship_qty:.1f}/{order_qty:.0f}个，{otd_note}"
        })

        # 注：成品出库不写 inventory_transaction（product_id 外键断链风险）
        print(f"  [发货] 工单{wo_id}对应订单{co['order_id']}，发货{ship_qty:.1f}，{otd_note}")

    # ========================================================================
    # Task 5: 质检QC Hold
    # ========================================================================

    def trigger_quality_inspection(self, wo_op_id: str, lot_id: str, machine_id: str,
                                    inspect_qty: float, scrap_qty: float) -> float:
        """对关键工序触发质检，返回实际报废数量（部分可能转为返工）"""
        if scrap_qty <= 0:
            # 无次品，记录合格
            insp_id = self.next_id("QI")
            self.db.insert("quality_inspection", {
                "inspection_id": insp_id,
                "inspection_type": "过程质检",
                "wo_op_id": wo_op_id,
                "lot_id": lot_id,
                "machine_id": machine_id,
                "related_doc_type": "WorkOrderOperation",
                "related_doc_id": wo_op_id,
                "inspection_time": self.sim_time_to_datetime(self.env.now),
                "inspect_qty": inspect_qty,
                "pass_qty": inspect_qty,
                "rework_qty": 0.0,
                "scrap_qty": 0.0,
                "result": "合格",
                "is_hold": False,
                "disposition": "全数合格，放行"
            })
            return 0.0

        # 有次品：30%概率可返工，70%直接报废
        rework_prob = 0.30
        if random.random() < rework_prob:
            rework_qty = scrap_qty
            actual_scrap = 0.0
            result = "返工"
            is_hold = True
            disposition = f"{rework_qty:.1f}个判定可返工，Hold等待返工排程"
        else:
            rework_qty = 0.0
            actual_scrap = scrap_qty
            result = "报废"
            is_hold = False
            disposition = f"{actual_scrap:.1f}个判定不可修复，直接报废"

        insp_id = self.next_id("QI")
        self.db.insert("quality_inspection", {
            "inspection_id": insp_id,
            "inspection_type": "过程质检",
            "wo_op_id": wo_op_id,
            "lot_id": lot_id,
            "machine_id": machine_id,
            "related_doc_type": "WorkOrderOperation",
            "related_doc_id": wo_op_id,
            "inspection_time": self.sim_time_to_datetime(self.env.now),
            "inspect_qty": inspect_qty + scrap_qty,
            "pass_qty": inspect_qty,
            "rework_qty": rework_qty,
            "scrap_qty": actual_scrap,
            "result": result,
            "is_hold": is_hold,
            "disposition": disposition
        })

        if is_hold and lot_id and lot_id in self.wip_lot_state:
            self.db.update("wip_lot", {"lot_id": lot_id}, {
                "lot_status": "Hold",
                "hold_reason": f"QC判定返工{rework_qty:.1f}个"
            })
            # 简化返工处理：Hold 4小时后自动解除，Lot 重回排队（原工序重跑）
            self.env.process(self._rework_hold_release(lot_id, rework_qty))

        return actual_scrap  # 返回实际报废数量



    # ========================================================================
    # Task 7: 库存盘点调整进程
    # ========================================================================

    def inventory_cycle_count_process(self):
        """每7天对所有物料执行一次盘点，产生账实差异"""
        import math
        yield self.env.timeout(7 * 24.0)  # 第一次盘点在第7天收盘后
        while True:
            today = self.sim_time_to_datetime(self.env.now).date()
            print(f"  [盘点] Day{self.get_sim_day()} 开始库存周期盘点...")
            for material_id, inv in self.inventory_state.items():
                total = inv.get("total", 0)
                if total <= 0:
                    continue
                # 正态分布扰动：均值0，标准差为库存量的2%
                import random
                sigma = total * 0.02
                # Box-Muller transform for normal distribution
                u1, u2 = random.random(), random.random()
                if u1 < 1e-10:
                    u1 = 1e-10
                z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
                adjustment = round(z * sigma, 2)
                if abs(adjustment) < 0.01:
                    continue
                # 更新内存
                inv["total"] = max(0, inv["total"] + adjustment)
                inv["available"] = max(0, inv["available"] + adjustment)
                trans_type = "盘点盈余" if adjustment > 0 else "盘点亏损"
                self.record_inventory_transaction(
                    material_id, trans_type, abs(adjustment),
                    description=f"周期盘点调整{'+' if adjustment > 0 else ''}{adjustment:.2f}"
                )
            yield self.env.timeout(7 * 24.0)

    # ========================================================================
    # Task 8: 换线首件检验IPQC
    # ========================================================================

    def _ipqc_first_article(self, machine_id: str, wo_op_id: str, wo_id: str, product_id: str):
        """换线后首件检验：不合格率由配置控制，最多重检一次"""
        import random
        ipqc_id = f"IPQC-{wo_op_id}-{self.counters['qc']:04d}"
        self.counters['qc'] += 1
        
        # 从配置读取检验耗时和不合格率
        inspection_hours = self.config.get("ipqc_inspection_hours", 0.5)
        reject_rate = self.config.get("ipqc_reject_rate", 0.15)
        
        yield self.env.timeout(inspection_hours)  # 首件检验耗时

        passed = random.random() >= reject_rate  # 按配置的不合格率判断
        result = "合格" if passed else "不合格"

        self.db.insert("quality_inspection", {
            "inspection_id": ipqc_id,
            "inspection_type": "首件检验",
            "related_doc_type": "WorkOrderOperation",
            "related_doc_id": wo_op_id,
            "inspect_qty": 1,
            "pass_qty": 1 if passed else 0,
            "scrap_qty": 0 if passed else 1,
            "result": result,
            "inspector": "IPQC-AUTO",
            "inspection_time": self.sim_time_to_datetime(self.env.now),
            "machine_id": machine_id,
            "note": f"换线后首件检验"
        })

        if not passed:
            print(f"  [IPQC不合格] {machine_id} 首件检验不合格，调整后重检")
            yield self.env.timeout(0.5)  # 调整+重检0.5小时
            # 重检必定合格（现实中若两次不合格会停机，这里简化）
            recheck_id = f"IPQC-{wo_op_id}-RC{self.counters['qc']:04d}"
            self.counters['qc'] += 1
            self.db.insert("quality_inspection", {
                "inspection_id": recheck_id,
                "inspection_type": "首件检验",
                "related_doc_type": "WorkOrderOperation",
                "related_doc_id": wo_op_id,
                "inspect_qty": 1,
                "pass_qty": 1,
                "scrap_qty": 0,
                "result": "合格",
                "inspector": "IPQC-AUTO",
                "inspection_time": self.sim_time_to_datetime(self.env.now),
                "machine_id": machine_id,
                "note": "调整后重检合格"
            })
            print(f"  [IPQC重检合格] {machine_id} 调整后合格，开始正式生产")

    # ========================================================================
    # Task 9: FQC成品出货检验辅助
    # ========================================================================

    def _run_iqc(self, qty: float, material_id: str):
        """IQC检验，返回 (result, scrap_qty, actual_qty)"""
        import random
        # 从配置读取IQC不合格率和报废率范围（独立配置）
        fail_rate = self.config.get("iqc_reject_rate", 0.03)  # 来料不合格率（3%）
        scrap_range = self.config.get("iqc_scrap_rate_range", [0.03, 0.15])  # 来料报废率范围
        
        if random.random() < fail_rate:
            scrap_qty = round(qty * random.uniform(scrap_range[0], scrap_range[1]), 2)
            actual_qty = qty - scrap_qty
            return "不合格-部分", scrap_qty, actual_qty
        return "合格", 0.0, qty

    def _run_fqc(self, order_id: str, product_id: str, ship_qty: float) -> bool:
        """FQC成品出货检验，写入质检记录，返回是否通过"""
        import random
        fqc_id = f"FQC-{order_id}-{self.counters['qc']:04d}"
        self.counters['qc'] += 1
        
        # 从配置读取FQC不合格率
        fail_rate = self.config.get("fqc_reject_rate", 0.05)
        passed = random.random() >= fail_rate

        self.db.insert("quality_inspection", {
            "inspection_id": fqc_id,
            "inspection_type": "FQC出货检验",
            "related_doc_type": "CustomerOrder",
            "related_doc_id": order_id,
            "inspect_qty": ship_qty,
            "pass_qty": ship_qty if passed else 0,
            "scrap_qty": 0 if passed else ship_qty,
            "result": "合格" if passed else "不合格",
            "inspector": "FQC-AUTO",
            "inspection_time": self.sim_time_to_datetime(self.env.now),
            "note": f"成品出货前FQC检验"
        })
        return passed

    def create_fqc_rework_order(self, order_id: str, product_id: str, rework_qty: float) -> str:
        """
        创建FQC重工工单（符合真实半导体行业实践）
        
        重工原则：
        1. 复用正常工艺路线，不创建新工序
        2. 走正常排程流程，占用机台资源
        3. 优先级设置为1（最高）
        4. 工序标记为重工类型，便于追溯
        5. 应用投入过量方案，考虑重工工序良率损耗
        
        重工场景：
        - FQC不合格通常是包装/标识问题，重工从"重新包装"开始
        - 严重功能不良直接报废，不重工
        """
        import random
        
        # 1. 判定是否可重工（80%可重工，20%直接报废）
        reworkable = random.random() < self.config.get("reworkable_rate", 0.80)
        
        if not reworkable:
            # 严重不良，直接报废
            print(f"  [重工判定] 订单{order_id}不良严重，无法重工，报废{rework_qty:.1f}")
            
            # 更新订单状态
            self.db.update("customer_order", {"order_id": order_id}, {
                "status": "已取消",
                "note": f"FQC不合格，不良严重无法重工，报废{rework_qty:.1f}"
            })
            return None
        
        # 2. 获取重工工序（最后3道）
        route_id = self.get_route_for_product(product_id)
        if not route_id:
            print(f"  [重工错误] 产品{product_id}无工艺路线")
            return None
        
        all_steps = self.route_steps.get(route_id, [])
        if not all_steps:
            print(f"  [重工错误] 工艺路线{route_id}无工序")
            return None
        
        # 取最后3道工序作为重工工序（包装、测试、最终检查）
        rework_step_count = min(3, len(all_steps))
        rework_steps = all_steps[-rework_step_count:]
        
        # 3. 【投入过量方案】计算重工需要的投入量
        # 重工工序的总良率 = 0.98^3 = 94.1%
        rework_total_yield = 1.0
        for step in rework_steps:
            step_yield = step.get("yield_rate_standard", self.config.get("default_yield_rate", 0.98))
            rework_total_yield *= step_yield
        
        # 反推重工投入量
        rework_input_qty = rework_qty / rework_total_yield
        
        # 向上取整到Lot大小的倍数
        lot_size = self.config.get("wip_lot_size", 25)
        rework_input_qty = math.ceil(rework_input_qty / lot_size) * lot_size
        
        print(f"  [重工计算] 订单{order_id}：需要{rework_qty:.1f}个 → 重工投入{rework_input_qty:.1f}个（良率{rework_total_yield:.2%}）")
        
        # 4. 创建重工工单（使用投入量）
        rework_wo_id = self.next_id("WO-RW")
        now_dt = self.sim_time_to_datetime(self.env.now)
        
        # 数据库记录
        rework_wo = {
            "work_order_id": rework_wo_id,
            "customer_order_id": order_id,
            "product_id": product_id,
            "planned_quantity": rework_input_qty,  # ✅ 重工投入量（过量）
            "expected_output_qty": rework_qty,  # ✅ 预期产出量（FQC不合格数量）
            "priority": 1,  # 重工工单最高优先级
            "status": "已下达",
            "work_order_type": "重工",
            "planned_start_date": now_dt,
            "planned_completion_date": now_dt,
            "note": f"FQC不合格重工，原订单{order_id}，投入{rework_input_qty:.1f}→预期{rework_qty:.1f}",
            "created_at": now_dt
        }
        self.db.insert("work_order", rework_wo)
        
        # 内存状态（必须包含所有必需字段）
        self.work_order_state[rework_wo_id] = {
            "status": "已下达",
            "current_step_idx": 0,
            "allocated_materials": {},
            "product_id": product_id,
            "quantity": rework_input_qty,  # ✅ 投入量
            "order_quantity": rework_qty,  # ✅ 订单数量（FQC不合格数量）
            "work_order_type": "重工"
        }
        
        print(f"  [重工工单] 创建{rework_wo_id}：产品{product_id}，投入{rework_input_qty:.1f}→预期{rework_qty:.1f}，优先级1")
        
        # 5. 展开重工工序（复用正常工艺路线）
        print(f"  [重工路线] 复用{route_id}的最后{rework_step_count}道工序")
        
        # 展开工序（标记为重工）
        rework_ops = []
        base_date = now_dt
        current_input_qty = rework_input_qty  # 当前工序投入量
        
        for idx, step in enumerate(rework_steps):
            wo_op_id = self.next_id("WOOP")
            
            # 计算计划时间（复用正常逻辑）
            std_time = step.get("std_time", 0.1) * current_input_qty
            planned_start = base_date
            planned_end = base_date + timedelta(hours=std_time + 0.5)  # 0.5小时排队时间
            
            wo_op = {
                "wo_op_id": wo_op_id,
                "work_order_id": rework_wo_id,
                "step_id": step["step_id"],
                "sequence_no": step["sequence_no"],
                "status": "待开工",
                "planned_start": planned_start,
                "planned_end": planned_end,
                "required_input_qty": round(current_input_qty, 4),  # ✅ 使用当前工序投入量
                "is_rework": True  # 标记为重工序工，便于追溯和统计
            }
            self.db.insert("work_order_operation", wo_op)
            rework_ops.append(wo_op)
            
            # 下一道工序的投入 = 本道工序产出（×良率）
            step_yield = step.get("yield_rate_standard", self.config.get("default_yield_rate", 0.98))
            current_input_qty *= step_yield
            
            base_date = planned_end
        
        # 6. 创建WIP Lot（待重工）- 使用投入量
        rework_lot_id = self.next_id("LOT-RW")
        rework_lot = {
            "lot_id": rework_lot_id,
            "work_order_id": rework_wo_id,
            "product_id": product_id,
            "lot_size": rework_input_qty,  # ✅ 使用投入量
            "current_qty": rework_input_qty,  # ✅ 使用投入量
            "lot_status": "待重工",
            "status": "排队中",
            "created_at": now_dt,
            "queue_start_time": now_dt
        }
        self.db.insert("wip_lot", rework_lot)
        
        # 内存状态（必须包含wo_id，否则_get_lot_for_op会报错）
        self.wip_lot_state[rework_lot_id] = {
            "wo_id": rework_wo_id,  # ← 关键字段！
            "product_id": product_id,
            "current_step_idx": 0,
            "status": "排队中",
            "current_qty": rework_input_qty  # ✅ 使用投入量
        }
        
        print(f"  [重工Lot] 创建{rework_lot_id}，投入{rework_input_qty:.1f}个，状态：待重工")
        
        # 7. 触发实时排程（重工工单进入排程队列）
        # 注：重工工单和正常工单一样，走daily_scheduler和realtime_schedule排程
        # 由于优先级=1，会被优先排程
        
        return rework_wo_id
    
    def _rework_hold_release(self, lot_id: str, rework_qty: float):
        """简化返工处理：Hold 4小时后自动解除，Lot 重回排队"""
        yield self.env.timeout(4.0)
        if lot_id not in self.wip_lot_state:
            return
        rework_yield = 0.95
        actual_rework_qty = round(rework_qty * rework_yield, 4)
        self.wip_lot_state[lot_id]['current_qty'] = actual_rework_qty
        self.wip_lot_state[lot_id]['status'] = '排队中'
        self.db.update('wip_lot', {'lot_id': lot_id}, {
            'lot_status': '排队中',
            'actual_quantity': actual_rework_qty,
            'hold_reason': None,
            'queue_start_time': self.sim_time_to_datetime(self.env.now)
        })
        print(f'  [返工完成] Lot {lot_id}: 返工{rework_qty:.1f} -> 合格{actual_rework_qty:.1f}，重回排队')



    # ========================================================================
    # Task 5: 客户订单取消进程
    # ========================================================================

    def order_cancellation_process(self):
        """Task5: 每天以一定概率取消未开工的已确认订单"""
        import random
        cancel_prob = self.config.get("order_cancel_daily_prob", 0.05)

        while True:
            yield self.env.timeout(24.0)  # 每天检查一次

            # 获取所有"已确认"状态的订单（只要未开工就可取消）
            confirmed_orders = self.db.query_by_status("customer_order", "已确认")
            if not confirmed_orders:
                yield self.env.timeout(0)  # 限制每批取消不超过3笔
                continue

            cancelled_this_round = 0
            max_cancel_per_day = 3  # 每天最多取消3笔，避免大量取消
            for co in confirmed_orders:
                if cancelled_this_round >= max_cancel_per_day:
                    break
                order_id = co["order_id"]
                if random.random() >= cancel_prob:
                    continue

                # 检查工单是否已开工
                wo = self.db.get_work_order_by_co(order_id)
                if not wo:
                    continue

                wo_id = wo["work_order_id"]
                wo_state = self.work_order_state.get(wo_id, {})
                # 已开工的工单不能取消
                if wo_state.get("actual_started"):
                    continue
                if wo.get("actual_start_date"):
                    continue
                # 已取消的订单跳过
                if co.get("status") == "已取消":
                    continue

                # 执行取消
                print(f"  [订单取消] 订单{order_id} 被客户取消，工单{wo_id}随之取消")

                # 释放已预留物料
                woms = self.db.query("work_order_material", {"work_order_id": wo_id})
                for wom in (woms or []):
                    mat_id = wom.get("material_id")
                    alloc_qty = wom.get("allocated_quantity", 0)
                    if alloc_qty > 0 and mat_id and mat_id in self.inventory_state:
                        inv = self.inventory_state[mat_id]
                        inv["reserved"] = max(0, inv.get("reserved", 0) - alloc_qty)
                        inv["available"] = inv.get("available", 0) + alloc_qty
                        self.record_inventory_transaction(
                            mat_id, "取消释放", alloc_qty,
                            related_doc_type="WorkOrder", related_doc_id=wo_id,
                            description=f"订单{order_id}取消释放预留物料"
                        )
                    self.db.update("work_order_material", {"wom_id": wom["wom_id"]},
                                   {"status": "已取消"})

                # 更新工单和订单状态
                self.db.update("work_order", {"work_order_id": wo_id}, {"status": "已取消"})
                self.db.update("customer_order", {"order_id": order_id}, {
                    "status": "已取消",
                    "note": f"Day{self.get_sim_day()} 客户主动取消"
                })

                # 更新内存状态
                if wo_id in self.work_order_state:
                    self.work_order_state[wo_id]["status"] = "已取消"
                cancelled_this_round += 1

    # ========================================================================
    # Task 10: 订单优先级动态升级进程
    # ========================================================================

    def priority_escalation_process(self):
        """Task10: 每天随机对一个订单触发紧急升级（模拟客户追单）"""
        import random
        escalate_prob = self.config.get("priority_escalation_daily_prob", 0.08)

        while True:
            yield self.env.timeout(24.0)

            if random.random() >= escalate_prob:
                continue

            # 随机选一个"已确认"且未被升级过的订单
            confirmed_orders = self.db.query_by_status("customer_order", "已确认")
            if not confirmed_orders:
                continue

            candidates = [co for co in confirmed_orders
                          if co["order_id"] not in self.escalated_orders]
            if not candidates:
                continue

            co = random.choice(candidates)
            order_id = co["order_id"]
            old_priority = co.get("priority", 5)

            # 升级优先级为1（最高）
            self.db.update("customer_order", {"order_id": order_id}, {
                "priority": 1,
                "note": f"[紧急插单] Day{self.get_sim_day()} 客户紧急追单，优先级从{old_priority}升至1"
            })
            self.escalated_orders.add(order_id)

            # 联动更新关联工单优先级
            wo = self.db.get_work_order_by_co(order_id)
            if wo:
                wo_id = wo["work_order_id"]
                self.db.update("work_order", {"work_order_id": wo_id}, {"priority": 1})
                if wo_id in self.work_order_state:
                    self.work_order_state[wo_id]["priority"] = 1

            print(f"  [紧急升级] 订单{order_id} 优先级{old_priority}→1（客户紧急追单）")

    # ========================================================================
    # Task 3: 机台随机故障进程
    # ========================================================================

    def machine_breakdown_process(self, machine_id: str):
        """Task3: 机台随机故障（非计划停机）仿真进程"""
        import random
        import math
        mtbf = self.config.get("breakdown_mtbf_hours", 96)
        mttr = self.config.get("breakdown_mttr_hours", 4)

        # 错开首次故障时间（避免全部机台同时第一次故障）
        first_wait = random.uniform(mtbf * 0.3, mtbf * 1.5)
        yield self.env.timeout(first_wait)

        while True:
            # 等待当前任务完成才能触发故障（不中断进行中的加工）
            while self.machine_state[machine_id].get("status") == "运行中":
                yield self.env.timeout(0.25)

            # 跳过已在维护中的机台
            if machine_id in self.machines_under_maintenance:
                yield self.env.timeout(4.0)
                continue

            # 触发故障
            self.machines_under_maintenance.add(machine_id)
            prev_status = self.machine_state[machine_id].get("status", "空闲")
            self.machine_state[machine_id]["status"] = "故障"

            # 故障持续时间：均匀分布 [1, 2*mttr]
            breakdown_hours = random.uniform(1.0, mttr * 2.0)

            # 写入机台状态日志
            self.log_machine_status(machine_id, "故障", None, None, None,
                                    oee=self._calculate_oee(machine_id))
            print(f"  [机台故障] {machine_id} 发生故障！Day={self.get_sim_day()}, 预计修复时间={breakdown_hours:.1f}h")

            yield self.env.timeout(breakdown_hours)

            # 故障修复
            self.machines_under_maintenance.discard(machine_id)
            self.machine_state[machine_id]["status"] = "空闲"
            self.machine_state[machine_id]["next_available_time"] = self.env.now
            self.log_machine_status(machine_id, "恢复", None, None, None)
            print(f"  [机台恢复] {machine_id} 故障修复完成，恢复生产")

            # 下次故障等待：指数分布（均值mtbf）
            # 使用简单的指数分布采样：-ln(U) * mtbf
            u = random.random()
            if u < 1e-10:
                u = 1e-10
            next_wait = -math.log(u) * mtbf
            yield self.env.timeout(next_wait)

    def machine_maintenance_process(self, machine_id: str):
        """P0-4: 单台机台的定期PM进程"""
        pm_interval = self.config["maintenance_frequency_hours"]
        pm_duration = self.config["maintenance_duration_hours"]

        while True:
            # 等待到下次PM时间（从上次运行小时数计算）
            yield self.env.timeout(pm_interval)

            # 等待机台空闲（不能强行中断正在加工的任务）
            while self.machine_state[machine_id]["status"] not in ("空闲", "已占用"):
                yield self.env.timeout(0.5)  # 每30分钟检查一次

            # 等待当前任务完成
            while self.machine_state[machine_id]["status"] == "运行中":
                yield self.env.timeout(0.25)

            # 开始PM
            self.machines_under_maintenance.add(machine_id)
            self.machine_state[machine_id]["status"] = "维护中"
            self.machine_state[machine_id]["last_pm_hours"] = self.env.now

            self.log_machine_status(machine_id, "维护", None, None, None,
                                    oee=self._calculate_oee(machine_id))
            print(f"  [PM维护] {machine_id} 开始维护, Day={self.get_sim_day()}")

            yield self.env.timeout(pm_duration)

            # PM完成
            self.machines_under_maintenance.discard(machine_id)
            self.machine_state[machine_id]["status"] = "空闲"
            self.machine_state[machine_id]["next_available_time"] = self.env.now
            self.log_machine_status(machine_id, "空闲", None, None, None)
            print(f"  [PM完成] {machine_id} 维护结束, 耗时{pm_duration}小时")

    def _calculate_oee(self, machine_id: str) -> float:
        """计算机台综合效率OEE"""
        state = self.machine_state.get(machine_id, {})
        total_run = state.get("total_run_hours", 0)
        total_setup = state.get("total_setup_hours", 0)
        total_time = self.env.now - 8.0  # 从第一天8:00开始
        if total_time <= 0:
            return 0.0
        # 简化OEE = 有效加工时间 / 总时间
        return min(1.0, total_run / max(total_time, 1.0))

    # ========================================================================
    # P1-9: MachineCapability动态OEE闭环更新
    # ========================================================================

    def daily_oee_updater(self):
        """每天收盘后更新MachineCapability的实际效率均值"""
        while True:
            yield self.wait_until_next_work_start()
            yield self.env.timeout(12.5)  # 20:30 日班结束后更新

            day = self.get_sim_day()
            if day < 3:  # 前3天数据太少，不更新
                continue

            for machine_id, product_stats in self.machine_daily_stats.items():
                for product_id, samples in product_stats.items():
                    if not samples:
                        continue

                    # 计算加权均值（按加工时间加权）
                    total_weight = sum(s[2] for s in samples)
                    if total_weight <= 0:
                        continue

                    weighted_efficiency = sum(s[0] * s[2] for s in samples) / total_weight
                    weighted_yield = sum(s[1] * s[2] for s in samples) / total_weight
                    count = len(samples)

                    # 查询当前capability_id
                    cap_key = (machine_id, product_id)
                    cap = self.machine_capabilities.get(cap_key)
                    if cap:
                        cap_id = cap.get("capability_id")
                        self.db.update("machine_capability", {"capability_id": cap_id}, {
                            "actual_efficiency_avg": round(weighted_efficiency, 4),
                            "actual_yield_avg": round(weighted_yield, 4),
                            "sample_count": lambda col: (col or 0) + count,
                            "last_updated_at": self.sim_time_to_datetime(self.env.now)
                        })
                        print(f"  [OEE更新] {machine_id}-{product_id}: "
                              f"效率={weighted_efficiency:.3f}, 良率={weighted_yield:.3f}, "
                              f"样本数={count}")

            # 清空当日统计（滚动计算，只看近期数据）
            self.machine_daily_stats.clear()

            yield self.env.timeout(11.5)  # 等到第二天排程前

    # ========================================================================
    # 仿真主控
    # ========================================================================

    def run(self):
        """启动所有仿真事件"""
        # 主流程
        self.env.process(self.order_generator())
        self.env.process(self.daily_mrp_processor())
        self.env.process(self.daily_scheduler())

        # P0-4: 为每台机台启动独立PM进程（随机错开启动时间避免同时维护）
        for i, machine_id in enumerate(self.machines.keys()):
            offset = i * 24.0 / len(self.machines)  # 错开启动
            self.env.process(self._delayed_pm_start(machine_id, offset))

        # P2-11: 安全库存监控
        self.env.process(self.safety_stock_monitor())

        # Task3: 为每台机台启动随机故障进程
        bd_prob = self.config.get("breakdown_probability", 0.70)
        import random as _random
        for machine_id in self.machines.keys():
            if _random.random() < bd_prob:
                self.env.process(self.machine_breakdown_process(machine_id))

        # Task5: 客户订单取消进程
        self.env.process(self.order_cancellation_process())

        # Task7: 库存周期盘点进程
        self.env.process(self.inventory_cycle_count_process())

        # Task10: 订单优先级动态升级进程
        self.env.process(self.priority_escalation_process())

        # Task11: 仓库间平衡调拨进程
        self.env.process(self.warehouse_balance_transfer_process())
        # P1-9: OEE动态更新
        self.env.process(self.daily_oee_updater())

        # 运行仿真
        duration_hours = self.config["duration_days"] * 24
        self.env.run(until=duration_hours)

        # 刷新剩余缓冲区
        self.flush_transactions()
        self.flush_status_logs()
        
        # 同步最终库存状态到数据库
        self._sync_inventory_to_db()
        
        # 同步最终成品库存状态到数据库
        self._sync_fg_inventory_to_db()

        print(f"\n仿真完成！总仿真时间: {duration_hours}小时 ({self.config['duration_days']}天)")

    def _delayed_pm_start(self, machine_id: str, offset_hours: float):
        """P0-4: 延迟启动PM进程（错开各机台首次维护时间）"""
        yield self.env.timeout(offset_hours)
        yield from self.machine_maintenance_process(machine_id)
