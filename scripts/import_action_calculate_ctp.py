"""
导入CTP可承诺量计算Action到本体

Action: calculateCTP
功能: 计算客户订单的可承诺交期
求解器: MIP (CBC)
难度: ⭐⭐
"""
import requests
import json

# API配置
API_URL = "http://localhost:8080/api/v1"

# Action定义
ACTION_DATA = {
    "id": "calculate_ctp",
    "api_name": "CalculateCTP",
    "name": "CTP可承诺量计算",
    "description": "根据当前产能负荷、物料可用性、工艺路线，计算客户订单的最早可承诺交期",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "customer_order",
    "parameters": [
        {
            "name": "order_id",
            "type": "string",
            "required": True,
            "description": "客户订单ID"
        },
        {
            "name": "quantity",
            "type": "float",
            "required": False,
            "description": "订单数量，如不指定则使用订单原始数量"
        },
        {
            "name": "planning_horizon_days",
            "type": "integer",
            "required": False,
            "description": "排程规划的时间范围，默认30天"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# CTP计算函数实现 - 使用 Ontology SDK + OR-Tools
import json
from datetime import datetime, timedelta
from ortools.linear_solver import pywraplp

# 使用 SDK
from my_ontology_sdk import OntologyClient

def execute_calculate_ctp(parameters):
    """
    CTP可承诺量计算 - MIP模型
    
    数学模型:
    - 决策变量: x[o,m,t]工序分配, S[o]开始时间, E[o]结束时间, Delay延迟
    - 目标函数: Minimize Delay
    - 约束条件:
      1. 开始时间定义: S[o] = Σ(t * x[o,m,t])
      2. 结束时间: E[o] = S[o] + P[o]
      3. 工艺路线顺序: S[o(i+1)] >= E[o(i)]
      4. 机台产能: Σx[o,m,t] <= 1
      5. 工序必须调度: Σx[o,m,t] = 1
      6. 工作日历约束
      7. 物料可用性检查
    
    Args:
        parameters: 包含order_id, quantity等参数
    Returns:
        dict: CTP计算结果（承诺交期、瓶颈工序、风险提示）
    """
    try:
        # 1. 解析参数
        order_id = parameters.get("order_id")
        if not order_id:
            return {"success": False, "error": "缺少订单ID参数"}
        
        quantity = parameters.get("quantity")
        planning_horizon_days = parameters.get("planning_horizon_days", 30)
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # 3. 获取订单信息
        order = client.models.CustomerOrder.get(order_id)
        if not order:
            return {"success": False, "error": f"订单不存在: {order_id}"}
        
        # 使用订单数量或参数指定数量
        qty = quantity if quantity else order.quantity
        
        # 【新增】获取客户信息，用于优先级加权
        customer_level = "普通"
        customer_weight = 1.0
        if hasattr(order, 'customer_id') and order.customer_id:
            customer = client.models.Customer.get(order.customer_id)
            if customer:
                customer_level = customer.customer_level or "普通"
                # 客户等级加权：VIP=2.0, 重要=1.5, 普通=1.0
                customer_weight = {
                    "VIP": 2.0,
                    "重要": 1.5,
                    "普通": 1.0
                }.get(customer_level, 1.0)
        
        # 4. 获取产品信息和工艺路线
        product = client.models.Product.get(order.product_id)
        if not product:
            return {"success": False, "error": f"产品不存在: {order.product_id}"}
        
        # 获取工艺路线
        routes = client.models.ProcessRoute.find(product_id=order.product_id, is_active=True)
        if not routes:
            return {"success": False, "error": f"产品没有激活的工艺路线: {order.product_id}"}
        
        route = routes[0]  # 取第一个激活的路线
        
        # 获取工序列表
        steps = client.models.RouteStep.find(route_id=route.route_id)
        if not steps:
            return {"success": False, "error": "工艺路线没有工序"}
        
        # 按工序序号排序
        steps = sorted(steps, key=lambda s: s.sequence_no or 0)
        
        # 5. 获取可用机台
        machines = _get_available_machines(client, steps)
        if not machines:
            return {"success": False, "error": "没有可用机台"}
        
        # 6. 检查物料可用性
        material_check = _check_material_availability(client, order.product_id, qty)
        if not material_check["available"]:
            return {
                "success": False,
                "error": "物料不足",
                "material_shortages": material_check["shortages"]
            }
        
        # 7. 创建MIP求解器
        solver = pywraplp.Solver.CreateSolver('CBC')
        if not solver:
            return {"success": False, "error": "无法创建求解器"}
        
        # 8. 准备数据
        # 时间槽（按小时）
        time_slots = range(planning_horizon_days * 24)
        
        # 起始时间
        start_time = datetime.now()
        
        # 9. 创建决策变量
        x = {}  # x[o, m, t]: 工序o是否在机台m、时间t开始
        S = {}  # S[o]: 工序o的开始时间
        E = {}  # E[o]: 工序o的结束时间
        
        for step in steps:
            for machine in machines:
                # 检查机台能力
                if not _check_machine_capability(client, machine.machine_id, order.product_id):
                    continue
                
                for t in time_slots:
                    # 检查工作日历
                    if not _check_work_calendar(client, machine.work_center_id, start_time + timedelta(hours=t)):
                        continue
                    
                    x[step.step_id, machine.machine_id, t] = solver.IntVar(
                        0, 1, f'x_{step.step_id}_{machine.machine_id}_{t}'
                    )
            
            # 开始时间和结束时间变量
            S[step.step_id] = solver.NumVar(0, planning_horizon_days * 24, f'S_{step.step_id}')
            E[step.step_id] = solver.NumVar(0, planning_horizon_days * 24, f'E_{step.step_id}')
        
        # 延迟变量
        Delay = solver.NumVar(0, planning_horizon_days * 24, 'Delay')
        
        # 10. 添加约束
        
        # 约束1: 开始时间定义
        for step in steps:
            valid_vars = [
                t * x[step.step_id, m.machine_id, t]
                for m in machines
                for t in time_slots
                if (step.step_id, m.machine_id, t) in x
            ]
            if valid_vars:
                solver.Add(S[step.step_id] == sum(valid_vars))
        
        # 约束2: 结束时间 = 开始时间 + 加工时长
        for step in steps:
            # 计算加工时长（考虑数量）
            processing_time = _calculate_processing_time(step, qty)
            solver.Add(E[step.step_id] == S[step.step_id] + processing_time)
        
        # 约束3: 工艺路线顺序（关键约束）
        for i in range(len(steps) - 1):
            current_step = steps[i]
            next_step = steps[i + 1]
            solver.Add(S[next_step.step_id] >= E[current_step.step_id])
        
        # 约束4: 机台产能（同一时间只能执行一道工序）
        for machine in machines:
            for t in time_slots:
                machine_step_vars = [
                    x[step.step_id, machine.machine_id, t]
                    for step in steps
                    if (step.step_id, machine.machine_id, t) in x
                ]
                if machine_step_vars:
                    solver.Add(sum(machine_step_vars) <= 1)
        
        # 约束5: 每道工序必须被调度
        for step in steps:
            valid_vars = [
                x[step.step_id, m.machine_id, t]
                for m in machines
                for t in time_slots
                if (step.step_id, m.machine_id, t) in x
            ]
            if valid_vars:
                solver.Add(sum(valid_vars) == 1)
        
        # 11. 目标函数：最小化延迟（考虑客户加权）
        # 计算要求交期（小时）
        if order.required_date:
            required_date = datetime.fromisoformat(order.required_date) if isinstance(order.required_date, str) else order.required_date
            required_hours = (required_date - start_time).total_seconds() / 3600
        else:
            required_hours = planning_horizon_days * 24  # 默认使用planning_horizon
        
        # 最后一道工序
        last_step = steps[-1]
        solver.Add(Delay >= E[last_step.step_id] - required_hours)
        solver.Add(Delay >= 0)
        
        # 目标函数：最小化加权延迟（客户等级 * 订单优先级）
        objective = solver.Objective()
        
        # 订单优先级权重：P1(紧急)=10, P3(普通)=5, P5(宽松)=1
        order_priority = order.priority or 3
        order_priority_weight = {1: 10, 3: 5, 5: 1}.get(order_priority, 5)
        
        # 综合权重 = 客户等级权重 × 订单优先级权重
        total_weight = customer_weight * order_priority_weight
        
        objective.SetCoefficient(Delay, total_weight)
        objective.SetMinimization()
        
        print(f"[CTP计算] 客户等级: {customer_level} (权重: {customer_weight}x)")
        print(f"[CTP计算] 订单优先级: P{order_priority} (权重: {order_priority_weight}x)")
        print(f"[CTP计算] 综合权重: {total_weight}x")
        
        # 12. 求解
        solver.SetTimeLimit(30000)  # 30秒
        status = solver.Solve()
        
        # 13. 解析结果
        if status == pywraplp.Solver.OPTIMAL:
            # 计算承诺交期
            end_hours = E[last_step.step_id].solution_value()
            committed_date = start_time + timedelta(hours=end_hours)
            
            delay_hours = Delay.solution_value()
            
            # 识别瓶颈工序
            bottleneck = _find_bottleneck(E, steps)
            
            # 提取排程方案
            schedule = _extract_schedule(x, steps, machines, start_time)
            
            # 置信度计算
            confidence = _calculate_confidence(delay_hours, material_check)
            
            result = {
                "order_id": order_id,
                "customer_id": getattr(order, 'customer_id', None),
                "customer_name": order.customer_name,
                "customer_level": customer_level,
                "customer_weight": customer_weight,
                "product_id": order.product_id,
                "quantity": qty,
                "committed_date": committed_date.isoformat(),
                "delay_hours": round(delay_hours, 2),
                "confidence": round(confidence, 2),
                "bottleneck_step": bottleneck,
                "schedule": schedule,
                "material_risks": material_check.get("shortages", []),
                "priority_info": {
                    "order_priority": f"P{order_priority}",
                    "order_priority_weight": order_priority_weight,
                    "customer_level": customer_level,
                    "customer_weight": customer_weight,
                    "total_weight": total_weight
                }
            }
            
            return {
                "success": True,
                "message": f"CTP计算完成，承诺交期: {committed_date.strftime('%Y-%m-%d')}",
                "result": result
            }
        else:
            return {
                "success": False,
                "error": "无可行解，当前产能无法满足订单需求"
            }
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}


def _get_available_machines(client, steps):
    """获取可用机台列表"""
    try:
        # 收集所有需要的工作中心
        work_center_ids = list(set([s.machine_type_required for s in steps if s.machine_type_required]))
        
        machines = []
        for wc_id in work_center_ids:
            wc_machines = client.models.Machine.find(work_center_id=wc_id, is_active=True)
            machines.extend(wc_machines)
        
        return machines
    except:
        return []


def _check_machine_capability(client, machine_id, product_id):
    """检查机台是否有能力生产该产品"""
    try:
        capabilities = client.models.MachineCapability.find(
            machine_id=machine_id,
            product_id=product_id
        )
        return len(capabilities) > 0
    except:
        return True


def _check_work_calendar(client, work_center_id, target_time):
    """检查工作时间是否有效"""
    try:
        # 简化检查：周末不工作
        if target_time.weekday() >= 6:  # 周日
            return False
        
        # TODO: 可接入WorkCalendar进行更精确的检查
        return True
    except:
        return True


def _calculate_processing_time(step, quantity):
    """计算工序加工时长（小时）"""
    try:
        # standard_time_hours已经是Lot批量(25片)的时间
        # 需要根据实际数量调整
        lot_size = 25
        lots = quantity / lot_size
        
        # 总工时 = 标准工时 × 批次数 + 换线时间
        setup_hours = (step.setup_time_minutes or 0) / 60
        total_time = (step.standard_time_hours or 0) * lots + setup_hours
        
        return total_time
    except:
        return step.standard_time_hours or 1


def _check_material_availability(client, product_id, quantity):
    """检查物料可用性"""
    try:
        # 获取产品BOM
        boms = client.models.Bom.find(product_id=product_id)
        
        shortages = []
        all_available = True
        
        for bom in boms:
            # 获取物料库存
            inv_records = client.models.Inventory.find(material_id=bom.material_id)
            available_qty = inv_records[0].available_quantity if inv_records else 0
            
            # 计算需求量
            required_qty = (bom.quantity_per_unit or 0) * quantity
            
            if available_qty < required_qty:
                all_available = False
                shortages.append({
                    "material_id": bom.material_id,
                    "required": required_qty,
                    "available": available_qty,
                    "shortage": required_qty - available_qty
                })
        
        return {
            "available": all_available,
            "shortages": shortages
        }
    except:
        return {"available": True, "shortages": []}


def _find_bottleneck(E, steps):
    """识别瓶颈工序"""
    try:
        max_duration = 0
        bottleneck_step = None
        
        for i in range(len(steps) - 1):
            duration = E[steps[i+1].step_id].solution_value() - E[steps[i].step_id].solution_value()
            if duration > max_duration:
                max_duration = duration
                bottleneck_step = steps[i+1]
        
        return {
            "step_id": bottleneck_step.step_id if bottleneck_step else None,
            "step_name": bottleneck_step.step_name if bottleneck_step else None,
            "duration_hours": round(max_duration, 2)
        }
    except:
        return None


def _extract_schedule(x, steps, machines, start_time):
    """提取排程方案"""
    try:
        schedule = []
        
        for step in steps:
            for machine in machines:
                for t in range(720):
                    if (step.step_id, machine.machine_id, t) in x:
                        if x[step.step_id, machine.machine_id, t].solution_value() > 0.5:
                            schedule.append({
                                "step_id": step.step_id,
                                "step_name": step.step_name,
                                "machine_id": machine.machine_id,
                                "start_time": (start_time + timedelta(hours=t)).isoformat(),
                                "start_hour": t
                            })
        
        return schedule
    except:
        return []


def _calculate_confidence(delay_hours, material_check):
    """计算置信度"""
    try:
        # 基础置信度
        if delay_hours <= 0:
            confidence = 0.95
        elif delay_hours <= 24:
            confidence = 0.85
        elif delay_hours <= 72:
            confidence = 0.70
        else:
            confidence = 0.50
        
        # 物料风险调整
        if not material_check["available"]:
            confidence -= 0.15
        
        return max(0.0, min(1.0, confidence))
    except:
        return 0.7


# 必须定义result变量供Action框架使用
result = execute_calculate_ctp(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入CTP可承诺量计算Action")
    print("=" * 60)
    
    # 发送POST请求创建Action
    response = requests.post(
        f"{API_URL}/actions",
        json=ACTION_DATA,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        print("[SUCCESS] CTP可承诺量计算Action导入成功")
        print(f"   Action ID: {ACTION_DATA['id']}")
        print(f"   Action Name: {ACTION_DATA['name']}")
        print(f"   求解器类型: MIP (CBC)")
        print(f"   实现难度: 2星")
        return True
    else:
        print(f"[FAILED] 导入失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
        return False


if __name__ == "__main__":
    success = import_action()
    exit(0 if success else 1)
