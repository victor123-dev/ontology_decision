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
    "id": "optimize_detailed_schedule_fast",
    "api_name": "OptimizeDetailedScheduleFast",
    "name": "详细排程优化（快速）",
    "description": "快速详细排程（贪婪算法），秒级出结果。适用于大规模工单，不保证最优但速度快。支持preview预览和upsert写入本体实例数据。小规模追求最优解请用 optimize_detailed_schedule。",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "work_order",
    "parameters": [
        {
            "name": "work_order_ids",
            "type": "array",
            "required": True,
            "description": "需要排程的工单ID列表"
        },
        {
            "name": "planning_horizon_days",
            "type": "integer",
            "required": False,
            "description": "排程规划天数，默认30天"
        },
        {
            "name": "consider_setup",
            "type": "boolean",
            "required": False,
            "description": "是否考虑换线时间。默认false。设为true会更真实但略慢"
        },
        {
            "name": "apply_mode",
            "type": "string",
            "required": False,
            "description": "排程结果应用模式：preview仅返回排程结果；upsert将结果写入本体实例，已有可修改ProductionTask则更新，没有则创建。默认preview"
        },
        {
            "name": "schedule_note",
            "type": "string",
            "required": False,
            "description": "写入ProductionTask.note的备注，默认'快速详细排程优化Action-自动写入'"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 启发式详细排程优化 - 贪婪算法（批量查询优化版）
import json
from datetime import datetime, timedelta
from my_ontology_sdk import OntologyClient

UPDATABLE_TASK_STATUS = {"已排程", "待执行", "已延期"}
UPDATABLE_OPERATION_STATUS = {"待开工", "已排程"}
DEFAULT_SCHEDULE_NOTE = "快速详细排程优化Action-自动写入"


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
        apply_mode = parameters.get("apply_mode", "preview")
        schedule_note = parameters.get("schedule_note", DEFAULT_SCHEDULE_NOTE)
        
        if not work_order_ids:
            return {"success": False, "error": "请提供工单ID列表"}
        
        if apply_mode not in {"preview", "upsert"}:
            return {"success": False, "error": "apply_mode仅支持preview或upsert"}
        
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
        wo_lookup = {wo.work_order_id: wo for wo in work_orders}
        
        # 4. 批量查询工序
        # 原方案: for wo in work_orders: ops = client.models.WorkOrderOperation.find(work_order_id=wo.work_order_id)
        # 优化后: 一次性查询所有工单的工序
        wo_ids = [wo.work_order_id for wo in work_orders]
        all_ops = list(client.models.WorkOrderOperation.find(work_order_id__in=wo_ids))
        op_lookup = {op.wo_op_id: op for op in all_ops}
        
        # 按工单ID分组工序，并排序
        ops_by_wo = {}
        for op in all_ops:
            if op.work_order_id not in ops_by_wo:
                ops_by_wo[op.work_order_id] = []
            ops_by_wo[op.work_order_id].append(op)
        for wo_id in ops_by_wo:
            ops_by_wo[wo_id].sort(key=lambda o: o.sequence_no or 0)
        
        # 5. 批量查询工序步骤
        step_ids = list(set([op.step_id for op in all_ops if op.step_id]))
        all_steps = {s.step_id: s for s in client.models.RouteStep.find(step_id__in=step_ids)} if step_ids else {}
        
        # 6. 批量查询机台
        work_center_ids = list(set([step.machine_type_required for step in all_steps.values() if step and step.machine_type_required]))
        all_machines = []
        for wc_id in work_center_ids:
            all_machines.extend(client.models.Machine.find(work_center_id=wc_id, is_active=True))
        machines_dict = {m.machine_id: m for m in all_machines}
        
        # 7. 批量查询机台能力
        # 原方案: 在构建任务列表时循环查询每个机台的能力
        # 优化后: 一次性查询所有机台能力，构建集合用于O(1)查找
        product_ids = list(set([wo.product_id for wo in work_orders if wo.product_id]))
        all_caps = client.models.MachineCapability.find(
            product_id__in=product_ids,
            machine_id__in=[m.machine_id for m in all_machines]
        ) if product_ids and all_machines else []
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
                std_time = step.standard_time_hours or 1.0
                wait_time = getattr(step, 'wait_time_hours', 0.0) or 0.0
                transport_time = getattr(step, 'transport_time_hours', 0.0) or 0.0
                queue_time = 0.5  # 工序间排队时间
                
                # 工序总时长 = 加工时间 + 等待时间 + 转运时间
                duration_minutes = max(1, int((std_time + wait_time + transport_time) * 60))
                planned_quantity = getattr(op, 'required_input_qty', None) or getattr(wo, 'planned_quantity', 0) or 0
                
                tasks.append({
                    "wo_id": wo.work_order_id,
                    "op_id": op.wo_op_id,
                    "step_id": op.step_id,
                    "seq": seq,
                    "sequence_no": op.sequence_no or seq + 1,
                    "product_id": wo.product_id,
                    "priority": wo.priority or 3,
                    "duration": duration_minutes,
                    "planned_quantity": planned_quantity,
                    "wait_time_minutes": int((wait_time + transport_time) * 60),
                    "valid_machine_ids": valid_machine_ids
                })
        
        # 9. 贪婪排程
        schedule = _greedy_schedule(tasks, machines_dict)
        
        # 10. 构建结果
        # TODO start_time = datetime.now()
        start_time = datetime(2026, 4, 26)
        schedule_result = []
        for task in schedule:
            start_dt = start_time + timedelta(minutes=task["start_time"])
            end_dt = start_time + timedelta(minutes=task["end_time"])
            schedule_result.append({
                "work_order_id": task["wo_id"],
                "operation_id": task["op_id"],
                "step_id": task["step_id"],
                "sequence_no": task["sequence_no"],
                "machine_id": task["machine_id"],
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "duration_minutes": task["duration"],
                "planned_quantity": task["planned_quantity"],
                "wait_time_minutes": task.get("wait_time_minutes", 0)
            })
        
        # 按开始时间排序
        schedule_result.sort(key=lambda x: x["start_time"])
        
        # 计算总工期（makespan）
        makespan = max(t.get("end_time", 0) for t in schedule) if schedule else 0
        makespan_hours = makespan / 60
        apply_result = None
        
        if apply_mode == "upsert":
            apply_result = _upsert_schedule_to_ontology(
                client,
                schedule_result,
                op_lookup,
                wo_lookup,
                schedule_note
            )
        
        # 防上下文膨胀：只返回前50条任务详情
        max_schedule = 50
        schedule_returned = schedule_result[:max_schedule]
        truncated_count = max(0, len(schedule_result) - max_schedule)
        message_suffix = "，并已应用到本体实例" if apply_mode == "upsert" else ""
        
        return {
            "success": True,
            "message": f"快速排程完成{message_suffix}，总工期: {makespan_hours:.1f}小时，共{len(schedule_result)}个任务",
            "result": {
                "makespan_hours": round(makespan_hours, 2),
                "makespan_days": round(makespan_hours / 24, 2),
                "total_tasks": len(schedule_result),
                "schedule": schedule_returned,
                "truncated_count": truncated_count,
                "algorithm": "Greedy Scheduling",
                "apply_mode": apply_mode,
                "applied": apply_mode == "upsert",
                "apply_result": apply_result,
                "note": "仅返回前50条任务详情" if truncated_count > 0 else None
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
        
        # 计算最早开始时间（考虑工序顺序约束 + 排队时间）
        earliest_start = 0
        if seq > 0:
            prev_key = (wo_id, seq - 1)
            if prev_key in wo_op_end_time:
                # 下一道工序 = 上一道工序结束时间 + 排队时间
                earliest_start = wo_op_end_time[prev_key] + int(queue_time * 60)
        
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


def _upsert_schedule_to_ontology(client, schedule, op_lookup, wo_lookup, schedule_note):
    operation_ids = [item["operation_id"] for item in schedule]
    existing_tasks_by_op = _load_existing_tasks_by_operation(client, operation_ids)
    created_tasks = []
    updated_tasks = []
    updated_operations = []
    updated_work_orders = []
    skipped_locked = []
    failed_items = []
    wo_windows = {}
    
    for index, item in enumerate(schedule, 1):
        op_id = item["operation_id"]
        try:
            op = op_lookup.get(op_id)
            if not op:
                failed_items.append({"operation_id": op_id, "error": "找不到对应工序对象"})
                continue
            
            start_dt = datetime.fromisoformat(item["start_time"])
            end_dt = datetime.fromisoformat(item["end_time"])
            shift_id, is_night = _get_shift_info(start_dt)
            existing_task = existing_tasks_by_op.get(op_id)
            task_payload = _build_task_payload(item, shift_id, is_night, schedule_note)
            
            if existing_task:
                if _is_task_updatable(existing_task):
                    existing_task.update(**task_payload)
                    updated_tasks.append(getattr(existing_task, 'task_id', None))
                else:
                    skipped_locked.append({
                        "operation_id": op_id,
                        "task_id": getattr(existing_task, 'task_id', None),
                        "status": getattr(existing_task, 'status', None),
                        "reason": "已有任务已开始、已完成或不可修改"
                    })
                    continue
            else:
                task_id = _generate_task_id(index)
                payload = {"task_id": task_id, **task_payload}
                client.models.ProductionTask.create(payload)
                created_tasks.append(task_id)
            
            if _is_operation_updatable(op):
                op.update(
                    assigned_machine_id=item["machine_id"],
                    status="已排程",
                    planned_start=item["start_time"],
                    planned_end=item["end_time"]
                )
                updated_operations.append(op_id)
            
            wo_id = item["work_order_id"]
            current_window = wo_windows.get(wo_id)
            if current_window:
                wo_windows[wo_id] = (min(current_window[0], start_dt), max(current_window[1], end_dt))
            else:
                wo_windows[wo_id] = (start_dt, end_dt)
        except Exception as e:
            failed_items.append({"operation_id": op_id, "error": str(e)})
    
    for wo_id, window in wo_windows.items():
        try:
            wo = wo_lookup.get(wo_id)
            if wo:
                wo.update(
                    planned_start_date=window[0].isoformat(),
                    planned_completion_date=window[1].isoformat()
                )
                updated_work_orders.append(wo_id)
        except Exception as e:
            failed_items.append({"work_order_id": wo_id, "error": str(e)})
    
    return {
        "created_tasks": created_tasks,
        "updated_tasks": updated_tasks,
        "updated_operations": updated_operations,
        "updated_work_orders": updated_work_orders,
        "skipped_locked": skipped_locked,
        "failed_items": failed_items
    }


def _load_existing_tasks_by_operation(client, operation_ids):
    if not operation_ids:
        return {}
    existing_tasks = list(client.models.ProductionTask.find(wo_op_id__in=operation_ids))
    result = {}
    for task in existing_tasks:
        status = getattr(task, 'status', None)
        op_id = getattr(task, 'wo_op_id', None)
        if not op_id or status == "已取消":
            continue
        current = result.get(op_id)
        if current is None:
            result[op_id] = task
            continue
        current_start = getattr(current, 'planned_start_time', '') or ''
        task_start = getattr(task, 'planned_start_time', '') or ''
        if task_start >= current_start:
            result[op_id] = task
    return result


def _build_task_payload(item, shift_id, is_night, schedule_note):
    wait_minutes = item.get("wait_time_minutes", 0) or 0
    return {
        "wo_op_id": item["operation_id"],
        "work_order_id": item["work_order_id"],
        "machine_id": item["machine_id"],
        "lot_id": None,
        "planned_start_time": item["start_time"],
        "planned_end_time": item["end_time"],
        "planned_quantity": item.get("planned_quantity", 0) or 0,
        "actual_start_time": None,
        "actual_end_time": None,
        "actual_quantity": 0.0,
        "scrap_quantity": 0.0,
        "actual_efficiency": None,
        "actual_yield": None,
        "setup_time_actual": 0.0,
        "wait_time_actual": round(wait_minutes / 60, 4),
        "shift_id": shift_id,
        "is_night_shift": is_night,
        "status": "已排程",
        "note": schedule_note
    }


def _is_task_updatable(task):
    if getattr(task, 'actual_start_time', None) or getattr(task, 'actual_end_time', None):
        return False
    return getattr(task, 'status', None) in UPDATABLE_TASK_STATUS


def _is_operation_updatable(op):
    if getattr(op, 'actual_start', None) or getattr(op, 'actual_end', None):
        return False
    return getattr(op, 'status', None) in UPDATABLE_OPERATION_STATUS


def _get_shift_info(dt):
    if 8 <= dt.hour < 20:
        return "SHIFT-DAY", False
    return "SHIFT-NIGHT", True


def _generate_task_id(index):
    # TODO now_key = datetime.now().strftime("%Y%m%d%H%M%S")
    now_key = datetime(2026, 4, 26).strftime("%Y%m%d%H%M%S")
    return f"PT-ACT-{now_key}-{index:04d}"


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
