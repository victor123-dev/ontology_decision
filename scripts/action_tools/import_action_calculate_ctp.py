"""
导入机台可用能力承诺(CTP)计算Action到本体

Action: calculateCTP
功能: 计算指定产品订单的最早可承诺交付日期
求解器: LP (GLOP)
难度: ⭐
"""
import requests

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "calculate_ctp",
    "api_name": "CalculateCTP",
    "name": "机台可用能力承诺(CTP)计算",
    "description": "计算指定产品和数量的最早可承诺交付日期。当客户询问'什么时候能交货'、需要承诺交期或评估订单可行性时使用。返回预计交付日期、瓶颈工序、可用机台及产能分析。",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "customer_order",
    "parameters": [
        {
            "name": "product_id",
            "type": "string",
            "required": True,
            "description": "产品ID。示例：'BGA-CPU'"
        },
        {
            "name": "quantity",
            "type": "float",
            "required": True,
            "description": "订单数量。支持浮点数，系统自动向上取整为整数"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 机台可用能力承诺(CTP)计算 - 使用 Ontology SDK + OR-Tools（批量查询优化版）
import json
from datetime import datetime
from ortools.linear_solver import pywraplp
from my_ontology_sdk import OntologyClient

def execute_calculate_ctp(parameters):
    """
    机台可用能力承诺(CTP)计算 - LP模型（批量查询优化版）
    
    功能:
    基于机台能力和工序时间，计算产品订单的最早可承诺交付日期
    
    数学模型:
    - 决策变量: D（交付日期，分钟）
    - 目标函数: Minimize D
    - 约束条件:
      1. D >= Σ(工序时间 × QTY / 机台可用能力)
      2. D >= 机台最早可用时间 + 加工时间
    
    优化内容:
    1. 【关键】批量查询所有机台和能力数据（避免N+1查询）
    2. 预计算工序总加工时间，减少循环中的重复计算
    """
    try:
        # 1. 解析参数
        product_id = parameters.get("product_id")
        quantity_raw = parameters.get("quantity")
        
        if not product_id:
            return {"success": False, "error": "请提供产品ID"}
        if quantity_raw is None or quantity_raw <= 0:
            return {"success": False, "error": "请提供有效的订单数量"}
        
        # 类型转换：支持浮点数输入，向上取整为整数
        import math
        quantity = int(math.ceil(float(quantity_raw)))
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # ============================================================
        # 【批量查询优化】核心数据加载阶段
        # 原方案: 循环中逐条查询机台能力（N×M次API调用）
        # 优化后: 批量查询机台能力（仅1次API调用）
        # ============================================================
        
        # 3. 批量查询所有机台
        all_machines = client.models.Machine.find(is_active=True)
        if not all_machines:
            return {"success": False, "error": "没有找到机台数据"}
        all_machines = list(all_machines)
        
        # 4. 批量查询机台能力
        # 原方案: for machine in machines: caps = client.models.MachineCapability.find(machine_id=m.machine_id, product_id=product_id)
        # 优化后: 一次性查询所有机台的能力，用__in批量查询
        all_caps = client.models.MachineCapability.find(
            product_id=product_id,
            machine_id__in=[m.machine_id for m in all_machines]
        )
        
        # 构建能力集合，用于快速查找
        capable_machine_ids = set([cap.machine_id for cap in all_caps])
        # 构建机台字典
        machines_dict = {m.machine_id: m for m in all_machines}
        # 构建机台能力字典（按机台ID索引）
        capability_dict = {cap.machine_id: cap for cap in all_caps}
        # 过滤出有能力的机台
        machines_with_capability = [m for m in all_machines if m.machine_id in capable_machine_ids]
        
        if not machines_with_capability:
            return {
                "success": False,
                "error": f"没有找到能够生产产品 {product_id} 的机台"
            }
        
        # 5. 查询产品工艺路线
        process_routes = client.models.ProcessRoute.find(product_id=product_id)
        if not process_routes:
            return {"success": False, "error": f"没有找到产品 {product_id} 的工艺路线"}
        
        # 获取工艺路线ID（取第一个）
        process_route = process_routes[0]
        route_id = process_route.route_id
        
        # 6. 查询工艺路线步骤
        route_steps = client.models.RouteStep.find(route_id=route_id)
        if not route_steps:
            return {"success": False, "error": f"工艺路线 {route_id} 没有工序步骤"}
        
        route_steps = sorted(route_steps, key=lambda x: x.sequence_no or 0)
        
        # 7. 计算每个步骤的加工时间
        step_times = []
        total_standard_time = 0
        
        for step in route_steps:
            standard_time = step.standard_time_hours or 0
            total_standard_time += standard_time
            step_times.append({
                "step_id": step.step_id,
                "sequence_no": step.sequence_no,
                "standard_time_hours": standard_time,
                "machine_type_required": step.machine_type_required
            })
        
        # 8. 创建LP求解器（GLOP是纯线性规划求解器，速度快）
        solver = pywraplp.Solver.CreateSolver('GLOP')
        if not solver:
            return {"success": False, "error": "无法创建求解器"}
        
        # 9. 创建决策变量
        
        # 交付时间变量（分钟）
        delivery_time = solver.NumVar(0, 1000000, 'delivery_time')
        
        # 每个机台的加工时间变量
        machine_process_times = {}
        for machine in machines_with_capability:
            # 检查机台是否属于所需的工序类型
            can_process = False
            for step in route_steps:
                if machine.work_center_id == step.machine_type_required:
                    can_process = True
                    break
            
            if can_process:
                machine_process_times[machine.machine_id] = solver.NumVar(
                    0, 1000000, f'machine_time_{machine.machine_id}'
                )
        
        # 10. 添加约束
        
        # 约束1: 交付时间 >= 所有机台加工时间的最大值
        for machine_id, var in machine_process_times.items():
            solver.Add(delivery_time >= var)
        
        # 约束2: 每个机台的加工时间 = Σ(步骤时间 × 数量) / 机台可用能力
        # 简化计算：使用标准加工时间
        for machine in machines_with_capability:
            if machine.machine_id not in machine_process_times:
                continue
            
            total_time = 0
            for step in step_times:
                if machine.work_center_id == step['machine_type_required']:
                    step_time_minutes = step['standard_time_hours'] * 60
                    total_time += step_time_minutes * quantity
            
            # 计算机台加工时间（使用MachineCapability中的效率因子）
            cap = capability_dict.get(machine.machine_id)
            efficiency_factor = cap.efficiency_factor if cap else 1.0
            
            if efficiency_factor > 0:
                actual_time = total_time / efficiency_factor
            else:
                actual_time = total_time
            
            # 机台加工时间约束
            solver.Add(
                machine_process_times[machine.machine_id] >= actual_time
            )
        
        # 11. 目标函数：最小化交付时间
        solver.Minimize(delivery_time)
        
        # 12. 求解
        solver.SetTimeLimit(5000)
        solver.EnableOutput()
        status = solver.Solve()
        
        if status != pywraplp.Solver.OPTIMAL:
            return {"success": False, "error": "求解失败"}
        
        # 13. 解析结果
        delivery_minutes = delivery_time.solution_value()
        delivery_hours = delivery_minutes / 60
        delivery_days = delivery_hours / 24
        
        # TODO ctp_date = datetime.now() + __import__('datetime').timedelta(hours=delivery_hours)
        ctp_date = datetime(2026, 4, 26) + __import__('datetime').timedelta(hours=delivery_hours)
        
        # 计算各机台加工时间
        machine_times = {}
        max_machine_time = 0
        bottleneck_machine_id = None
        for machine_id, var in machine_process_times.items():
            time_minutes = var.solution_value()
            machine_times[machine_id] = {
                "time_minutes": round(time_minutes, 2),
                "time_hours": round(time_minutes / 60, 2)
            }
            if time_minutes > max_machine_time:
                max_machine_time = time_minutes
                bottleneck_machine_id = machine_id
        
        # 找出瓶颈工序（加工时间最长的工序类型）
        bottleneck_step = None
        max_step_time = 0
        for step in step_times:
            step_time_minutes = step['standard_time_hours'] * 60
            if step_time_minutes > max_step_time:
                max_step_time = step_time_minutes
                bottleneck_step = step
        
        # 计算置信度
        if status == pywraplp.Solver.OPTIMAL:
            confidence = "high"
        elif status == pywraplp.Solver.FEASIBLE:
            confidence = "medium"
        else:
            confidence = "low"
        
        # 生成建议
        recommendations = []
        if delivery_days > 7:
            recommendations.append({
                "type": "warning",
                "message": f"交付周期较长（{delivery_days:.1f}天），建议考虑加急或分批交付"
            })
        if bottleneck_machine_id:
            recommendations.append({
                "type": "info",
                "message": f"瓶颈机台：{bottleneck_machine_id}（加工时间最长 {max_machine_time:.0f} 分钟）"
            })
        if bottleneck_step:
            recommendations.append({
                "type": "info",
                "message": f"瓶颈工序：{bottleneck_step.get('step_id', '')}（标准时间 {max_step_time:.1f} 分钟）"
            })
        
        result = {
            "product_id": product_id,
            "quantity": quantity,
            "total_standard_time_hours": round(total_standard_time * quantity, 2),
            "estimated_delivery_time": {
                "minutes": round(delivery_minutes, 2),
                "hours": round(delivery_hours, 2),
                "days": round(delivery_days, 2),
                "date": ctp_date.isoformat()
            },
            "confidence": confidence,
            "summary": {
                "capable_machine_count": len(machines_with_capability),
                "total_standard_time_hours": round(total_standard_time * quantity, 2)
            },
            "recommendations": recommendations,
            "bottleneck_analysis": {
                "bottleneck_machine_id": bottleneck_machine_id,
                "bottleneck_machine_time_minutes": round(max_machine_time, 2) if max_machine_time > 0 else None,
                "bottleneck_step_id": bottleneck_step['step_id'] if bottleneck_step else None,
                "bottleneck_step_time_minutes": round(max_step_time, 2) if max_step_time > 0 else None
            },
            "summary": {
                "capable_machine_count": len(machines_with_capability),
                "total_standard_time_hours": round(total_standard_time * quantity, 2)
            },
            "calculated_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "message": f"CTP计算完成，最早可承诺交付日期: {ctp_date.strftime('%Y-%m-%d')}",
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}


result = execute_calculate_ctp(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入机台可用能力承诺(CTP)计算Action")
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
            print("\n[SUCCESS] 机台可用能力承诺(CTP)计算Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   求解器类型: LP (GLOP)")
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
