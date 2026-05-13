"""
生成未来7天的生产排程数据
基准时间: 2026-04-26 08:00:00（与仿真数据衔接）
规划周期: 7天（到2026-05-03）

功能:
1. 查询所有"生产中"状态的工单
2. 找出这些工单中"待开工"的工序
3. 使用考虑机台占用、工序顺序、工单优先级和换线成本的启发式贪婪算法生成生产任务
4. 使用MachineCapability过滤可加工机台并应用效率因子
5. 避让已有production_task，避免重复排同一wo_op_id
6. 符合仿真系统的production_task生成逻辑：
   - task_id格式: PT-{天数}-{序号}
   - lot_id关联: 从wip_lot表查询分配
   - 时间格式: ISO 8601带时分秒
   - planned_quantity: 考虑良率损耗
   - shift_id/is_night_shift: 根据时间自动判断
"""

from my_ontology_sdk import OntologyClient
from datetime import datetime, timedelta
from collections import defaultdict
import math
import sys

SIMULATION_START_DATE = datetime(2026, 4, 26, 8, 0, 0)
SCHEDULE_BASE_TIME = datetime(2026, 4, 26, 8, 0, 0)
PLANNING_DAYS = 7
WIP_LOT_SIZE = 25
DEFAULT_YIELD_RATE = 0.98
DAY_START_HOUR = 8
DAY_END_HOUR = 20
INITIAL_OFFSET_HOURS = 4.0
QUEUE_TIME_HOURS = 0.5
SETUP_COST_WEIGHT = 2.0
DEMO_TASK_NOTE = "甘特图演示数据-自动生成"
FAR_FUTURE = datetime(2099, 12, 31, 23, 59, 59)


def parse_datetime(value, default=None):
    if not value:
        return default
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00').replace('+00:00', ''))
    except Exception:
        return default


def to_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def calculate_sim_day(task_date: datetime) -> int:
    delta = task_date - SIMULATION_START_DATE
    return delta.days + 1


def generate_task_id(sim_day: int, counter: int) -> str:
    return f"PT-{sim_day:03d}-{counter:03d}"


def get_shift_info(dt: datetime) -> tuple:
    if DAY_START_HOUR <= dt.hour < DAY_END_HOUR:
        return "SHIFT-DAY", False
    return "SHIFT-NIGHT", True


def get_wip_lots_for_workorder(client, wo_id: str) -> list:
    try:
        lots = client.models.WipLot.find(work_order_id=wo_id)
        if lots:
            return sorted(list(lots), key=lambda x: x.lot_id)
    except Exception as e:
        print(f"    ⚠️ 查询WIP Lot失败: {e}")
    return []


def calculate_operation_quantity(wo_planned_qty: float, steps: list, op_sequence: int) -> float:
    if not steps or wo_planned_qty <= 0:
        return wo_planned_qty

    total_yield_rate = 1.0
    for step in steps:
        total_yield_rate *= getattr(step, 'yield_rate_standard', DEFAULT_YIELD_RATE) or DEFAULT_YIELD_RATE

    first_op_input_qty = wo_planned_qty / max(total_yield_rate, 0.0001)
    first_op_input_qty = math.ceil(first_op_input_qty / WIP_LOT_SIZE) * WIP_LOT_SIZE

    if op_sequence == 1:
        return first_op_input_qty

    current_qty = first_op_input_qty
    for i, step in enumerate(steps):
        if i + 1 >= op_sequence:
            break
        current_qty *= getattr(step, 'yield_rate_standard', DEFAULT_YIELD_RATE) or DEFAULT_YIELD_RATE

    return round(current_qty, 4)


def safe_priority(wo) -> int:
    value = getattr(wo, 'priority', None)
    try:
        return int(value) if value is not None else 5
    except Exception:
        return 5


def load_pending_operations(client, work_orders):
    wo_ids = [wo.work_order_id for wo in work_orders]
    all_ops = list(client.models.WorkOrderOperation.find(work_order_id__in=wo_ids)) if wo_ids else []
    ops_by_wo = defaultdict(list)
    pending_ops = []

    for op in all_ops:
        ops_by_wo[op.work_order_id].append(op)
        if getattr(op, 'status', '') == '待开工':
            pending_ops.append(op)

    for wo_id in ops_by_wo:
        ops_by_wo[wo_id].sort(key=lambda x: getattr(x, 'sequence_no', 0) or 0)

    return all_ops, pending_ops, ops_by_wo


def load_route_steps(client, operations):
    step_ids = list({op.step_id for op in operations if getattr(op, 'step_id', None)})
    if not step_ids:
        return {}
    return {step.step_id: step for step in client.models.RouteStep.find(step_id__in=step_ids)}


def load_machines(client, steps_by_id):
    work_center_ids = list({getattr(step, 'machine_type_required', None) for step in steps_by_id.values() if getattr(step, 'machine_type_required', None)})
    machines = []
    for wc_id in work_center_ids:
        machines.extend(client.models.Machine.find(work_center_id=wc_id, is_active=True))

    machines_by_id = {machine.machine_id: machine for machine in machines}
    machines_by_wc = defaultdict(list)
    for machine in machines:
        machines_by_wc[machine.work_center_id].append(machine)

    return machines, machines_by_id, machines_by_wc


def load_capabilities(client, machines, work_orders):
    machine_ids = [machine.machine_id for machine in machines]
    product_ids = list({wo.product_id for wo in work_orders if getattr(wo, 'product_id', None)})
    if not machine_ids or not product_ids:
        return {}, set()

    caps = client.models.MachineCapability.find(machine_id__in=machine_ids, product_id__in=product_ids)
    capability_map = {(cap.machine_id, cap.product_id): cap for cap in caps}
    capable_set = set(capability_map.keys())
    return capability_map, capable_set


def load_setup_matrix(client, machine_ids, product_ids):
    try:
        matrices = client.models.SetupMatrix.find(machine_id__in=machine_ids, to_product_id__in=product_ids, is_active=True)
        return {(m.machine_id, m.from_product_id, m.to_product_id): m for m in matrices}
    except Exception:
        return {}


def load_existing_tasks(client, base_time: datetime):
    try:
        return list(client.models.ProductionTask.find(planned_end_time__gte=to_iso(base_time)))
    except Exception as e:
        print(f"⚠️ 查询已有生产任务失败，将不做已有任务避让: {e}")
        return []


def initialize_schedule_state(base_time, machines, existing_tasks, work_orders_by_id):
    machine_available_at = {machine.machine_id: base_time for machine in machines}
    machine_last_product = {machine.machine_id: getattr(machine, 'current_product_id', None) for machine in machines}
    wo_last_end_at = defaultdict(lambda: base_time)
    existing_wo_op_ids = set()

    for task in existing_tasks:
        status = getattr(task, 'status', '')
        if status == '已取消':
            continue

        wo_op_id = getattr(task, 'wo_op_id', None)
        if wo_op_id:
            existing_wo_op_ids.add(wo_op_id)

        start_time = parse_datetime(getattr(task, 'planned_start_time', None), base_time)
        end_time = parse_datetime(getattr(task, 'planned_end_time', None), base_time)
        machine_id = getattr(task, 'machine_id', None)
        wo_id = getattr(task, 'work_order_id', None)

        if machine_id in machine_available_at and end_time > machine_available_at[machine_id]:
            machine_available_at[machine_id] = end_time

        if wo_id and end_time > wo_last_end_at[wo_id]:
            wo_last_end_at[wo_id] = end_time

        if machine_id and wo_id in work_orders_by_id:
            machine_last_product[machine_id] = getattr(work_orders_by_id[wo_id], 'product_id', machine_last_product.get(machine_id))

        if machine_id and start_time and end_time:
            pass

    return machine_available_at, machine_last_product, wo_last_end_at, existing_wo_op_ids


def calculate_remaining_hours(ops, steps_by_id):
    total = 0.0
    for op in ops:
        step = steps_by_id.get(op.step_id)
        if not step:
            continue
        total += getattr(step, 'standard_time_hours', 1.0) or 1.0
        total += getattr(step, 'wait_time_hours', 0.0) or 0.0
        total += getattr(step, 'transport_time_hours', 0.0) or 0.0
        total += QUEUE_TIME_HOURS
    return max(total, 0.1)


def work_order_sort_key(wo, ops_by_wo, steps_by_id, base_time):
    due_date = parse_datetime(getattr(wo, 'planned_completion_date', None), FAR_FUTURE)
    remaining_time = max((due_date - base_time).total_seconds() / 3600, 1.0)
    remaining_hours = calculate_remaining_hours(ops_by_wo.get(wo.work_order_id, []), steps_by_id)
    critical_ratio = remaining_time / remaining_hours
    return (critical_ratio, safe_priority(wo), due_date, wo.work_order_id)


def get_setup_hours(machine_id, from_product_id, to_product_id, capability, setup_matrix):
    if from_product_id and to_product_id and from_product_id != to_product_id:
        matrix = setup_matrix.get((machine_id, from_product_id, to_product_id))
        if matrix:
            return (getattr(matrix, 'setup_time_minutes', 0) or 0) / 60.0
        return (getattr(capability, 'setup_time_minutes', 30) or 30) / 60.0
    return 0.0


def choose_best_machine(op, wo, step, candidate_machines, capability_map, machine_available_at, machine_last_product, wo_last_end_at, setup_matrix, base_time):
    best = None
    operation_ready_time = max(
        base_time + timedelta(hours=INITIAL_OFFSET_HOURS),
        wo_last_end_at[wo.work_order_id] + timedelta(hours=QUEUE_TIME_HOURS)
    )

    for machine in candidate_machines:
        capability = capability_map.get((machine.machine_id, wo.product_id))
        if not capability:
            continue

        efficiency = getattr(capability, 'efficiency_factor', 1.0) or 1.0
        process_hours = (getattr(step, 'standard_time_hours', 1.0) or 1.0) / max(efficiency, 0.0001)
        wait_hours = getattr(step, 'wait_time_hours', 0.0) or 0.0
        transport_hours = getattr(step, 'transport_time_hours', 0.0) or 0.0
        setup_hours = get_setup_hours(
            machine.machine_id,
            machine_last_product.get(machine.machine_id),
            wo.product_id,
            capability,
            setup_matrix
        )

        planned_start = max(operation_ready_time, machine_available_at.get(machine.machine_id, base_time))
        planned_end = planned_start + timedelta(hours=setup_hours + process_hours + wait_hours + transport_hours)
        score = (
            planned_end + timedelta(hours=setup_hours * (SETUP_COST_WEIGHT - 1.0)),
            setup_hours,
            machine_available_at.get(machine.machine_id, base_time),
            machine.machine_id
        )

        candidate = {
            "machine": machine,
            "capability": capability,
            "planned_start": planned_start,
            "planned_end": planned_end,
            "setup_hours": setup_hours,
            "process_hours": process_hours,
            "wait_hours": wait_hours,
            "transport_hours": transport_hours,
            "score": score,
        }

        if best is None or candidate["score"] < best["score"]:
            best = candidate

    return best


def update_operation(op, machine_id, planned_start, planned_end):
    try:
        op.update(
            assigned_machine_id=machine_id,
            status='已排程',
            planned_start=to_iso(planned_start),
            planned_end=to_iso(planned_end)
        )
    except Exception as e:
        print(f"    ⚠️ 更新工序状态失败 {op.wo_op_id}: {e}")


def generate_future_schedule():
    client = OntologyClient("http://localhost:8080", api_key="your-api-key")
    base_time = SCHEDULE_BASE_TIME
    planning_end = base_time + timedelta(days=PLANNING_DAYS)

    print("=" * 80)
    print("生产排程数据生成工具")
    print("=" * 80)
    print(f"基准时间: {base_time}")
    print(f"规划天数: {PLANNING_DAYS}天")
    print(f"结束时间: {planning_end}")
    print(f"排程策略: 关键比率 + 优先级 + 机台占用 + 能力矩阵 + 换线成本")
    print()

    print("📋 查询生产中的工单...")
    work_orders = list(client.models.WorkOrder.find(status="生产中"))
    if not work_orders:
        print("❌ 没有找到生产中的工单")
        return 0

    work_orders_by_id = {wo.work_order_id: wo for wo in work_orders}
    print(f"✅ 找到 {len(work_orders)} 个生产中的工单")

    all_ops, pending_ops, ops_by_wo = load_pending_operations(client, work_orders)
    if not pending_ops:
        print("⚠️ 没有找到待开工工序")
        return 0
    print(f"✅ 找到 {len(pending_ops)} 个待开工工序")

    steps_by_id = load_route_steps(client, all_ops)
    machines, machines_by_id, machines_by_wc = load_machines(client, steps_by_id)
    capability_map, capable_set = load_capabilities(client, machines, work_orders)
    setup_matrix = load_setup_matrix(client, list(machines_by_id.keys()), list({wo.product_id for wo in work_orders}))
    existing_tasks = load_existing_tasks(client, base_time)

    machine_available_at, machine_last_product, wo_last_end_at, existing_wo_op_ids = initialize_schedule_state(
        base_time,
        machines,
        existing_tasks,
        work_orders_by_id
    )

    print(f"✅ 加载工序定义 {len(steps_by_id)} 个、机台 {len(machines)} 台、能力矩阵 {len(capability_map)} 条")
    print(f"✅ 已有未来任务 {len(existing_tasks)} 个，将用于机台占用避让")
    print(f"✅ 已有任务关联工序 {len(existing_wo_op_ids)} 个，将避免重复创建")

    sorted_work_orders = sorted(work_orders, key=lambda wo: work_order_sort_key(wo, ops_by_wo, steps_by_id, base_time))

    tasks_created = 0
    tasks_failed = 0
    tasks_skipped_duplicate = 0
    tasks_skipped_no_machine = 0
    task_counter = 0
    last_planned_end = base_time

    for idx, wo in enumerate(sorted_work_orders, 1):
        pending_for_wo = [op for op in ops_by_wo.get(wo.work_order_id, []) if getattr(op, 'status', '') == '待开工']
        if not pending_for_wo:
            continue

        pending_for_wo.sort(key=lambda op: getattr(op, 'sequence_no', 0) or 0)
        sorted_steps = sorted(
            [steps_by_id[op.step_id] for op in ops_by_wo.get(wo.work_order_id, []) if op.step_id in steps_by_id],
            key=lambda step: getattr(step, 'sequence_no', 0) or 0
        )
        wip_lots = get_wip_lots_for_workorder(client, wo.work_order_id)
        sort_key = work_order_sort_key(wo, ops_by_wo, steps_by_id, base_time)

        print(f"\n[{idx}/{len(sorted_work_orders)}] 工单 {wo.work_order_id} 产品 {getattr(wo, 'product_id', 'N/A')} 优先级 {safe_priority(wo)} CR {sort_key[0]:.2f}")
        print(f"  📝 待排工序 {len(pending_for_wo)} 个")

        for op_idx, op in enumerate(pending_for_wo, 1):
            try:
                if op.wo_op_id in existing_wo_op_ids:
                    tasks_skipped_duplicate += 1
                    print(f"    ⏭️ 工序 {op.wo_op_id} 已存在生产任务，跳过")
                    continue

                step = steps_by_id.get(op.step_id)
                if not step:
                    print(f"    ⚠️ 工序 {op.wo_op_id} 找不到步骤定义")
                    tasks_failed += 1
                    continue

                wc_id = getattr(step, 'machine_type_required', None)
                wc_machines = machines_by_wc.get(wc_id, [])
                candidate_machines = [m for m in wc_machines if (m.machine_id, wo.product_id) in capable_set]

                if not candidate_machines:
                    print(f"    ⚠️ 工序 {op.wo_op_id} 无满足工作中心和能力矩阵的可用机台")
                    tasks_skipped_no_machine += 1
                    continue

                best = choose_best_machine(
                    op,
                    wo,
                    step,
                    candidate_machines,
                    capability_map,
                    machine_available_at,
                    machine_last_product,
                    wo_last_end_at,
                    setup_matrix,
                    base_time
                )

                if not best:
                    print(f"    ⚠️ 工序 {op.wo_op_id} 无法选择机台")
                    tasks_skipped_no_machine += 1
                    continue

                planned_start = best["planned_start"]
                planned_end = best["planned_end"]
                if planned_start > planning_end:
                    print(f"    ⏭️ 工序 {op.wo_op_id} 起始时间超出规划范围，跳过")
                    break

                task_counter += 1
                task_id = generate_task_id(calculate_sim_day(planned_start), task_counter)
                planned_qty = calculate_operation_quantity(
                    getattr(wo, 'planned_quantity', 0) or 0,
                    sorted_steps,
                    getattr(op, 'sequence_no', 1) or 1
                )

                lot_id = None
                if wip_lots:
                    lot_index = ((getattr(op, 'sequence_no', 1) or 1) - 1) % len(wip_lots)
                    lot_id = wip_lots[lot_index].lot_id

                shift_id, is_night = get_shift_info(planned_start)
                machine = best["machine"]

                client.models.ProductionTask.create({
                    "task_id": task_id,
                    "wo_op_id": op.wo_op_id,
                    "work_order_id": wo.work_order_id,
                    "machine_id": machine.machine_id,
                    "lot_id": lot_id,
                    "planned_start_time": to_iso(planned_start),
                    "planned_end_time": to_iso(planned_end),
                    "planned_quantity": planned_qty,
                    "actual_start_time": None,
                    "actual_end_time": None,
                    "actual_quantity": 0.0,
                    "scrap_quantity": 0.0,
                    "actual_efficiency": None,
                    "actual_yield": None,
                    "setup_time_actual": round(best["setup_hours"], 4),
                    "wait_time_actual": round(best["wait_hours"] + best["transport_hours"], 4),
                    "shift_id": shift_id,
                    "is_night_shift": is_night,
                    "status": "已排程",
                    "note": DEMO_TASK_NOTE
                })

                update_operation(op, machine.machine_id, planned_start, planned_end)

                machine_available_at[machine.machine_id] = planned_end
                machine_last_product[machine.machine_id] = wo.product_id
                wo_last_end_at[wo.work_order_id] = planned_end
                existing_wo_op_ids.add(op.wo_op_id)
                tasks_created += 1
                last_planned_end = max(last_planned_end, planned_end)

                print(
                    f"    ✓ {op_idx}/{len(pending_for_wo)} {op.wo_op_id} -> {machine.machine_id} "
                    f"{to_iso(planned_start)} ~ {to_iso(planned_end)} "
                    f"setup={best['setup_hours']:.2f}h"
                )

            except Exception as e:
                print(f"    ❌ 创建任务失败 {getattr(op, 'wo_op_id', 'UNKNOWN')}: {e}")
                tasks_failed += 1

    print("\n" + "=" * 80)
    print("✅ 排程计划生成完成!")
    print("=" * 80)
    print(f"   成功创建: {tasks_created} 个生产任务")
    print(f"   失败跳过: {tasks_failed} 个")
    print(f"   重复跳过: {tasks_skipped_duplicate} 个")
    print(f"   无机台跳过: {tasks_skipped_no_machine} 个")
    print(f"   时间范围: {base_time} ~ {last_planned_end}")
    print(f"   实际跨度: {(last_planned_end - base_time).days}天 {(last_planned_end - base_time).seconds // 3600}小时")
    print("=" * 80)

    return tasks_created


if __name__ == "__main__":
    try:
        created = generate_future_schedule()
        if created > 0:
            print(f"\n🎉 成功生成 {created} 个排产任务！")
            sys.exit(0)
        else:
            print("\n⚠️ 未生成任何任务")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
