"""
导入启发式详细排程Action到本体

Action: optimizeDetailedScheduleHeuristic
功能: 使用贪婪算法进行详细排程，秒级出结果
算法: 启发式（贪婪排程）
难度: ⭐⭐
优势: 超快速、支持大规模、灵活处理复杂约束
"""
import requests

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "optimize_detailed_schedule_heuristic",
    "api_name": "OptimizeDetailedScheduleHeuristic",
    "name": "详细排程优化（启发式）",
    "description": "使用贪婪算法进行快速排程，支持机台能力过滤，秒级出结果",
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
            "description": "排程规划时间范围，默认30天"
        },
        {
            "name": "consider_setup",
            "type": "boolean",
            "required": False,
            "description": "是否考虑换线时间，默认false"
        },
        {
            "name": "optimization_iterations",
            "type": "integer",
            "required": False,
            "description": "局部优化迭代次数，默认100（当前未使用）"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 启发式详细排程优化 - 贪婪算法（批量查询优化版）
import json
from datetime import datetime, timedelta
from my_ontology_sdk import OntologyClient

def execute_optimize_detailed_schedule_heuristic(parameters):
    """
    启发式详细排程优化 - 贪婪算法（批量查询优化版）
    
    算法流程:
    1. 批量加载所有数据（工单、工序、步骤、机台能力）
    2. 按工单优先级+工序顺序排序任务
    3. 依次分配每个任务到最早可用的合适机台
    4. 计算总工期（makespan）
    
    优化内容:
    1. 【关键】批量查询工单、工序、步骤、机台能力（避免N+1查询）
    2. 内存过滤机台能力，避免循环API调用
    """
    try:
        # 1. 解析参数
        work_order_ids = parameters.get("work_order_ids", [])
        planning_horizon_days = parameters.get("planning_horizon_days", 30)
        
        if not work_order_ids:
            return {"success": False, "error": "请提供工单ID列表"}
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # ============================================================
        # 【批量查询优化】核心数据加载阶段
        # 原方案: 循环中逐条查询工单、工序、步骤、机台能力（N次API调用）
        # 优化后: 批量查询所有相关数据（仅5次API调用）
        # ============================================================
        
        # 3. 批量查询工单
        work_orders = client.models.WorkOrder.find(work_order_id__in=work_order_ids)
        if not work_orders:
            return {"success": False, "error": "没有找到工单"}
        work_orders = list(work_orders)
        
        # 4. 批量查询工序
        # 原方案: for wo in work_orders: ops = client.models.WorkOrderOperation.find(work_order_id=wo.work_order_id)
        # 优化后: 一次性查询所有工单的工序
        wo_ids = [wo.work_order_id for wo in work_orders]
        all_ops = client.models.WorkOrderOperation.find(work_order_id__in=wo_ids)
        
        # 按工单ID分组工序，并排序
        ops_by_wo = {}
        for op in all_ops:
            if op.work_order_id not in ops_by_wo:
                ops_by_wo[op.work_order_id] = []
            ops_by_wo[op.work_order_id].append(op)
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
        # 原方案: 在构建任务列表时循环查询每个机台的能力
        # 优化后: 一次性查询所有机台能力，构建集合用于O(1)查找
        product_ids = list(set([wo.product_id for wo in work_orders]))
        all_caps = client.models.MachineCapability.find(
            product_id__in=product_ids,
            machine_id__in=[m.machine_id for m in all_machines]
        )
        capable_set = set([(cap.machine_id, cap.product_id) for cap in all_caps])
        
        # 8. 构建任务列表
        tasks = []
        for wo in work_orders:
            ops = ops_by_wo.get(wo.work_order_id, [])
            
            for seq, op in enumerate(ops):
                step = all_steps.get(op.step_id)
                if not step:
                    continue
                
                # 找到所需工序类型的机台
                wc_machines = [m for m in all_machines if m.work_center_id == step.machine_type_required]
                
                # 使用预构建的能力集合过滤（O(1)查找）
                valid_machine_ids = []
                for m in wc_machines:
                    if (m.machine_id, wo.product_id) in capable_set:
                        valid_machine_ids.append(m.machine_id)
                
                # 如果没有可用机台，跳过此任务
                if not valid_machine_ids:
                    continue
                
                # 计算加工时长（分钟）
                duration_minutes = int((step.standard_time_hours or 1) * 60)
                
                tasks.append({
                    "wo_id": wo.work_order_id,
                    "op_id": op.wo_op_id,
                    "step_id": op.step_id,
                    "seq": seq,
                    "product_id": wo.product_id,
                    "priority": wo.priority or 3,
                    "duration": duration_minutes,
                    "valid_machine_ids": valid_machine_ids
                })
        
        # 9. 贪婪排程
        schedule = _greedy_schedule(tasks, machines_dict)
        
        # 10. 构建结果
        start_time = datetime.now()
        schedule_result = []
        for task in schedule:
            schedule_result.append({
                "work_order_id": task["wo_id"],
                "operation_id": task["op_id"],
                "step_id": task["step_id"],
                "sequence_no": task["seq"],
                "machine_id": task["machine_id"],
                "start_time": (start_time + timedelta(minutes=task["start_time"])).isoformat(),
                "end_time": (start_time + timedelta(minutes=task["end_time"])).isoformat(),
                "duration_minutes": task["duration"]
            })
        
        # 按开始时间排序
        schedule_result.sort(key=lambda x: x["start_time"])
        
        # 计算总工期（makespan）
        makespan = max(t.get("end_time", 0) for t in schedule) if schedule else 0
        makespan_hours = makespan / 60
        
        return {
            "success": True,
            "message": f"启发式排程完成，总工期: {makespan_hours:.1f}小时",
            "result": {
                "makespan_hours": round(makespan_hours, 2),
                "makespan_days": round(makespan_hours / 24, 2),
                "total_tasks": len(schedule_result),
                "algorithm": "Greedy Scheduling",
                "schedule": schedule_result
            }
        }
        
    except Exception as e:
        import traceback
        return {"success": False, "error": f"执行失败: {str(e)} - {traceback.format_exc()}"}


def _greedy_schedule(tasks, machines_dict):
    """
    贪婪算法构造排程
    
    策略:
    1. 按工单优先级排序（高优先级先排）
    2. 同一工单内按工序顺序排
    3. 每道工序选择最早可用的合适机台
    
    时间复杂度: O(T × M) 其中T为任务数，M为平均可选机台数
    """
    # 按优先级、工单ID、工序顺序排序
    # 优先级数字越小优先级越高（1 > 3 > 5）
    sorted_tasks = sorted(tasks, key=lambda t: (t["priority"], t["wo_id"], t["seq"]))
    
    # 记录每个机台的可用时间（分钟）
    machine_available_time = {m: 0 for m in machines_dict.keys()}
    # 记录每个工单每道工序的完成时间
    wo_op_end_time = {}
    
    schedule = []
    
    for task in sorted_tasks:
        wo_id = task["wo_id"]
        seq = task["seq"]
        duration = task["duration"]
        
        # 计算最早开始时间（考虑工序顺序约束）
        earliest_start = 0
        if seq > 0:
            prev_key = (wo_id, seq - 1)
            if prev_key in wo_op_end_time:
                earliest_start = wo_op_end_time[prev_key]
        
        # 找到最佳机台（最早可用）
        best_machine_id = None
        best_start = float("inf")
        
        for mid in task["valid_machine_ids"]:
            # 机台可用时间 = max(工序最早开始时间, 机台当前可用时间)
            machine_start = max(earliest_start, machine_available_time.get(mid, 0))
            
            if machine_start < best_start:
                best_start = machine_start
                best_machine_id = mid
        
        # 如果找到合适机台，分配任务
        if best_machine_id:
            task["machine_id"] = best_machine_id
            task["start_time"] = best_start
            task["end_time"] = best_start + duration
            
            # 更新机台可用时间
            machine_available_time[best_machine_id] = task["end_time"]
            # 记录工序完成时间
            wo_op_end_time[(wo_id, seq)] = task["end_time"]
            
            schedule.append(task)
    
    return schedule


result = execute_optimize_detailed_schedule_heuristic(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入启发式详细排程优化Action")
    print("=" * 60)
    
    print(f"\nAPI URL: {API_URL}/actions")
    print(f"Action ID: {ACTION_DATA['id']}")
    print(f"Function code length: {len(ACTION_DATA.get('function_code', ''))} chars")
    
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
            print("\n[SUCCESS] 启发式详细排程优化Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   算法类型: 贪婪排程")
            print(f"   预计求解时间: < 1秒")
            print(f"   实现难度: 2星")
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
