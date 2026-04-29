"""
导入产能优化分配Action到本体

Action: optimizeCapacityAllocation  
功能: 多工单竞争有限产能时的最优分配
求解器: MIP (CBC)
难度: ⭐⭐⭐
"""
import requests

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "optimize_capacity_allocation",
    "api_name": "OptimizeCapacityAllocation",
    "name": "产能优化分配",
    "description": "在多个工单竞争有限产能时，优化分配以最大化按时交付率（优先级加权）",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "work_order",
    "parameters": [
        {
            "name": "work_order_ids",
            "type": "array",
            "required": True,
            "description": "要优化的工单ID列表"
        },
        {
            "name": "planning_horizon_days",
            "type": "integer",
            "required": False,
            "description": "排程规划时间范围，默认30天"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 产能优化分配函数实现 - 使用 Ontology SDK + OR-Tools
import json
from datetime import datetime, timedelta
from ortools.linear_solver import pywraplp
from my_ontology_sdk import OntologyClient

def execute_optimize_capacity_allocation(parameters):
    """
    产能优化分配 - MIP模型
    
    数学模型:
    - 决策变量: x[w,o,m,t]工单工序分配, C[w]是否按时交付
    - 目标函数: Maximize Σ(Priority[w] * C[w])
    - 约束条件:
      1. 按时交付: E[w,last] <= D[w] + M*(1-C[w])
      2. 工艺路线顺序: S[o(i+1)] >= E[o(i)]
      3. 机台产能: Σx[w,o,m,t] <= 1
      4. 工序必须调度: Σx[w,o,m,t] = 1
    """
    try:
        work_order_ids = parameters.get("work_order_ids", [])
        planning_horizon_days = parameters.get("planning_horizon_days", 30)
        
        if not work_order_ids:
            return {"success": False, "error": "请提供工单ID列表"}
        
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # 获取工单
        work_orders = []
        for wo_id in work_order_ids:
            wo = client.models.WorkOrder.get(wo_id)
            if wo:
                work_orders.append(wo)
        
        if not work_orders:
            return {"success": False, "error": "没有找到工单"}
        
        # 创建MIP求解器
        solver = pywraplp.Solver.CreateSolver('CBC')
        if not solver:
            return {"success": False, "error": "无法创建求解器"}
        
        # 准备数据
        time_slots = range(planning_horizon_days * 24)
        start_time = datetime.now()
        BIG_M = 10000
        
        # 获取所有工序
        all_operations = {}
        for wo in work_orders:
            ops = client.models.WorkOrderOperation.find(work_order_id=wo.work_order_id)
            all_operations[wo.work_order_id] = sorted(ops, key=lambda o: o.sequence_no or 0)
        
        # 获取机台
        machines = client.models.Machine.find(is_active=True)
        
        # 【新增】获取客户信息，用于优先级加权
        customer_weights = {}  # work_order_id -> customer_weight
        for wo in work_orders:
            customer_weight = 1.0
            # 尝试获取工单关联的订单
            if hasattr(wo, 'customer_order_id') and wo.customer_order_id:
                order = client.models.CustomerOrder.get(wo.customer_order_id)
                if order and hasattr(order, 'customer_id') and order.customer_id:
                    customer = client.models.Customer.get(order.customer_id)
                    if customer:
                        customer_level = customer.customer_level or "普通"
                        customer_weight = {
                            "VIP": 2.0,
                            "重要": 1.5,
                            "普通": 1.0
                        }.get(customer_level, 1.0)
            customer_weights[wo.work_order_id] = customer_weight
        
        # 创建决策变量
        x = {}
        S = {}
        E = {}
        C = {}
        
        for wo in work_orders:
            ops = all_operations[wo.work_order_id]
            priority_weight = _get_priority_weight(wo.priority)
            
            # 按时交付变量
            C[wo.work_order_id] = solver.IntVar(0, 1, f'C_{wo.work_order_id}')
            
            for op in ops:
                for m in machines:
                    for t in time_slots:
                        if _check_work_calendar(client, m.work_center_id, start_time + timedelta(hours=t)):
                            x[wo.work_order_id, op.wo_op_id, m.machine_id, t] = solver.IntVar(
                                0, 1, f'x_{wo.work_order_id}_{op.wo_op_id}_{m.machine_id}_{t}'
                            )
                
                S[op.wo_op_id] = solver.NumVar(0, planning_horizon_days*24, f'S_{op.wo_op_id}')
                E[op.wo_op_id] = solver.NumVar(0, planning_horizon_days*24, f'E_{op.wo_op_id}')
        
        # 添加约束
        
        # 约束1: 开始时间定义
        for wo in work_orders:
            for op in all_operations[wo.work_order_id]:
                valid_vars = [t * x[wo.work_order_id, op.wo_op_id, m.machine_id, t]
                             for m in machines for t in time_slots
                             if (wo.work_order_id, op.wo_op_id, m.machine_id, t) in x]
                if valid_vars:
                    solver.Add(S[op.wo_op_id] == sum(valid_vars))
        
        # 约束2: 结束时间
        for wo in work_orders:
            for op in all_operations[wo.work_order_id]:
                step = client.models.RouteStep.get(op.step_id)
                processing_time = step.standard_time_hours if step else 1
                solver.Add(E[op.wo_op_id] == S[op.wo_op_id] + processing_time)
        
        # 约束3: 工艺路线顺序
        for wo in work_orders:
            ops = all_operations[wo.work_order_id]
            for i in range(len(ops) - 1):
                solver.Add(S[ops[i+1].wo_op_id] >= E[ops[i].wo_op_id])
        
        # 约束4: 机台产能
        for m in machines:
            for t in time_slots:
                machine_vars = [x[wo.work_order_id, op.wo_op_id, m.machine_id, t]
                               for wo in work_orders
                               for op in all_operations[wo.work_order_id]
                               if (wo.work_order_id, op.wo_op_id, m.machine_id, t) in x]
                if machine_vars:
                    solver.Add(sum(machine_vars) <= 1)
        
        # 约束5: 工序必须调度
        for wo in work_orders:
            for op in all_operations[wo.work_order_id]:
                valid_vars = [x[wo.work_order_id, op.wo_op_id, m.machine_id, t]
                             for m in machines for t in time_slots
                             if (wo.work_order_id, op.wo_op_id, m.machine_id, t) in x]
                if valid_vars:
                    solver.Add(sum(valid_vars) == 1)
        
        # 约束6: 按时交付定义
        for wo in work_orders:
            ops = all_operations[wo.work_order_id]
            last_op = ops[-1]
            
            if wo.planned_completion_date:
                due_date = datetime.fromisoformat(wo.planned_completion_date) if isinstance(wo.planned_completion_date, str) else wo.planned_completion_date
                due_hours = (due_date - start_time).total_seconds() / 3600
            else:
                due_hours = planning_horizon_days * 24
            
            solver.Add(E[last_op.wo_op_id] <= due_hours + BIG_M * (1 - C[wo.work_order_id]))
        
        # 目标函数: 最大化按时交付的优先级加权和（客户等级 × 订单优先级）
        objective = solver.Objective()
        for wo in work_orders:
            # 订单优先级权重
            order_priority = wo.priority or 3
            order_priority_weight = {1: 10, 3: 5, 5: 1}.get(order_priority, 5)
            
            # 客户等级权重
            customer_weight = customer_weights.get(wo.work_order_id, 1.0)
            
            # 综合权重 = 客户等级权重 × 订单优先级权重
            total_weight = customer_weight * order_priority_weight
            
            objective.SetCoefficient(C[wo.work_order_id], total_weight)
        objective.SetMaximization()
        
        # 打印权重信息
        print(f"[产能优化] 工单数量: {len(work_orders)}")
        for wo in work_orders:
            order_priority = wo.priority or 3
            order_priority_weight = {1: 10, 3: 5, 5: 1}.get(order_priority, 5)
            customer_weight = customer_weights.get(wo.work_order_id, 1.0)
            total_weight = customer_weight * order_priority_weight
            print(f"  - 工单 {wo.work_order_id}: P{order_priority}({order_priority_weight}x) × 客户({customer_weight}x) = {total_weight}x")
        
        # 求解
        solver.SetTimeLimit(120000)  # 2分钟
        status = solver.Solve()
        
        # 解析结果
        if status == pywraplp.Solver.OPTIMAL:
            schedule = []
            on_time_count = 0
            
            for wo in work_orders:
                on_time = C[wo.work_order_id].solution_value() > 0.5
                if on_time:
                    on_time_count += 1
                
                for op in all_operations[wo.work_order_id]:
                    for m in machines:
                        for t in time_slots:
                            if (wo.work_order_id, op.wo_op_id, m.machine_id, t) in x:
                                if x[wo.work_order_id, op.wo_op_id, m.machine_id, t].solution_value() > 0.5:
                                    schedule.append({
                                        "work_order_id": wo.work_order_id,
                                        "operation_id": op.wo_op_id,
                                        "machine_id": m.machine_id,
                                        "start_hour": t,
                                        "start_time": (start_time + timedelta(hours=t)).isoformat()
                                    })
            
            result = {
                "total_work_orders": len(work_orders),
                "on_time_count": on_time_count,
                "on_time_rate": round(on_time_count / len(work_orders) * 100, 2),
                "customer_weight_applied": True,
                "work_order_priorities": [
                    {
                        "work_order_id": wo.work_order_id,
                        "order_priority": wo.priority or 3,
                        "customer_weight": customer_weights.get(wo.work_order_id, 1.0),
                        "total_weight": customer_weights.get(wo.work_order_id, 1.0) * {1: 10, 3: 5, 5: 1}.get(wo.priority or 3, 5)
                    }
                    for wo in work_orders
                ],
                "schedule": schedule
            }
            
            return {
                "success": True,
                "message": f"产能优化完成，按时交付率: {result['on_time_rate']}%",
                "result": result
            }
        else:
            return {"success": False, "error": "无可行解"}
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}

def _get_priority_weight(priority):
    """获取优先级权重"""
    weights = {1: 10, 3: 5, 5: 1}
    return weights.get(priority, 1)

def _check_work_calendar(client, work_center_id, target_time):
    """检查工作时间"""
    try:
        return target_time.weekday() < 6
    except:
        return True

result = execute_optimize_capacity_allocation(parameters)
'''
}

def import_action():
    print("=" * 60)
    print("开始导入产能优化分配Action")
    print("=" * 60)
    
    response = requests.post(f"{API_URL}/actions", json=ACTION_DATA, headers={"Content-Type": "application/json"})
    
    if response.status_code in [200, 201]:
        print("[SUCCESS] 产能优化分配Action导入成功")
        print(f"   Action ID: {ACTION_DATA['id']}")
        print(f"   求解器类型: MIP (CBC)")
        print(f"   实现难度: 3星")
        return True
    else:
        print(f"[FAILED] 导入失败: {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    success = import_action()
    exit(0 if success else 1)
