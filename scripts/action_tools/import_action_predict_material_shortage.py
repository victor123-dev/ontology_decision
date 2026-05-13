"""
导入缺料预测Action到本体

Action: predictMaterialShortage
功能: 预测未来30天内哪些物料会短缺
求解器: LP (GLOP)
难度: ⭐
"""
import requests
import json

# API配置
API_URL = "http://localhost:8080/api/v1"

# Action定义
ACTION_DATA = {
    "id": "predict_material_shortage",
    "api_name": "PredictMaterialShortage",
    "name": "缺料预测",
    "description": "预测未来指定天数内哪些物料会出现短缺。当需要检查物料供应风险、回答'未来X天哪些物料会缺货'或评估采购紧迫性时使用。输出按严重程度分级的缺料清单、影响工单及行动建议。",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "material",
    "parameters": [
        {
            "name": "forecast_days",
            "type": "integer",
            "required": False,
            "description": "预测天数范围。短期用7天，中期用30天。默认30天"
        },
        {
            "name": "material_ids",
            "type": "array",
            "required": False,
            "description": "指定要检查的物料ID列表。为空则检查所有物料。示例：['MAT-DIE-BGA', 'MAT-EMC-QFN']"
        },
        {
            "name": "safety_stock_threshold",
            "type": "float",
            "required": False,
            "description": "统一安全库存阈值（覆盖物料自身设置）。为空则使用各物料定义的安全库存"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 缺料预测函数实现 - 使用 Ontology SDK + OR-Tools（批量查询优化版）
import json
from datetime import datetime, timedelta
from ortools.linear_solver import pywraplp

# 使用 SDK
from my_ontology_sdk import OntologyClient

def execute_predict_material_shortage(parameters):
    """
    缺料预测 - LP模型（批量查询优化版 + 静态缺料检测）
    
    【改进算法】双阶段缺料检测：
    阶段1 - 静态缺料检测：检查当前库存是否低于安全库存（即使未来无需求）
    阶段2 - 动态缺料预测：基于LP模型预测未来需求导致的缺料
    
    数学模型（动态预测）:
    - 决策变量: I[m,t]库存量, G[m,t]缺料量
    - 目标函数: Minimize ΣG[m,t]（虚拟目标，实际值由约束决定）
    - 约束条件:
      1. 库存平衡: I[m,t] = I[m,t-1] + R[m,t] - D[m,t]
      2. 缺料计算: G[m,t] >= safety_stock - I[m,t]
      3. 非负约束: G[m,t] >= 0
    
    优化内容:
    1. 【关键】批量查询所有物料、库存、工单、采购订单数据（避免N+1查询）
    2. 预计算每天的需求和到货量，避免重复查询
    3. 预构建工单日期映射，快速查找影响工单
    4. 【新增】静态缺料检测：即使未来无需求，当前库存不足也会报警
    """
    try:
        # 1. 解析参数
        forecast_days = parameters.get("forecast_days", 30)
        material_ids = parameters.get("material_ids", [])
        safety_stock_threshold = parameters.get("safety_stock_threshold")
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # ============================================================
        # 【批量查询优化】核心数据加载阶段
        # 原方案: 循环中逐条查询（N次API调用）
        # 优化后: 使用 __in 批量查询（仅1次API调用）
        # ============================================================
        
        # 3. 批量查询物料数据
        if material_ids:
            # 使用 material_id__in 批量查询指定物料
            materials = client.models.Material.find(material_id__in=material_ids)
        else:
            # 查询所有物料
            materials = client.models.Material.find()
        
        if not materials:
            return {"success": False, "error": "没有找到物料数据"}
        
        materials_list = list(materials)
        material_id_list = [m.material_id for m in materials_list]
        
        # 4. 批量查询所有库存数据（原方案: 循环N次，现: 1次批量查询）
        all_inventories = client.models.Inventory.find(material_id__in=material_id_list)
        inventory_map = {inv.material_id: inv.available_quantity for inv in all_inventories}
        
        # 5. 批量查询所有工单物料需求
        all_woms = client.models.WorkOrderMaterial.find(material_id__in=material_id_list)
        
        # 6. 批量查询所有工单工序
        # 提取所有工单工序ID，一次性查询
        wo_op_ids = list(set([wom.wo_op_id for wom in all_woms if hasattr(wom, 'wo_op_id') and wom.wo_op_id]))
        all_wo_ops = {}
        if wo_op_ids:
            for wo_op in client.models.WorkOrderOperation.find(wo_op_id__in=wo_op_ids):
                all_wo_ops[wo_op.wo_op_id] = wo_op
        
        # 7. 批量查询所有工单
        wo_ids = list(set([wom.work_order_id for wom in all_woms]))
        all_work_orders = {}
        if wo_ids:
            for wo in client.models.WorkOrder.find(work_order_id__in=wo_ids):
                all_work_orders[wo.work_order_id] = wo
        
        # 8. 批量查询所有采购订单行
        all_po_lines = client.models.PurchaseOrderLine.find(material_id__in=material_id_list)
        
        # 9. 批量查询所有采购订单
        po_ids = list(set([line.po_id for line in all_po_lines if hasattr(line, 'po_id') and line.po_id]))
        all_pos = {}
        if po_ids:
            for po in client.models.PurchaseOrder.find(po_id__in=po_ids):
                all_pos[po.po_id] = po
        
        # 10. 创建LP求解器（GLOP是纯线性规划求解器，速度快）
        solver = pywraplp.Solver.CreateSolver('GLOP')
        if not solver:
            return {"success": False, "error": "无法创建求解器"}
        
        # 11. 预计算每天的需求和到货量（使用内存数据，无API调用）
        days = range(forecast_days)
        today = datetime(2026, 4, 26)
        # TODO today = datetime.now()
        
        # 需求缓存: demand_cache[material_id][day] = demand_qty
        demand_cache = {}
        for m in materials_list:
            demand_cache[m.material_id] = {t: 0 for t in days}
        
        # 遍历所有工单物料需求，按日期聚合
        for wom in all_woms:
            demand_qty = wom.required_quantity or 0
            if demand_qty == 0:
                continue
            
            material_id = wom.material_id
            if material_id not in demand_cache:
                continue
            
            planned_date = None
            
            # 优先使用工序计划开始时间
            if hasattr(wom, 'wo_op_id') and wom.wo_op_id and wom.wo_op_id in all_wo_ops:
                wo_op = all_wo_ops[wom.wo_op_id]
                if wo_op.planned_start:
                    planned_date = datetime.fromisoformat(wo_op.planned_start) if isinstance(wo_op.planned_start, str) else wo_op.planned_start
                elif wo_op.planned_end:
                    planned_date = datetime.fromisoformat(wo_op.planned_end) if isinstance(wo_op.planned_end, str) else wo_op.planned_end
            
            # 其次使用工单计划日期
            if not planned_date and hasattr(wom, 'work_order_id') and wom.work_order_id in all_work_orders:
                wo = all_work_orders[wom.work_order_id]
                if wo.planned_start_date:
                    planned_date = datetime.fromisoformat(wo.planned_start_date) if isinstance(wo.planned_start_date, str) else wo.planned_start_date
                elif wo.planned_completion_date:
                    planned_date = datetime.fromisoformat(wo.planned_completion_date) if isinstance(wo.planned_completion_date, str) else wo.planned_completion_date
            
            if planned_date:
                days_diff = (planned_date - today).days
                if days_diff in demand_cache[material_id]:
                    demand_cache[material_id][days_diff] += demand_qty
            else:
                # 无计划日期，默认当天需求
                demand_cache[material_id][0] += demand_qty
        
        # 到货缓存: receipt_cache[material_id][day] = receipt_qty
        receipt_cache = {}
        for m in materials_list:
            receipt_cache[m.material_id] = {t: 0 for t in days}
        
        # 遍历所有采购订单行，按日期聚合到货量
        for line in all_po_lines:
            if line.status not in ['待收货', '部分到货']:
                continue
            
            material_id = line.material_id
            if material_id not in receipt_cache:
                continue
            
            if hasattr(line, 'po_id') and line.po_id and line.po_id in all_pos:
                po = all_pos[line.po_id]
                if po.expected_delivery_date:
                    delivery_date = datetime.fromisoformat(po.expected_delivery_date) if isinstance(po.expected_delivery_date, str) else po.expected_delivery_date
                    days_diff = (delivery_date - today).days
                    
                    if days_diff in receipt_cache[material_id]:
                        receipt_cache[material_id][days_diff] += line.quantity - (line.received_quantity or 0)
        
        # 12. 创建决策变量
        inventory = {}  # I[m,t]: 物料m在第t天的库存
        shortage = {}   # G[m,t]: 物料m在第t天的缺料量
        
        for m in materials_list:
            current_inv = inventory_map.get(m.material_id, 0)
            
            # 初始库存 (t=0) 固定为当前库存
            inventory[m.material_id, 0] = solver.NumVar(0, 1000000, f'inv_{m.material_id}_0')
            inventory[m.material_id, 0].ub = current_inv
            inventory[m.material_id, 0].lb = current_inv
            
            for t in days:
                if t > 0:
                    inventory[m.material_id, t] = solver.NumVar(
                        0, 1000000, f'inv_{m.material_id}_{t}'
                    )
                
                shortage[m.material_id, t] = solver.NumVar(
                    0, 1000000, f'short_{m.material_id}_{t}'
                )
        
        # 13. 添加约束
        
        # 约束1: 库存平衡方程 I[m,t] = I[m,t-1] + receipt - demand
        for m in materials_list:
            for t in days:
                if t == 0:
                    continue
                
                demand = demand_cache[m.material_id][t]
                receipt = receipt_cache[m.material_id][t]
                
                solver.Add(
                    inventory[m.material_id, t] == 
                    inventory[m.material_id, t-1] + receipt - demand
                )
        
        # 约束2: 缺料量计算 G[m,t] >= safety_stock - I[m,t]
        for m in materials_list:
            safety_stock = safety_stock_threshold if safety_stock_threshold else (m.safety_stock_level or 0)
            
            for t in days:
                solver.Add(
                    shortage[m.material_id, t] >= safety_stock - inventory[m.material_id, t]
                )
        
        # 14. 目标函数：最小化总缺料量
        objective = solver.Objective()
        for m in materials_list:
            for t in days:
                objective.SetCoefficient(shortage[m.material_id, t], 1)
        objective.SetMinimization()
        
        # 15. 求解
        solver.SetTimeLimit(5000)
        solver.EnableOutput()
        status = solver.Solve()
        
        # 16. 解析结果
        if status != pywraplp.Solver.OPTIMAL:
            return {"success": False, "error": "求解失败"}
        
        # 【批量优化】预构建工单日期映射，避免结果解析时的循环查询
        wo_date_map = {}
        for wo_id, wo in all_work_orders.items():
            wo_date = None
            if wo.planned_start_date:
                wo_date = datetime.fromisoformat(wo.planned_start_date) if isinstance(wo.planned_start_date, str) else wo.planned_start_date
            elif wo.planned_completion_date:
                wo_date = datetime.fromisoformat(wo.planned_completion_date) if isinstance(wo.planned_completion_date, str) else wo.planned_completion_date
            
            if wo_date:
                days_diff = (wo_date - today).days
                if days_diff not in wo_date_map:
                    wo_date_map[days_diff] = []
                wo_date_map[days_diff].append({
                    "work_order_id": wo.work_order_id,
                    "product_id": wo.product_id,
                    "status": wo.status
                })
        
        shortages = []
        critical_count = 0
        warning_count = 0
        
        # ============================================================
        # 【改进算法】第一阶段：静态缺料检测（当前库存 vs 安全库存）
        # 即使未来没有需求，只要当前库存低于安全库存就报警
        # ============================================================
        static_shortage_count = 0
        for m in materials_list:
            safety_stock = safety_stock_threshold if safety_stock_threshold else (m.safety_stock_level or 0)
            current_inv = inventory_map.get(m.material_id, 0)
            
            # 如果安全库存设置有效且当前库存不足
            if safety_stock > 0 and current_inv < safety_stock:
                gap = safety_stock - current_inv
                static_shortage_count += 1
                
                # 严重程度分级
                severity_ratio = gap / safety_stock if safety_stock > 0 else 1
                if severity_ratio > 2:
                    severity = "critical"
                    critical_count += 1
                elif severity_ratio > 1:
                    severity = "warning"
                    warning_count += 1
                else:
                    severity = "info"
                                
                shortages.append({
                    "material_id": m.material_id,
                    "material_name": m.material_name,
                    "date_offset_days": 0,  # 当前立即缺料
                    "shortage_qty": round(gap, 2),
                    "inventory_level": round(current_inv, 2),
                    "safety_stock": safety_stock,
                    "severity": severity,
                    "shortage_type": "static",  # 标记为静态缺料
                    "affected_work_orders": [],  # 静态缺料暂不关联工单
                    "description": f"当前库存({current_inv})低于安全库存({safety_stock})"
                })
        
        # ============================================================
        # 【原有逻辑】第二阶段：动态缺料预测（LP求解器结果）
        # 基于未来需求和到货预测未来30天的缺料情况
        # ============================================================
        dynamic_shortage_count = 0
        
        for m in materials_list:
            for t in days:
                gap = shortage[m.material_id, t].solution_value()
                inv_level = inventory[m.material_id, t].solution_value()
                
                # 过滤微小缺料（数值误差）
                if gap > 0.1:
                    safety_stock = safety_stock_threshold if safety_stock_threshold else (m.safety_stock_level or 0)
                    
                    # 避免重复：如果静态检测已报告t=0的缺料，跳过动态检测的t=0
                    if t == 0:
                        already_reported = any(
                            s["material_id"] == m.material_id and s["date_offset_days"] == 0 
                            for s in shortages
                        )
                        if already_reported:
                            continue
                    
                    dynamic_shortage_count += 1
                    
                    # 严重程度分级
                    if safety_stock > 0:
                        severity_ratio = gap / safety_stock
                        if severity_ratio > 2:
                            severity = "critical"
                            critical_count += 1
                        elif severity_ratio > 1:
                            severity = "warning"
                            warning_count += 1
                        else:
                            severity = "info"
                    else:
                        severity = "warning"
                        warning_count += 1
                    
                    # 从预构建的映射中获取影响工单（O(1)查找）
                    affected_wos = wo_date_map.get(t, [])[:5]
                    
                    shortages.append({
                        "material_id": m.material_id,
                        "material_name": m.material_name,
                        "date_offset_days": t,
                        "shortage_qty": round(gap, 2),
                        "inventory_level": round(inv_level, 2),
                        "safety_stock": safety_stock,
                        "severity": severity,
                        "shortage_type": "dynamic",  # 标记为动态缺料
                        "affected_work_orders": affected_wos,
                        "description": f"第{t}天预测缺料（需求驱动）"
                    })
        
        # 生成行动建议
        recommendations = []
        if critical_count > 0:
            critical_items = [s["material_id"] for s in shortages if s["severity"] == "critical"][:5]
            # 区分静态和动态紧急缺料
            static_critical = [s["material_id"] for s in shortages if s["severity"] == "critical" and s.get("shortage_type") == "static"]
            dynamic_critical = [s["material_id"] for s in shortages if s["severity"] == "critical" and s.get("shortage_type") == "dynamic"]
            
            recommendation_text = "发现 {} 个严重缺料点（缺口超过安全库存2倍）".format(critical_count)
            if static_critical:
                recommendation_text += "，其中 {} 个为当前库存不足".format(len(static_critical))
            if dynamic_critical:
                recommendation_text += "，{} 个为未来需求预测".format(len(dynamic_critical))
            
            recommendations.append({
                "priority": "urgent",
                "action": "立即启动紧急采购流程",
                "reason": recommendation_text,
                "materials": critical_items
            })
        if warning_count > 0:
            static_warning = [s["material_id"] for s in shortages if s["severity"] == "warning" and s.get("shortage_type") == "static"]
            dynamic_warning = [s["material_id"] for s in shortages if s["severity"] == "warning" and s.get("shortage_type") == "dynamic"]
            
            recommendation_text = "发现 {} 个预警缺料点（缺口超过安全库存）".format(warning_count)
            if static_warning:
                recommendation_text += "，其中 {} 个为当前库存不足".format(len(static_warning))
            if dynamic_warning:
                recommendation_text += "，{} 个为未来需求预测".format(len(dynamic_warning))
            
            recommendations.append({
                "priority": "normal",
                "action": "安排常规采购补货",
                "reason": recommendation_text,
                "materials": [s["material_id"] for s in shortages if s["severity"] == "warning"][:10]
            })
        
        # 按严重程度排序
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        shortages.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["date_offset_days"]))
        
        # 防上下文膨胀：只返回前20条详情，其余汇总
        max_details = 20
        shortage_details_returned = shortages[:max_details]
        truncated_count = max(0, len(shortages) - max_details)
        
        # 统计静态/动态缺料数量
        static_shortages = [s for s in shortages if s.get("shortage_type") == "static"]
        dynamic_shortages = [s for s in shortages if s.get("shortage_type") == "dynamic"]
        
        result = {
            "forecast_days": forecast_days,
            "total_shortages": len(shortages),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "shortage_details": shortage_details_returned,
            "truncated_count": truncated_count,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat()
        }
        
        # 构建详细消息
        message_parts = ["缺料预测完成"]
        if static_shortages:
            message_parts.append("当前库存不足{}个物料".format(len(static_shortages)))
        if dynamic_shortages:
            message_parts.append("未来需求预测{}个缺料点".format(len(dynamic_shortages)))
        message_parts.append("严重{}个，预警{}个".format(critical_count, warning_count))
        
        return {
            "success": True,
            "message": "，".join(message_parts),
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}


result = execute_predict_material_shortage(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入缺料预测Action")
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
            print("\n[SUCCESS] 缺料预测Action导入成功")
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
