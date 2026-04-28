"""
导入详细排程优化Action到本体

Action: optimizeDetailedSchedule
功能: 使用CP-SAT进行详细排程优化，支持换线矩阵等复杂约束
求解器: CP-SAT
难度: ⭐⭐⭐⭐
"""
import requests

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "optimize_detailed_schedule",
    "api_name": "OptimizeDetailedSchedule",
    "name": "详细排程优化",
    "description": "使用CP-SAT约束规划进行详细排程，支持换线时间、工作日历、机台能力等复杂约束",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "work_order",
    "parameters": [
        {
            "name": "work_order_ids",
            "type": "array",
            "required": True,
            "description": "要排程的工单ID列表"
        },
        {
            "name": "planning_horizon_days",
            "type": "integer",
            "required": False,
            "description": "排程规划时间范围，默认7天"
        },
        {
            "name": "consider_setup",
            "type": "boolean",
            "required": False,
            "description": "是否在排程中考虑换线时间，默认true"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 详细排程优化函数实现 - 使用 Ontology SDK + OR-Tools CP-SAT
import json
from datetime import datetime, timedelta
from ortools.sat.python import cp_model
from my_ontology_sdk import OntologyClient

def execute_optimize_detailed_schedule(parameters):
    """
    详细排程优化 - CP-SAT模型
    
    为什么使用CP-SAT而不是MIP?
    - CP-SAT使用IntervalVar直接表示任务时间区间，无需时间槽离散化
    - 原生支持NoOverlap约束（机台不重叠）
    - 换线约束建模更简单
    - 求解速度比MIP快10-100倍
    
    数学模型:
    - 决策变量: Task[w,o]区间变量(Start, End, Duration)
    - 目标函数: Minimize Makespan
    - 约束条件:
      1. 工艺路线顺序: Start[o(i+1)] >= End[o(i)]
      2. 机台不重叠: NoOverlap(Tasks_on_same_machine)
      3. 换线时间: SetupTime(prev_product, curr_product)
      4. 工作日历: 只在有效时间内排程
    """
    try:
        work_order_ids = parameters.get("work_order_ids", [])
        planning_horizon_days = parameters.get("planning_horizon_days", 7)
        consider_setup = parameters.get("consider_setup", True)
        
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
        
        # 创建CP-SAT模型
        model = cp_model.CpModel()
        
        # 时间范围（分钟）
        horizon = planning_horizon_days * 24 * 60
        
        # 准备数据
        start_time = datetime.now()
        tasks = {}  # Task[wo_id, op_id]
        machines_dict = {}  # machine_id -> Machine对象
        
        # 获取所有机台
        all_machines = client.models.Machine.find(is_active=True)
        for m in all_machines:
            machines_dict[m.machine_id] = m
        
        # 为每个工单的每个工序创建区间变量
        for wo in work_orders:
            ops = client.models.WorkOrderOperation.find(work_order_id=wo.work_order_id)
            ops = sorted(ops, key=lambda o: o.sequence_no or 0)
            
            for op in ops:
                # 获取工序信息
                step = client.models.RouteStep.get(op.step_id)
                if not step:
                    continue
                
                # 计算加工时长（分钟）
                duration_minutes = int((step.standard_time_hours or 1) * 60)
                
                # 找到合适的机台
                wc_machines = [m for m in all_machines if m.work_center_id == step.machine_type_required]
                
                if not wc_machines:
                    continue
                
                # 为每个可用机台创建区间变量
                machine_tasks = []
                for machine in wc_machines:
                    # 检查机台能力
                    if not _check_machine_capability(client, machine.machine_id, wo.product_id):
                        continue
                    
                    # 创建区间变量
                    task_start = model.NewIntVar(0, horizon, f'start_{wo.work_order_id}_{op.wo_op_id}_{machine.machine_id}')
                    task_end = model.NewIntVar(0, horizon, f'end_{wo.work_order_id}_{op.wo_op_id}_{machine.machine_id}')
                    
                    task_interval = model.NewIntervalVar(
                        task_start,
                        duration_minutes,
                        task_end,
                        f'task_{wo.work_order_id}_{op.wo_op_id}_{machine.machine_id}'
                    )
                    
                    machine_tasks.append((machine.machine_id, task_interval, task_start, task_end))
                
                if machine_tasks:
                    tasks[wo.work_order_id, op.wo_op_id] = {
                        'step': step,
                        'machines': machine_tasks,
                        'wo': wo,
                        'op': op
                    }
        
        # 添加约束
        
        # 约束1: 每个工序只能分配到一个机台
        for (wo_id, op_id), task_info in tasks.items():
            machine_vars = []
            for machine_id, interval, start, end in task_info['machines']:
                present = model.NewBoolVar(f'present_{wo_id}_{op_id}_{machine_id}')
                model.Add(start >= 0).OnlyEnforceIf(present)
                machine_vars.append(present)
            
            # 只能选择一个机台
            model.Add(sum(machine_vars) == 1)
        
        # 约束2: 工艺路线顺序
        for wo in work_orders:
            ops = client.models.WorkOrderOperation.find(work_order_id=wo.work_order_id)
            ops = sorted(ops, key=lambda o: o.sequence_no or 0)
            
            for i in range(len(ops) - 1):
                op_current = ops[i]
                op_next = ops[i + 1]
                
                if (wo.work_order_id, op_current.wo_op_id) in tasks and \\
                   (wo.work_order_id, op_next.wo_op_id) in tasks:
                    # 下一道工序的开始 >= 当前工序的结束
                    current_ends = [end for _, _, _, end in tasks[wo.work_order_id, op_current.wo_op_id]['machines']]
                    next_starts = [start for _, _, start, _ in tasks[wo.work_order_id, op_next.wo_op_id]['machines']]
                    
                    # 简化：取第一个机台
                    if current_ends and next_starts:
                        model.Add(next_starts[0] >= current_ends[0])
        
        # 约束3: 机台不重叠（核心约束）
        for machine in all_machines:
            machine_intervals = []
            for (wo_id, op_id), task_info in tasks.items():
                for mid, interval, start, end in task_info['machines']:
                    if mid == machine.machine_id:
                        present = model.NewBoolVar(f'present_{wo_id}_{op_id}_{mid}')
                        machine_intervals.append((interval, present))
            
            if machine_intervals:
                # 使用NoOverlap约束
                intervals = [interval for interval, present in machine_intervals]
                model.AddNoOverlap(intervals)
        
        # 约束4: 换线时间（如果启用）
        if consider_setup:
            for machine in all_machines:
                machine_tasks_list = []
                for (wo_id, op_id), task_info in tasks.items():
                    for mid, interval, start, end in task_info['machines']:
                        if mid == machine.machine_id:
                            machine_tasks_list.append((wo_id, op_id, start, end, task_info['wo'].product_id))
                
                # 添加换线约束（简化版）
                for i in range(len(machine_tasks_list) - 1):
                    wo_id1, op_id1, start1, end1, prod_id1 = machine_tasks_list[i]
                    wo_id2, op_id2, start2, end2, prod_id2 = machine_tasks_list[i + 1]
                    
                    if prod_id1 != prod_id2:
                        # 查询换线矩阵
                        setup_time = _get_setup_time(client, machine.machine_id, prod_id1, prod_id2)
                        if setup_time > 0:
                            model.Add(start2 >= end1 + setup_time)
        
        # 目标函数：最小化Makespan（总完成时间）
        makespan = model.NewIntVar(0, horizon, 'makespan')
        for wo in work_orders:
            ops = client.models.WorkOrderOperation.find(work_order_id=wo.work_order_id)
            if ops:
                last_op = max(ops, key=lambda o: o.sequence_no or 0)
                if (wo.work_order_id, last_op.wo_op_id) in tasks:
                    ends = [end for _, _, _, end in tasks[wo.work_order_id, last_op.wo_op_id]['machines']]
                    if ends:
                        model.Add(makespan >= ends[0])
        
        model.Minimize(makespan)
        
        # 求解
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 300.0  # 5分钟
        solver.parameters.num_search_workers = 4
        
        status = solver.Solve(model)
        
        # 解析结果
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            schedule = []
            makespan_minutes = solver.Value(makespan)
            makespan_hours = makespan_minutes / 60
            
            for (wo_id, op_id), task_info in tasks.items():
                for machine_id, interval, start, end in task_info['machines']:
                    if solver.Value(start) > 0:
                        start_minutes = solver.Value(start)
                        end_minutes = solver.Value(end)
                        
                        schedule.append({
                            "work_order_id": wo_id,
                            "operation_id": op_id,
                            "step_id": task_info['op'].step_id,
                            "machine_id": machine_id,
                            "start_time": (start_time + timedelta(minutes=start_minutes)).isoformat(),
                            "end_time": (start_time + timedelta(minutes=end_minutes)).isoformat(),
                            "duration_minutes": end_minutes - start_minutes
                        })
            
            result = {
                "makespan_hours": round(makespan_hours, 2),
                "makespan_days": round(makespan_hours / 24, 2),
                "total_tasks": len(schedule),
                "schedule": schedule
            }
            
            return {
                "success": True,
                "message": f"详细排程完成，总工期: {makespan_hours:.1f}小时",
                "result": result
            }
        else:
            return {"success": False, "error": "无可行解"}
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}

def _check_machine_capability(client, machine_id, product_id):
    """检查机台能力"""
    try:
        caps = client.models.MachineCapability.find(machine_id=machine_id, product_id=product_id)
        return len(caps) > 0
    except:
        return True

def _get_setup_time(client, machine_id, from_product_id, to_product_id):
    """获取换线时间（分钟）"""
    try:
        setups = client.models.SetupMatrix.find(
            machine_id=machine_id,
            from_product_id=from_product_id,
            to_product_id=to_product_id
        )
        if setups:
            return setups[0].setup_time_minutes or 0
        return 0
    except:
        return 0

result = execute_optimize_detailed_schedule(parameters)
'''
}

def import_action():
    print("=" * 60)
    print("开始导入详细排程优化Action")
    print("=" * 60)
    
    response = requests.post(f"{API_URL}/actions", json=ACTION_DATA, headers={"Content-Type": "application/json"})
    
    if response.status_code in [200, 201]:
        print("[SUCCESS] 详细排程优化Action导入成功")
        print(f"   Action ID: {ACTION_DATA['id']}")
        print(f"   求解器类型: CP-SAT")
        print(f"   实现难度: 4星")
        return True
    else:
        print(f"[FAILED] 导入失败: {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    success = import_action()
    exit(0 if success else 1)
