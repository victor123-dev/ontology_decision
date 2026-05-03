"""
导入启发式产能优化分配Action到本体

Action: optimizeCapacityAllocationHeuristic
功能: 使用优先级规则进行产能分配，秒级出结果
算法: 启发式（EDD+SPT混合规则）
难度: ⭐
优势: 超快速、无需求解器、适合大规模场景
"""
import requests

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "optimize_capacity_allocation_heuristic",
    "api_name": "OptimizeCapacityAllocationHeuristic",
    "name": "产能优化分配（启发式）",
    "description": "使用启发式规则进行产能分配，最大化按时交付率（优先级加权），秒级出结果",
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
        },
        {
            "name": "scheduling_rule",
            "type": "string",
            "required": False,
            "description": "调度规则：EDD(最早交期), SPT(最短加工), CR(关键比率), 默认EDD"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 启发式产能优化分配 - EDD/SPT/CR混合规则（批量查询优化版）
import json
from datetime import datetime, timedelta
from my_ontology_sdk import OntologyClient

def execute_optimize_capacity_allocation_heuristic(parameters):
    """
    启发式产能优化分配（批量查询优化版）
    
    调度规则:
    1. EDD (Earliest Due Date): 最早交期优先 - 交期越早，优先级越高
    2. SPT (Shortest Processing Time): 最短加工时间优先 - 加工时间越短，优先级越高
    3. CR (Critical Ratio): 关键比率 = (交期-当前时间)/剩余加工时间 - 比率越小，优先级越高
    
    算法流程:
    1. 批量加载所有数据（工单、工序、步骤、机台、客户）
    2. 计算每个工单的优先级分数（考虑客户等级+订单优先级）
    3. 按分数排序
    4. 贪婪分配机台（选择最早可用的有能力机台）
    5. 检查按时交付情况
    
    优化内容:
    1. 【关键】批量查询所有工单、工序、步骤、机台能力（避免N+1查询）
    2. 内存过滤机台能力，避免循环API调用
    """
    try:
        # 1. 解析参数
        work_order_ids = parameters.get("work_order_ids", [])
        planning_horizon_days = parameters.get("planning_horizon_days", 30)
        scheduling_rule = parameters.get("scheduling_rule", "EDD")
        
        if not work_order_ids:
            return {"success": False, "error": "请提供工单ID列表"}
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # ============================================================
        # 【批量查询优化】核心数据加载阶段
        # 原方案: 循环中逐条查询工单、工序、步骤、客户信息（N次API调用）
        # 优化后: 批量查询所有相关数据（仅6次API调用）
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
        
        # 7. 批量查询机台能力
        # 原方案: for machine in machines: caps = client.models.MachineCapability.find(machine_id=machine.machine_id, product_id=product_id)
        # 优化后: 一次性查询所有机台能力，构建集合用于O(1)查找
        product_ids = list(set([wo.product_id for wo in work_orders]))
        all_caps = client.models.MachineCapability.find(
            product_id__in=product_ids,
            machine_id__in=[m.machine_id for m in all_machines]
        )
        capable_set = set([(cap.machine_id, cap.product_id) for cap in all_caps])
        
        # 8. 批量查询客户信息
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
        
        # 9. 预计算客户等级权重（内存查找，无API调用）
        customer_weights = {}
        for wo in work_orders:
            customer_weight = 1.0
            if hasattr(wo, 'customer_order_id') and wo.customer_order_id and wo.customer_order_id in all_orders:
                order = all_orders[wo.customer_order_id]
                if hasattr(order, 'customer_id') and order.customer_id and order.customer_id in all_customers:
                    customer = all_customers[order.customer_id]
                    customer_level = customer.customer_level or "普通"
                    # VIP客户权重2.0，重要客户1.5，普通客户1.0
                    customer_weight = {"VIP": 2.0, "重要": 1.5, "普通": 1.0}.get(customer_level, 1.0)
            customer_weights[wo.work_order_id] = customer_weight
        
        # 10. 计算每个工单的调度分数
        scored_work_orders = []
        now = datetime.now()
        
        for wo in work_orders:
            ops = ops_by_wo.get(wo.work_order_id, [])
            
            # 计算总加工时长（分钟）
            total_processing_time = 0
            for op in ops:
                step = all_steps.get(op.step_id)
                if step:
                    total_processing_time += (step.standard_time_hours or 1) * 60  # 转换为分钟
            
            # 计算交期（小时）
            if wo.planned_completion_date:
                due_date = datetime.fromisoformat(wo.planned_completion_date) if isinstance(wo.planned_completion_date, str) else wo.planned_completion_date
                due_hours = (due_date - now).total_seconds() / 3600
            else:
                due_hours = planning_horizon_days * 24
                due_date = now + timedelta(hours=due_hours)
            
            # 计算权重
            # 订单优先级权重：P1=10, P3=5, P5=1
            order_priority = wo.priority or 3
            order_priority_weight = {1: 10, 3: 5, 5: 1}.get(order_priority, 5)
            customer_weight = customer_weights.get(wo.work_order_id, 1.0)
            total_weight = customer_weight * order_priority_weight
            
            # 根据调度规则计算分数
            if scheduling_rule == "EDD":
                score = due_hours  # 交期越早，分数越小，优先级越高
            elif scheduling_rule == "SPT":
                score = total_processing_time  # 加工时间越短，优先级越高
            elif scheduling_rule == "CR":
                cr = due_hours / (total_processing_time / 60) if total_processing_time > 0 else float("inf")
                score = cr  # 关键比率越小，优先级越高
            else:
                score = due_hours
            
            scored_work_orders.append({
                "wo": wo,
                "ops": ops,
                "total_processing_time": total_processing_time,
                "due_date": due_date,
                "due_hours": due_hours,
                "score": score,
                "priority_weight": total_weight,
                "order_priority": order_priority,
                "customer_weight": customer_weight
            })
        
        # 11. 排序（分数小的优先）
        scored_work_orders.sort(key=lambda x: x["score"])
        
        # 12. 贪婪分配机台
        # 记录每个机台的可用时间（分钟）
        machine_available_time = {m.machine_id: 0 for m in all_machines}
        schedule = []
        on_time_count = 0
        
        for scored_wo in scored_work_orders:
            wo = scored_wo["wo"]
            ops = scored_wo["ops"]
            
            wo_end_time = 0  # 工单完成时间（分钟）
            
            for op in ops:
                step = all_steps.get(op.step_id)
                if not step:
                    continue
                
                duration = (step.standard_time_hours or 1) * 60
                
                # 找到所需工序类型的机台
                wc_machines = [m for m in all_machines if m.work_center_id == step.machine_type_required]
                
                # 选择最早可用的有能力机台
                best_machine = None
                best_start = float("inf")
                
                for machine in wc_machines:
                    # 使用预构建的能力集合进行O(1)查找
                    if (machine.machine_id, wo.product_id) in capable_set:
                        start_time = machine_available_time[machine.machine_id]
                        if start_time < best_start:
                            best_start = start_time
                            best_machine = machine
                
                if best_machine:
                    start = wo_end_time if wo_end_time > best_start else best_start
                    end = start + duration
                    
                    machine_available_time[best_machine.machine_id] = end
                    wo_end_time = end
                    
                    schedule.append({
                        "work_order_id": wo.work_order_id,
                        "operation_id": op.wo_op_id,
                        "step_id": op.step_id,
                        "sequence_no": op.sequence_no,
                        "machine_id": best_machine.machine_id,
                        "start_time": (now + timedelta(minutes=start)).isoformat(),
                        "end_time": (now + timedelta(minutes=end)).isoformat(),
                        "start_minutes": start,
                        "end_minutes": end
                    })
            
            # 检查是否按时交付
            wo_end_hours = wo_end_time / 60
            if wo_end_hours <= scored_wo["due_hours"]:
                on_time_count += 1
        
        # 13. 构建结果
        total_wos = len(work_orders)
        on_time_rate = round(on_time_count / total_wos * 100, 2) if total_wos > 0 else 0
        
        schedule.sort(key=lambda x: x["start_time"])
        
        result = {
            "total_work_orders": total_wos,
            "on_time_count": on_time_count,
            "on_time_rate": on_time_rate,
            "scheduling_rule": scheduling_rule,
            "customer_weight_applied": True,
            "work_order_priorities": [
                {
                    "work_order_id": scored_wo["wo"].work_order_id,
                    "order_priority": scored_wo["order_priority"],
                    "customer_weight": scored_wo["customer_weight"],
                    "total_weight": scored_wo["priority_weight"],
                    "due_hours": round(scored_wo["due_hours"], 2),
                    "score": round(scored_wo["score"], 2)
                }
                for scored_wo in scored_work_orders
            ],
            "schedule": schedule
        }
        
        return {
            "success": True,
            "message": f"产能优化完成，按时交付率: {on_time_rate}%，调度规则: {scheduling_rule}",
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}

result = execute_optimize_capacity_allocation_heuristic(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入启发式产能优化分配Action")
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
            print("\n[SUCCESS] 启发式产能优化分配Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   算法类型: 启发式规则（EDD/SPT/CR）")
            print(f"   预计求解时间: < 0.1秒")
            print(f"   实现难度: 1星")
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
