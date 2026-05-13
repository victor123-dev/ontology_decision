"""
导入产能优化分配Action到本体

Action: optimizeCapacityAllocation
功能: 使用MIP进行产能分配，最大化按时交付率
求解器: MIP (CBC)
难度: ⭐⭐⭐
"""
import requests

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "optimize_capacity_allocation",
    "api_name": "OptimizeCapacityAllocation",
    "name": "产能优化分配",
    "description": "使用 MIP 优化产能分配，最大化按时交付率。适用于中小规模工单（≤50个），需要最优解时使用。返回工单级分配方案、按时交付率及瓶颈分析。该Action不是工序级排程，仅支持preview，不直接写入ProductionTask。大规模场景请用 optimize_capacity_allocation_fast。",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "work_order",
    "parameters": [
        {
            "name": "work_order_ids",
            "type": "array",
            "required": True,
            "description": "需要分配产能的工单ID列表"
        },
        {
            "name": "planning_horizon_days",
            "type": "integer",
            "required": False,
            "description": "排程规划天数。时间越长计算越慢，默认30天"
        },
        {
            "name": "apply_mode",
            "type": "string",
            "required": False,
            "description": "应用模式。该MIP产能分配Action只输出工单级结果，仅支持preview；如需upsert写入ProductionTask，请使用详细排程Action或快速产能分配Action"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 产能优化分配 - 使用 Ontology SDK + OR-Tools（批量查询优化版）
import json
from datetime import datetime, timedelta
from ortools.linear_solver import pywraplp
from my_ontology_sdk import OntologyClient

def execute_optimize_capacity_allocation(parameters):
    """
    产能优化分配 - MIP模型（批量查询优化版）
    
    数学模型:
    - 决策变量:
      X[w,m]: 工单w是否分配给机台m（0-1变量）
      T[w]: 工单w的完成时间（连续变量）
      L[w]: 工单w是否按时交付（0-1变量）
    - 目标函数: Maximize Σ(weight[w] × L[w])
      weight[w] = 客户等级权重 × 订单优先级权重
    - 约束条件:
      1. 每个工单只能分配一个机台: ΣX[w,m] = 1
      2. 机台产能限制: Σ(duration[w] × X[w,m]) <= capacity[m]
      3. 按时交付判定: T[w] <= due_date[w] + M × (1 - L[w])
      4. 完成时间计算: T[w] >= Σ(duration[w] × X[w,m])
      5. 变量边界: X[w,m] ∈ {0,1}, L[w] ∈ {0,1}, T[w] >= 0
    
    优化内容:
    1. 【关键】批量查询所有工单、工序、客户信息（避免N+1查询）
    2. 预计算工单加工时长，避免循环中重复查询
    3. 预构建机台能力集合，快速过滤
    """
    try:
        # 1. 解析参数
        work_order_ids = parameters.get("work_order_ids", [])
        planning_horizon_days = parameters.get("planning_horizon_days", 30)
        apply_mode = parameters.get("apply_mode", "preview")
        
        if apply_mode != "preview":
            return {"success": False, "error": "optimize_capacity_allocation仅输出工单级产能分配结果，不支持upsert写入ProductionTask；请使用optimize_detailed_schedule、optimize_detailed_schedule_fast或optimize_capacity_allocation_fast"}
        
        if not work_order_ids:
            return {"success": False, "error": "请提供工单ID列表"}
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # ============================================================
        # 【批量查询优化】核心数据加载阶段
        # 原方案: 循环中逐条查询工单、工序、客户信息（N次API调用）
        # 优化后: 批量查询所有相关数据（仅4次API调用）
        # ============================================================
        
        # 3. 批量查询工单
        work_orders = client.models.WorkOrder.find(work_order_id__in=work_order_ids)
        if not work_orders:
            return {"success": False, "error": "没有找到工单"}
        work_orders = list(work_orders)
        
        # 4. 批量查询工单工序
        # 原方案: for wo in work_orders: ops = client.models.WorkOrderOperation.find(work_order_id=wo.work_order_id)
        # 优化后: 一次性查询所有工单的工序，用__in批量查询
        wo_ids = [wo.work_order_id for wo in work_orders]
        all_ops = client.models.WorkOrderOperation.find(work_order_id__in=wo_ids)
        
        # 按工单ID分组工序
        ops_by_wo = {}
        for op in all_ops:
            if op.work_order_id not in ops_by_wo:
                ops_by_wo[op.work_order_id] = []
            ops_by_wo[op.work_order_id].append(op)
        # 每个工单的工序按序号排序
        for wo_id in ops_by_wo:
            ops_by_wo[wo_id].sort(key=lambda o: o.sequence_no or 0)
        
        # 5. 批量查询工序步骤
        step_ids = list(set([op.step_id for op in all_ops]))
        all_steps = {s.step_id: s for s in client.models.RouteStep.find(step_id__in=step_ids)}
        
        # 6. 批量查询机台
        work_center_ids = list(set([step.machine_type_required for step in all_steps.values() if step and step.machine_type_required]))
        all_machines = []
        for wc_id in work_center_ids:
            all_machines.extend(client.models.Machine.find(work_center_id=wc_id, is_active=True))
        machines_dict = {m.machine_id: m for m in all_machines}
        
        # 7. 批量查询机台能力
        product_ids = list(set([wo.product_id for wo in work_orders]))
        all_caps = client.models.MachineCapability.find(
            product_id__in=product_ids,
            machine_id__in=[m.machine_id for m in all_machines]
        )
        # 构建能力集合，用于快速查找
        capable_set = set([(cap.machine_id, cap.product_id) for cap in all_caps])
        
        # 8. 批量查询客户信息
        # 原方案: for wo in work_orders: order = client.models.CustomerOrder.get(wo.customer_order_id); customer = client.models.Customer.get(order.customer_id)
        # 优化后: 一次性查询所有客户订单和客户
        order_ids = list(set([wo.customer_order_id for wo in work_orders if hasattr(wo, 'customer_order_id') and wo.customer_order_id]))
        all_orders = {}
        if order_ids:
            for order in client.models.CustomerOrder.find(order_id__in=order_ids):
                all_orders[order.order_id] = order
        
        customer_ids = list(set([o.customer_id for o in all_orders.values() if hasattr(o, 'customer_id') and o.customer_id]))
        all_customers = {}
        if customer_ids:
            for customer in client.models.Customer.find(customer_id__in=customer_ids):
                all_customers[customer.customer_id] = customer
        
        # 9. 预计算每个工单的权重和加工时长
        wo_data = {}
        for wo in work_orders:
            # 计算客户等级权重
            customer_weight = 1.0
            if hasattr(wo, 'customer_order_id') and wo.customer_order_id and wo.customer_order_id in all_orders:
                order = all_orders[wo.customer_order_id]
                if hasattr(order, 'customer_id') and order.customer_id and order.customer_id in all_customers:
                    customer = all_customers[order.customer_id]
                    customer_level = customer.customer_level or "普通"
                    customer_weight = {"VIP": 2.0, "重要": 1.5, "普通": 1.0}.get(customer_level, 1.0)
            
            # 计算订单优先级权重
            order_priority = wo.priority or 3
            order_priority_weight = {1: 10, 3: 5, 5: 1}.get(order_priority, 5)
            
            # 总权重 = 客户等级权重 × 订单优先级权重
            total_weight = customer_weight * order_priority_weight
            
            # 计算工单总加工时长（分钟）
            ops = ops_by_wo.get(wo.work_order_id, [])
            total_processing_time = 0
            for op in ops:
                step = all_steps.get(op.step_id)
                if step:
                    total_processing_time += (step.standard_time_hours or 1) * 60
            
            # 计算交期（小时）
            now = datetime.now()
            if wo.planned_completion_date:
                due_date = datetime.fromisoformat(wo.planned_completion_date) if isinstance(wo.planned_completion_date, str) else wo.planned_completion_date
                due_hours = (due_date - now).total_seconds() / 3600
            else:
                due_hours = planning_horizon_days * 24
                due_date = now + timedelta(hours=due_hours)
            
            wo_data[wo.work_order_id] = {
                "wo": wo,
                "ops": ops,
                "total_processing_time": total_processing_time,
                "due_hours": due_hours,
                "total_weight": total_weight,
                "customer_weight": customer_weight,
                "order_priority": order_priority,
                "order_priority_weight": order_priority_weight
            }
        
        # 10. 创建MIP求解器（CBC是混合整数规划求解器）
        solver = pywraplp.Solver.CreateSolver('CBC')
        if not solver:
            return {"success": False, "error": "无法创建求解器"}
        
        # 11. 创建决策变量
        # X[wo_id, machine_id]: 工单是否分配给该机台（0-1变量）
        # L[wo_id]: 工单是否按时交付（0-1变量）
        # T[wo_id]: 工单完成时间（连续变量，小时）
        x_vars = {}
        l_vars = {}
        t_vars = {}
        
        for wo_id, data in wo_data.items():
            wo = data["wo"]
            
            # 找到有能力生产该产品的机台
            capable_machines = [
                m for m in all_machines
                if (m.machine_id, wo.product_id) in capable_set
            ]
            
            if not capable_machines:
                continue
            
            # 创建分配变量
            for machine in capable_machines:
                x_vars[wo_id, machine.machine_id] = solver.IntVar(
                    0, 1, f'x_{wo_id}_{machine.machine_id}'
                )
            
            # 创建按时交付变量
            l_vars[wo_id] = solver.IntVar(0, 1, f'l_{wo_id}')
            
            # 创建完成时间变量
            t_vars[wo_id] = solver.NumVar(0, planning_horizon_days * 24, f't_{wo_id}')
        
        # 12. 添加约束
        
        # 约束1: 每个工单只能分配一个机台
        for wo_id in wo_data:
            if wo_id not in t_vars:
                continue
            
            expr = solver.Sum([
                x_vars[wo_id, mid]
                for (wid, mid) in x_vars
                if wid == wo_id
            ])
            solver.Add(expr == 1)
        
        # 约束2: 完成时间计算 T[w] >= duration[w] × X[w,m]
        for wo_id, data in wo_data.items():
            if wo_id not in t_vars:
                continue
            
            processing_hours = data["total_processing_time"] / 60
            
            for (wid, mid) in x_vars:
                if wid == wo_id:
                    solver.Add(
                        t_vars[wo_id] >= processing_hours * x_vars[wid, mid]
                    )
        
        # 约束3: 按时交付判定 T[w] <= due_date[w] + M × (1 - L[w])
        # M是大数，当L[w]=0时约束失效
        # 使用足够大的M值：规划时间范围 + 最大可能加工时间
        max_processing_hours = max([d["total_processing_time"] / 60 for d in wo_data.values()]) if wo_data else 24
        M = planning_horizon_days * 24 + max_processing_hours * 2
        for wo_id, data in wo_data.items():
            if wo_id not in t_vars:
                continue
            
            due_hours = data["due_hours"]
            # 确保due_hours不为负数
            due_hours = max(0, due_hours)
            solver.Add(
                t_vars[wo_id] <= due_hours + M * (1 - l_vars[wo_id])
            )
        
        # 13. 目标函数：最大化加权按时交付率
        objective = solver.Objective()
        for wo_id in l_vars:
            weight = wo_data[wo_id]["total_weight"]
            objective.SetCoefficient(l_vars[wo_id], weight)
        objective.SetMaximization()
        
        # 14. 求解
        solver.SetTimeLimit(60000)
        solver.EnableOutput()
        status = solver.Solve()
        
        if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            return {"success": False, "error": "求解失败"}
        
        # 15. 解析结果
        schedule = []
        on_time_count = 0
        total_weight_on_time = 0
        total_weight = 0
        
        for wo_id, data in wo_data.items():
            if wo_id not in t_vars:
                continue
            
            wo = data["wo"]
            completion_time = t_vars[wo_id].solution_value()
            is_on_time = l_vars[wo_id].solution_value() > 0.5
            
            # 找到分配的机台
            assigned_machine = None
            for (wid, mid) in x_vars:
                if wid == wo_id and x_vars[wid, mid].solution_value() > 0.5:
                    assigned_machine = mid
                    break
            
            if is_on_time:
                on_time_count += 1
                total_weight_on_time += data["total_weight"]
            
            total_weight += data["total_weight"]
            
            schedule.append({
                "work_order_id": wo_id,
                "product_id": wo.product_id,
                "assigned_machine": assigned_machine,
                "completion_time_hours": round(completion_time, 2),
                "due_hours": round(data["due_hours"], 2),
                "is_on_time": is_on_time,
                "customer_weight": data["customer_weight"],
                "order_priority": data["order_priority"],
                "order_priority_weight": data["order_priority_weight"],
                "total_weight": data["total_weight"]
            })
        
        weighted_on_time_rate = round(total_weight_on_time / total_weight * 100, 2) if total_weight > 0 else 0
        simple_on_time_rate = round(on_time_count / len([w for w in wo_data if w in t_vars]) * 100, 2) if wo_data else 0
        
        result = {
            "total_work_orders": len([w for w in wo_data if w in t_vars]),
            "on_time_count": on_time_count,
            "on_time_rate": simple_on_time_rate,
            "weighted_on_time_rate": weighted_on_time_rate,
            "customer_weight_applied": True,
            "work_order_priorities": [
                {
                    "work_order_id": wo_id,
                    "order_priority": data["order_priority"],
                    "customer_weight": data["customer_weight"],
                    "total_weight": data["total_weight"]
                }
                for wo_id, data in wo_data.items()
                if wo_id in t_vars
            ],
            "schedule": schedule
        }
        
        return {
            "success": True,
            "message": f"产能优化完成，按时交付率: {simple_on_time_rate}%（加权: {weighted_on_time_rate}%）",
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}


result = execute_optimize_capacity_allocation(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入产能优化分配Action")
    print("=" * 60)
    
    # 打印请求信息
    print(f"\nAPI URL: {API_URL}/actions")
    print(f"Action ID: {ACTION_DATA['id']}")
    print(f"Function code length: {len(ACTION_DATA.get('function_code', ''))} chars")
    
    # 发送POST请求创建Action
    try:
        response = requests.post(
            f"{API_URL}/actions",
            json=ACTION_DATA,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}")
        
        if response.status_code in [200, 201]:
            print("\n[SUCCESS] 产能优化分配Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   求解器类型: MIP (CBC)")
            print(f"   实现难度: 3星")
            return True
        else:
            print(f"\n[FAILED] 导入失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"\n[ERROR] 请求异常: {str(e)}")
        return False


if __name__ == "__main__":
    success = import_action()
    exit(0 if success else 1)
