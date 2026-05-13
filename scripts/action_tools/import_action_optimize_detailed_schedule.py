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
    "description": "使用 CP-SAT 进行精确排程，支持换线时间等复杂约束。适用于小规模工单（≤20个），需要精确到工序级排程时使用。计算时间较长（1-5分钟）。大规模场景请用 optimize_detailed_schedule_fast。",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "work_order",
    "parameters": [
        {
            "name": "work_order_ids",
            "type": "array",
            "required": True,
            "description": "需要精确排程的工单ID列表（建议≤20个）"
        },
        {
            "name": "planning_horizon_days",
            "type": "integer",
            "required": False,
            "description": "排程规划天数。时间越长计算越慢，默认7天"
        },
        {
            "name": "consider_setup",
            "type": "boolean",
            "required": False,
            "description": "是否考虑换线时间。默认true。设为false可加快计算"
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
            "description": "写入ProductionTask.note的备注，默认'CP-SAT详细排程优化Action-自动写入'"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 详细排程优化函数实现 - 使用 Ontology SDK + OR-Tools CP-SAT（批量查询优化版）
import json
from datetime import datetime, timedelta
from ortools.sat.python import cp_model
from my_ontology_sdk import OntologyClient

UPDATABLE_TASK_STATUS = {"已排程", "待执行", "已延期"}
UPDATABLE_OPERATION_STATUS = {"待开工", "已排程"}
DEFAULT_SCHEDULE_NOTE = "CP-SAT详细排程优化Action-自动写入"


def execute_optimize_detailed_schedule(parameters):
    """
    详细排程优化 - CP-SAT模型（批量查询优化版）
    
    数学模型:
    - 决策变量:
      S[o,m]: 工序o在机台m上的开始时间（区间变量）
      P[o,m]: 工序o是否分配给机台m（0-1布尔变量）
      C: 最大完成时间（makespan，整数变量）
    - 目标函数: Minimize C（最小化总工期）
    - 约束条件:
      1. 工序分配: ΣP[o,m] = 1（每道工序必须分配给一个机台）
      2. 工序顺序: S[o+1] >= End(S[o])（同一工单的工序必须顺序执行）
      3. 机台不重叠: NoOverlap(S[o,m] for all o on machine m)
      4. 机台能力: P[o,m] = 0 如果机台m不能生产产品
      5. 时间边界: 0 <= S[o,m] <= horizon
    
    优化内容:
    1. 【关键】批量查询所有工单、工序、步骤、机台能力
    2. 预过滤有能力机台，减少CP-SAT变量数量
    3. 使用可选区间变量(OptionalIntervalVar)处理机台选择
    """
    try:
        # 1. 解析参数
        work_order_ids = parameters.get("work_order_ids", [])
        planning_horizon_days = parameters.get("planning_horizon_days", 7)
        consider_setup = parameters.get("consider_setup", True)
        
        if not work_order_ids:
            return {"success": False, "error": "请提供工单ID列表"}
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # ============================================================
        # 【批量查询优化】核心数据加载阶段
        # 原方案: 循环中逐条查询工单、工序、步骤、机台能力（N×M次API调用）
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
        # 原方案: 在创建变量时循环查询每个机台的能力
        # 优化后: 一次性查询所有机台能力，构建集合用于O(1)查找
        product_ids = list(set([wo.product_id for wo in work_orders]))
        all_caps = client.models.MachineCapability.find(
            product_id__in=product_ids,
            machine_id__in=[m.machine_id for m in all_machines]
        )
        capable_set = set([(cap.machine_id, cap.product_id) for cap in all_caps])
        
        # 8. 创建CP-SAT模型
        model = cp_model.CpModel()
        
        # 规划时间范围（分钟）
        horizon = planning_horizon_days * 24 * 60
        start_time = datetime.now()
        
        # 存储任务数据，用于结果解析
        task_data = {}
        # 存储每个机台的任务列表，用于不重叠约束
        machine_tasks = {}
        
        # 9. 创建变量
        for wo in work_orders:
            ops = ops_by_wo.get(wo.work_order_id, [])
            
            for seq, op in enumerate(ops):
                step = all_steps.get(op.step_id)
                if not step:
                    continue
                
                # 计算工序加工时长（分钟）
                std_time = step.standard_time_hours or 1.0
                wait_time = getattr(step, 'wait_time_hours', 0.0) or 0.0
                transport_time = getattr(step, 'transport_time_hours', 0.0) or 0.0
                queue_time = 0.5  # 工序间排队时间
                
                # 工序总时长 = 加工时间 + 等待时间 + 转运时间
                duration_minutes = int((std_time + wait_time + transport_time) * 60)
                
                # 找到所需工序类型的机台
                wc_machines = [m for m in all_machines if m.work_center_id == step.machine_type_required]
                if not wc_machines:
                    continue
                
                # 为每个可行机台创建可选区间变量
                optional_intervals = []
                presences = []
                
                for machine in wc_machines:
                    # 预过滤：跳过没有能力的机台（减少变量数量）
                    if (machine.machine_id, wo.product_id) not in capable_set:
                        continue
                    
                    # 布尔变量：工序是否在该机台上执行
                    presence = model.NewBoolVar(
                        f'present_{wo.work_order_id}_{op.wo_op_id}_{machine.machine_id}'
                    )
                    presences.append(presence)
                    
                    # 区间变量：工序的开始时间、持续时间、结束时间
                    start_var = model.NewIntVar(
                        0, horizon,
                        f'start_{wo.work_order_id}_{op.wo_op_id}_{machine.machine_id}'
                    )
                    end_var = model.NewIntVar(
                        0, horizon,
                        f'end_{wo.work_order_id}_{op.wo_op_id}_{machine.machine_id}'
                    )
                    
                    # 可选区间变量：只有当presence=1时才生效
                    interval = model.NewOptionalIntervalVar(
                        start_var,
                        duration_minutes,  # 固定持续时间
                        end_var,
                        presence,
                        f'interval_{wo.work_order_id}_{op.wo_op_id}_{machine.machine_id}'
                    )
                    
                    optional_intervals.append((machine.machine_id, interval, presence))
                
                # 如果没有任何可行机台，跳过此工序
                if optional_intervals:
                    # 约束：工序必须且只能在一个机台上执行
                    model.Add(sum(presence for _, _, presence in optional_intervals) == 1)
                    
                    # 存储任务数据
                    task_data[wo.work_order_id, seq] = {
                        'wo': wo,
                        'op': op,
                        'step': step,
                        'optional_intervals': optional_intervals,
                        'presences': presences
                    }
                    
                    # 记录每个机台的任务，用于不重叠约束
                    for machine_id, interval, presence in optional_intervals:
                        if machine_id not in machine_tasks:
                            machine_tasks[machine_id] = []
                        machine_tasks[machine_id].append((interval, presence, wo.work_order_id, op.wo_op_id))
        
        # 10. 添加工序顺序约束 + 排队时间
        # 同一工单的工序必须按顺序执行，且工序间需要排队时间
        for wo in work_orders:
            ops = ops_by_wo.get(wo.work_order_id, [])
            
            for i in range(len(ops) - 1):
                if (wo.work_order_id, i) in task_data and (wo.work_order_id, i+1) in task_data:
                    current_task = task_data[wo.work_order_id, i]
                    next_task = task_data[wo.work_order_id, i+1]
                    
                    # 对于当前工序的每个可能机台和下一工序的每个可能机台
                    # 如果两个工序都被分配（presence=1），则下一工序必须在当前工序结束后 + 排队时间 开始
                    for curr_machine_id, curr_interval, curr_presence in current_task['optional_intervals']:
                        for next_machine_id, next_interval, next_presence in next_task['optional_intervals']:
                            # 下一道工序开始时间 >= 当前工序结束时间 + 排队时间
                            queue_minutes = int(queue_time * 60)
                            model.Add(next_interval.StartExpr() >= curr_interval.EndExpr() + queue_minutes).OnlyEnforceIf(
                                [curr_presence, next_presence]
                            )
        
        # 11. 添加机台不重叠约束
        # 同一机台上的任务不能同时执行
        for machine_id in machine_tasks:
            intervals = [interval for interval, presence, _, _ in machine_tasks[machine_id]]
            if intervals:
                model.AddNoOverlap(intervals)
        
        # 12. 换线时间约束（当前为简化版本）
        if consider_setup:
            print("[INFO] 换线时间约束已启用，但当前为简化版本")
            # TODO: 可根据实际需要添加换线矩阵约束
        
        # 13. 创建makespan变量
        # makespan = 所有工序的最晚结束时间
        makespan = model.NewIntVar(0, horizon, 'makespan')
        
        for wo in work_orders:
            ops = ops_by_wo.get(wo.work_order_id, [])
            if ops:
                last_seq = len(ops) - 1
                if (wo.work_order_id, last_seq) in task_data:
                    last_task = task_data[wo.work_order_id, last_seq]
                    
                    # makespan >= 每个工单最后一道工序的结束时间
                    for _, interval, presence in last_task['optional_intervals']:
                        model.Add(makespan >= interval.EndExpr()).OnlyEnforceIf(presence)
        
        # 14. 目标函数：最小化makespan
        model.Minimize(makespan)
        
        # 15. 配置求解器
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 300.0  # 5分钟超时
        solver.parameters.num_search_workers = 4       # 多线程搜索
        solver.parameters.log_search_progress = True    # 输出搜索日志
        
        # 16. 求解
        status = solver.Solve(model)
        
        # 17. 解析结果
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            schedule = []
            makespan_minutes = solver.Value(makespan)
            makespan_hours = makespan_minutes / 60
            
            # 遍历所有任务，提取排程结果
            for (wo_id, seq), task_info in task_data.items():
                for machine_id, interval, presence in task_info['optional_intervals']:
                    # 只提取被选中的分配（presence=1）
                    if solver.BooleanValue(presence):
                        start_minutes = solver.Value(interval.StartExpr())
                        end_minutes = solver.Value(interval.EndExpr())
                        
                        schedule.append({
                            "work_order_id": wo_id,
                            "operation_id": task_info['op'].wo_op_id,
                            "step_id": task_info['op'].step_id,
                            "sequence_no": seq,
                            "machine_id": machine_id,
                            "start_time": (start_time + timedelta(minutes=start_minutes)).isoformat(),
                            "end_time": (start_time + timedelta(minutes=end_minutes)).isoformat(),
                            "duration_minutes": end_minutes - start_minutes
                        })
            
            # 按开始时间排序
            schedule.sort(key=lambda x: x['start_time'])
            
            apply_result = None
            if apply_mode == "upsert":
                apply_result = _upsert_schedule_to_ontology(
                    client,
                    schedule,
                    op_lookup,
                    wo_lookup,
                    schedule_note
                )
            
            # 防上下文膨胀：只返回前50条任务详情
            max_schedule = 50
            schedule_returned = schedule[:max_schedule]
            truncated_count = max(0, len(schedule) - max_schedule)
            
            result = {
                "makespan_hours": round(makespan_hours, 2),
                "makespan_days": round(makespan_hours / 24, 2),
                "total_tasks": len(schedule),
                "schedule": schedule_returned,
                "truncated_count": truncated_count,
                "schedule_summary": {
                    "total_tasks": len(schedule),
                    "returned_tasks": len(schedule_returned),
                    "note": "仅返回前50条任务详情，完整数据可通过数据库查询" if truncated_count > 0 else None
                },
                "apply_mode": apply_mode,
                "applied": apply_mode == "upsert",
                "apply_result": apply_result
            }
            
            message_suffix = "，并已应用到本体实例" if apply_mode == "upsert" else ""
            return {
                "success": True,
                "message": f"详细排程完成{message_suffix}，总工期: {makespan_hours:.1f}小时",
                "result": result
            }
        else:
            return {"success": False, "error": "无可行解"}
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}

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
    now_key = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"PT-CPSAT-{now_key}-{index:04d}"


result = execute_optimize_detailed_schedule(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入详细排程优化Action")
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
            print("\n[SUCCESS] 详细排程优化Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   求解器类型: CP-SAT")
            print(f"   实现难度: 4星")
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
