"""
导入采购计划优化Action到本体

Action: optimizePurchasePlan
功能: 优化采购计划，选择最优供应商组合
求解器: MIP (CBC)
难度: ⭐⭐
"""
import requests

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "optimize_purchase_plan",
    "api_name": "OptimizePurchasePlan",
    "name": "采购计划优化",
    "description": "优化采购计划，选择最优供应商组合以最小化成本。当需要制定采购决策、回答'应该向哪些供应商采购多少物料'或优化采购成本时使用。返回采购清单、总成本、供应商选择建议及成本分析。",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "purchase_order",
    "parameters": [
        {
            "name": "material_ids",
            "type": "array",
            "required": True,
            "description": "需要采购的物料ID列表。示例：['MAT-DIE-BGA', 'MAT-EMC-QFN']"
        },
        {
            "name": "forecast_days",
            "type": "integer",
            "required": False,
            "description": "采购规划天数。短期采购用7天，常规用30天。默认30天"
        },
        {
            "name": "budget_limit",
            "type": "float",
            "required": False,
            "description": "预算上限（元）。如果不设置则不限制预算"
        },
        {
            "name": "max_suppliers_per_material",
            "type": "integer",
            "required": False,
            "description": "每个物料最多选择几个供应商。用于分散供应风险，默认3。设1表示单一供应商"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 采购计划优化 - 使用 Ontology SDK + OR-Tools（批量查询优化版）
import json
from datetime import datetime, timedelta
from ortools.linear_solver import pywraplp
from my_ontology_sdk import OntologyClient

def execute_optimize_purchase_plan(parameters):
    """
    采购计划优化 - MIP模型（批量查询优化版）
    
    数学模型:
    - 决策变量:
      X[s,m]: 供应商s向物料m的采购量（连续变量）
      Y[s,m]: 是否选择供应商s供应物料m（0-1变量）
    - 目标函数: Minimize Σ(price[s,m] × X[s,m])
    - 约束条件:
      1. 需求满足: ΣX[s,m] >= demand[m]
      2. 供应商容量: X[s,m] <= capacity[s,m] × Y[s,m]
      3. 供应商数量限制: ΣY[s,m] <= max_suppliers
      4. 最小订单量: X[s,m] >= min_order[s,m] × Y[s,m]
      5. 变量边界: X[s,m] >= 0, Y[s,m] ∈ {0,1}
    
    优化内容:
    1. 【关键】批量查询所有供应商-物料关系（原方案: N×M次API调用）
    2. 预构建供应商物料字典，避免循环查询
    3. 预计算需求缺口，减少重复计算
    """
    try:
        # 1. 解析参数
        material_ids = parameters.get("material_ids", [])
        forecast_days = parameters.get("forecast_days", 30)
        max_suppliers = parameters.get("max_suppliers_per_material", 3)
        
        if not material_ids:
            return {"success": False, "error": "请提供物料ID列表"}
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # ============================================================
        # 【批量查询优化】核心数据加载阶段
        # 原方案: 循环中逐条查询供应商物料关系（N×M次API调用）
        # 优化后: 批量查询所有供应商-物料关系（仅1次API调用）
        # ============================================================
        
        # 3. 批量查询物料数据
        materials = client.models.Material.find(material_id__in=material_ids)
        if not materials:
            return {"success": False, "error": "没有找到物料数据"}
        materials = list(materials)
        material_id_list = [m.material_id for m in materials]
        
        # 4. 批量查询所有供应商
        all_suppliers = client.models.Supplier.find(is_active=True)
        if not all_suppliers:
            return {"success": False, "error": "没有找到供应商数据"}
        all_suppliers = list(all_suppliers)
        supplier_id_list = [s.supplier_id for s in all_suppliers]
        
        # 5. 【核心优化】批量查询供应商-物料关系
        # 原方案: for s in suppliers: for m in materials: sm = client.models.SupplierMaterial.find(supplier_id=s.supplier_id, material_id=m.material_id)
        # 优化后: 一次性查询所有供应商-物料关系，用__in批量查询
        all_sm = client.models.SupplierMaterial.find(
            supplier_id__in=supplier_id_list,
            material_id__in=material_id_list
        )
        
        # 构建供应商-物料关系字典，用于快速查找
        # Key: (supplier_id, material_id) -> Value: SupplierMaterial对象
        sm_dict = {}
        for sm in all_sm:
            sm_dict[(sm.supplier_id, sm.material_id)] = sm
        
        # 6. 批量查询库存数据
        all_inventories = client.models.Inventory.find(material_id__in=material_id_list)
        inventory_map = {inv.material_id: inv.available_quantity for inv in all_inventories}
        
        # 7. 批量查询工单物料需求
        all_woms = client.models.WorkOrderMaterial.find(material_id__in=material_id_list)
        
        # 8. 计算每个物料的需求量（基于工单需求 - 当前库存）
        demand_map = {}
        for m in materials:
            material_id = m.material_id
            
            # 计算该物料的总工单需求
            wo_demand = 0
            for wom in all_woms:
                if wom.material_id == material_id:
                    wo_demand += (wom.required_quantity or 0)
            
            # 计算当前库存
            current_inv = inventory_map.get(material_id, 0)
            
            # 需求缺口 = 工单需求 - 当前库存
            demand = max(0, wo_demand - current_inv)
            
            # 考虑安全库存
            safety_stock = m.safety_stock_level or 0
            demand = max(demand, safety_stock - current_inv)
            
            if demand > 0:
                demand_map[material_id] = {
                    "wo_demand": wo_demand,
                    "current_inv": current_inv,
                    "safety_stock": safety_stock,
                    "demand": demand
                }
        
        # 9. 构建供应商-物料可行列表
        # 只有demand>0且有供应商-物料关系的才参与优化
        feasible_pairs = []
        for m in materials:
            material_id = m.material_id
            if material_id not in demand_map:
                continue
            
            for s in all_suppliers:
                supplier_id = s.supplier_id
                sm_key = (supplier_id, material_id)
                
                if sm_key in sm_dict:
                    sm = sm_dict[sm_key]
                    feasible_pairs.append({
                        "supplier": s,
                        "material": m,
                        "sm": sm,
                        "demand": demand_map[material_id]["demand"]
                    })
        
        if not feasible_pairs:
            return {"success": False, "error": "没有找到可行的供应商-物料组合"}
        
        # 10. 创建MIP求解器（CBC是混合整数规划求解器，支持0-1变量）
        solver = pywraplp.Solver.CreateSolver('CBC')
        if not solver:
            return {"success": False, "error": "无法创建求解器"}
        
        # 11. 创建决策变量
        # X[supplier_id, material_id]: 采购量（连续变量）
        # Y[supplier_id, material_id]: 是否选择该供应商（0-1变量）
        x_vars = {}
        y_vars = {}
        
        for pair in feasible_pairs:
            s = pair["supplier"]
            m = pair["material"]
            sm = pair["sm"]
            
            supplier_id = s.supplier_id
            material_id = m.material_id
            key = (supplier_id, material_id)
            
            # Y变量: 0-1变量，是否选择该供应商
            y_vars[key] = solver.IntVar(0, 1, f'y_{supplier_id}_{material_id}')
            
            # X变量: 采购量，上界为供应商最大订购量
            max_qty = sm.max_order_qty if hasattr(sm, 'max_order_qty') and sm.max_order_qty else 1000000
            x_vars[key] = solver.NumVar(0, max_qty, f'x_{supplier_id}_{material_id}')
        
        # 12. 添加约束
        
        # 约束1: 需求满足 ΣX[s,m] >= demand[m]
        for m in materials:
            material_id = m.material_id
            if material_id not in demand_map:
                continue
            
            demand = demand_map[material_id]["demand"]
            expr = solver.Sum([
                x_vars.get((s.supplier_id, material_id), solver.NumVar(0, 0, ''))
                for s in all_suppliers
                if (s.supplier_id, material_id) in x_vars
            ])
            solver.Add(expr >= demand)
        
        # 约束2: 供应商容量 X[s,m] <= capacity[s,m] × Y[s,m]
        # 约束3: 最小订单量 X[s,m] >= min_order[s,m] × Y[s,m]
        for key in x_vars:
            supplier_id, material_id = key
            x = x_vars[key]
            y = y_vars[key]
            
            # 获取供应商-物料关系
            sm_key = (supplier_id, material_id)
            if sm_key not in sm_dict:
                continue
            
            sm = sm_dict[sm_key]
            
            # 供应商最大订购量约束
            max_qty = sm.max_order_qty if hasattr(sm, 'max_order_qty') and sm.max_order_qty else 1000000
            solver.Add(x <= max_qty * y)
            
            # 最小订单量约束
            min_order = sm.min_order_qty or 0
            if min_order > 0:
                solver.Add(x >= min_order * y)
        
        # 约束4: 每个物料最多选择max_suppliers个供应商
        for m in materials:
            material_id = m.material_id
            if material_id not in demand_map:
                continue
            
            expr = solver.Sum([
                y_vars.get((s.supplier_id, material_id), solver.IntVar(0, 0, ''))
                for s in all_suppliers
                if (s.supplier_id, material_id) in y_vars
            ])
            solver.Add(expr <= max_suppliers)
        
        # 13. 目标函数：最小化总采购成本
        objective = solver.Objective()
        for key in x_vars:
            supplier_id, material_id = key
            
            # 获取单价
            sm_key = (supplier_id, material_id)
            if sm_key not in sm_dict:
                continue
            
            sm = sm_dict[sm_key]
            unit_price = sm.unit_price or 0
            
            objective.SetCoefficient(x_vars[key], unit_price)
        objective.SetMinimization()
        
        # 14. 求解
        solver.SetTimeLimit(30000)
        solver.EnableOutput()
        status = solver.Solve()
        
        if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            return {"success": False, "error": "求解失败"}
        
        # 15. 解析结果
        purchase_plan = []
        total_cost = 0
        
        for key in x_vars:
            supplier_id, material_id = key
            x_val = x_vars[key].solution_value()
            y_val = y_vars[key].solution_value()
            
            # 只保留有采购量的记录
            if x_val > 0.1:
                sm_key = (supplier_id, material_id)
                sm = sm_dict[sm_key]
                
                # 获取物料和供应商名称
                material_name = None
                for m in materials:
                    if m.material_id == material_id:
                        material_name = m.material_name
                        break
                
                supplier_name = None
                for s in all_suppliers:
                    if s.supplier_id == supplier_id:
                        supplier_name = s.supplier_name
                        break
                
                cost = x_val * (sm.unit_price or 0)
                total_cost += cost
                
                purchase_plan.append({
                    "supplier_id": supplier_id,
                    "supplier_name": supplier_name,
                    "material_id": material_id,
                    "material_name": material_name,
                    "quantity": round(x_val, 2),
                    "unit_price": sm.unit_price or 0,
                    "cost": round(cost, 2),
                    "selected": y_val > 0.5
                })
        
        # 按成本排序
        purchase_plan.sort(key=lambda x: x["cost"], reverse=True)
        
        # 按供应商聚合分析
        supplier_cost_map = {}
        for item in purchase_plan:
            sid = item["supplier_id"]
            if sid not in supplier_cost_map:
                supplier_cost_map[sid] = {"supplier_name": item["supplier_name"], "total_cost": 0, "item_count": 0}
            supplier_cost_map[sid]["total_cost"] += item["cost"]
            supplier_cost_map[sid]["item_count"] += 1
        
        # 生成供应商建议
        supplier_recommendations = []
        for sid, info in sorted(supplier_cost_map.items(), key=lambda x: x[1]["total_cost"], reverse=True):
            supplier_recommendations.append({
                "supplier_id": sid,
                "supplier_name": info["supplier_name"],
                "total_cost": round(info["total_cost"], 2),
                "item_count": info["item_count"],
                "recommendation": "主要供应商" if info["total_cost"] > total_cost * 0.3 else "次要供应商"
            })
        
        result = {
            "total_cost": round(total_cost, 2),
            "total_purchase_items": len(purchase_plan),
            "purchase_plan": purchase_plan,
            "supplier_summary": supplier_recommendations,
            "forecast_days": forecast_days,
            "material_demands": {
                mid: {
                    "demand": demand_map[mid]["demand"],
                    "wo_demand": demand_map[mid]["wo_demand"],
                    "current_inv": demand_map[mid]["current_inv"]
                }
                for mid in demand_map
            },
            "cost_breakdown": {
                "total_cost": round(total_cost, 2),
                "avg_cost_per_item": round(total_cost / len(purchase_plan), 2) if purchase_plan else 0,
                "supplier_count": len(supplier_cost_map)
            }
        }
        
        return {
            "success": True,
            "message": f"采购计划优化完成，总成本: ¥{total_cost:.2f}",
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}


result = execute_optimize_purchase_plan(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入采购计划优化Action")
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
            print("\n[SUCCESS] 采购计划优化Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   求解器类型: MIP (CBC)")
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
