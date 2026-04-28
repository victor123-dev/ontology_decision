"""
导入采购计划优化Action到本体

Action: optimizePurchasePlan
功能: 优化未来30天的采购计划，最小化采购成本
求解器: MIP (CBC)
难度: ⭐⭐
"""
import requests
import json

# API配置
API_URL = "http://localhost:8080/api/v1"

# Action定义
ACTION_DATA = {
    "id": "optimize_purchase_plan",
    "api_name": "OptimizePurchasePlan",
    "name": "采购计划优化",
    "description": "基于物料需求、供应商信息、库存状态，优化采购计划以最小化总采购成本",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "material",
    "parameters": [
        {
            "name": "material_ids",
            "type": "array",
            "required": False,
            "description": "要优化的物料ID列表，为空则优化所有物料"
        },
        {
            "name": "planning_days",
            "type": "integer",
            "required": False,
            "description": "采购规划的时间范围，默认30天"
        },
        {
            "name": "budget_limit",
            "type": "float",
            "required": False,
            "description": "总预算上限"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 采购计划优化函数实现 - 使用 Ontology SDK + OR-Tools
import json
from datetime import datetime, timedelta
from ortools.linear_solver import pywraplp

# 使用 SDK
from my_ontology_sdk import OntologyClient

def execute_optimize_purchase_plan(parameters):
    """
    采购计划优化 - MIP模型
    
    数学模型:
    - 决策变量: y[m,s,t]采购数量, z[m,s,t]是否采购, I[m,t]库存
    - 目标函数: Minimize Σ(P[m,s] * y[m,s,t])
    - 约束条件:
      1. 库存平衡: I[m,t] = I[m,t-1] + Σy[m,s,t-L[m,s]] - D[m,t]
      2. 最小订购量: y[m,s,t] >= MOQ[m,s] * z[m,s,t]
      3. 非负库存: I[m,t] >= 0
      4. 预算限制: Σ(P[m,s] * y[m,s,t]) <= B
    
    Args:
        parameters: 包含material_ids, planning_days, budget_limit等参数
    Returns:
        dict: 优化后的采购计划
    """
    try:
        # 1. 解析参数
        material_ids = parameters.get("material_ids", [])
        planning_days = parameters.get("planning_days", 30)
        budget_limit = parameters.get("budget_limit")
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # 3. 获取物料数据
        if material_ids:
            materials = []
            for mid in material_ids:
                mat = client.models.Material.get(mid)
                if mat:
                    materials.append(mat)
        else:
            materials = client.models.Material.find()
        
        if not materials:
            return {"success": False, "error": "没有找到物料数据"}
        
        # 4. 获取供应商数据
        suppliers = client.models.Supplier.find(is_active=True)
        if not suppliers:
            return {"success": False, "error": "没有可用供应商"}
        
        # 5. 创建MIP求解器
        solver = pywraplp.Solver.CreateSolver('CBC')
        if not solver:
            return {"success": False, "error": "无法创建求解器"}
        
        # 6. 准备数据
        days = range(planning_days)
        materials_list = list(materials)
        suppliers_list = list(suppliers)
        
        # 7. 创建决策变量
        y = {}  # 采购数量 y[m,s,t]
        z = {}  # 是否采购 z[m,s,t]
        
        # 只对有供应关系的物料-供应商组合创建变量
        valid_combinations = []
        for m in materials_list:
            for s in suppliers_list:
                # 检查供应商是否能供应此物料
                sm_records = client.models.SupplierMaterial.find(
                    supplier_id=s.supplier_id,
                    material_id=m.material_id
                )
                
                if sm_records:
                    sm = sm_records[0]
                    valid_combinations.append((m, s, sm))
                    
                    for t in days:
                        y[m.material_id, s.supplier_id, t] = solver.NumVar(
                            0, 1000000, f'y_{m.material_id}_{s.supplier_id}_{t}'
                        )
                        z[m.material_id, s.supplier_id, t] = solver.IntVar(
                            0, 1, f'z_{m.material_id}_{s.supplier_id}_{t}'
                        )
                        
                        # 最小订购量约束
                        moq = sm.min_order_qty or 0
                        solver.Add(y[m.material_id, s.supplier_id, t] >= moq * z[m.material_id, s.supplier_id, t])
                        solver.Add(y[m.material_id, s.supplier_id, t] <= 1000000 * z[m.material_id, s.supplier_id, t])
        
        if not valid_combinations:
            return {"success": False, "error": "没有有效的物料-供应商组合"}
        
        # 库存变量
        I = {}
        for m in materials_list:
            for t in days:
                I[m.material_id, t] = solver.NumVar(0, 1000000, f'I_{m.material_id}_{t}')
        
        # 8. 添加约束
        
        # 约束1: 库存平衡方程
        for m in materials_list:
            # 获取当前库存
            inv_records = client.models.Inventory.find(material_id=m.material_id)
            current_inv = inv_records[0].available_quantity if inv_records else 0
            
            for t in days:
                # 计算当天需求量
                demand = _get_production_demand(client, m.material_id, t)
                
                # 计算当天到货量（考虑交期）
                receipts = []
                for s, sm in [(item[1], item[2]) for item in valid_combinations if item[0].material_id == m.material_id]:
                    lead_time = sm.lead_time_days or 0
                    if t >= lead_time:
                        receipts.append(y[m.material_id, s.supplier_id, t - lead_time])
                
                receipt_sum = sum(receipts) if receipts else 0
                
                if t == 0:
                    solver.Add(I[m.material_id, t] == current_inv + receipt_sum - demand)
                else:
                    solver.Add(I[m.material_id, t] == I[m.material_id, t-1] + receipt_sum - demand)
                
                # 约束2: 非负库存（不允许缺货）
                solver.Add(I[m.material_id, t] >= 0)
        
        # 9. 目标函数：最小化总采购成本
        objective = solver.Objective()
        for m, s, sm in valid_combinations:
            unit_price = sm.unit_price or 0
            for t in days:
                objective.SetCoefficient(y[m.material_id, s.supplier_id, t], unit_price)
        objective.SetMinimization()
        
        # 10. 预算约束（如果指定）
        if budget_limit:
            budget_expr = []
            for m, s, sm in valid_combinations:
                unit_price = sm.unit_price or 0
                for t in days:
                    budget_expr.append(unit_price * y[m.material_id, s.supplier_id, t])
            
            if budget_expr:
                solver.Add(sum(budget_expr) <= budget_limit)
        
        # 11. 求解
        solver.SetTimeLimit(30000)  # 30秒
        status = solver.Solve()
        
        # 12. 解析结果
        if status == pywraplp.Solver.OPTIMAL:
            purchase_plan = []
            total_cost = 0
            
            for m, s, sm in valid_combinations:
                for t in days:
                    qty = y[m.material_id, s.supplier_id, t].solution_value()
                    if qty > 0.1:  # 阈值过滤
                        cost = qty * (sm.unit_price or 0)
                        total_cost += cost
                        
                        # 计算到货日期
                        lead_time = sm.lead_time_days or 0
                        delivery_date = datetime.now() + timedelta(days=t + lead_time)
                        
                        purchase_plan.append({
                            "material_id": m.material_id,
                            "material_name": m.material_name,
                            "supplier_id": s.supplier_id,
                            "supplier_name": s.supplier_name,
                            "order_date": (datetime.now() + timedelta(days=t)).strftime('%Y-%m-%d'),
                            "delivery_date": delivery_date.strftime('%Y-%m-%d'),
                            "quantity": round(qty, 2),
                            "unit_price": sm.unit_price,
                            "total_cost": round(cost, 2),
                            "lead_time_days": lead_time
                        })
            
            # 按日期排序
            purchase_plan.sort(key=lambda x: x['order_date'])
            
            result = {
                "planning_days": planning_days,
                "total_orders": len(purchase_plan),
                "total_cost": round(total_cost, 2),
                "budget_limit": budget_limit,
                "budget_used_percent": round((total_cost / budget_limit * 100) if budget_limit else 0, 2),
                "purchase_plan": purchase_plan
            }
            
            return {
                "success": True,
                "message": f"采购计划优化完成，总成本: ¥{total_cost:.2f}",
                "result": result
            }
        else:
            return {
                "success": False,
                "error": "无可行解，请检查约束条件"
            }
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}


def _get_production_demand(client, material_id, day_offset):
    """
    计算某天该物料的生产需求量
    """
    try:
        # 查询使用该物料的工单物料需求
        woms = client.models.WorkOrderMaterial.find(material_id=material_id)
        
        total_demand = 0
        today = datetime.now()
        
        for wom in woms:
            # 获取关联的工单工序
            wo_op = client.models.WorkOrderOperation.get(wom.wo_op_id)
            if wo_op and wo_op.planned_start:
                # 计算工序开始日期
                start_date = datetime.fromisoformat(wo_op.planned_start) if isinstance(wo_op.planned_start, str) else wo_op.planned_start
                days_diff = (start_date - today).days
                
                if days_diff == day_offset:
                    total_demand += wom.required_quantity or 0
        
        return total_demand
    except:
        return 0


# 必须定义result变量供Action框架使用
result = execute_optimize_purchase_plan(parameters)
'''
}

def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入采购计划优化Action")
    print("=" * 60)
    
    # 发送POST请求创建Action
    response = requests.post(
        f"{API_URL}/actions",
        json=ACTION_DATA,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        print("[SUCCESS] 采购计划优化Action导入成功")
        print(f"   Action ID: {ACTION_DATA['id']}")
        print(f"   Action Name: {ACTION_DATA['name']}")
        print(f"   求解器类型: MIP (CBC)")
        print(f"   实现难度: 2星")
        return True
    else:
        print(f"[FAILED] 导入失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
        return False


if __name__ == "__main__":
    success = import_action()
    exit(0 if success else 1)
