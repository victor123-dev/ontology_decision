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
    "description": "预测未来指定天数内哪些物料会出现短缺，输出缺料清单、缺口数量、影响工单等信息",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "material",
    "parameters": [
        {
            "name": "forecast_days",
            "type": "integer",
            "required": False,
            "description": "预测未来多少天的缺料情况，默认30天"
        },
        {
            "name": "material_ids",
            "type": "array",
            "required": False,
            "description": "要预测的物料ID列表，为空则预测所有物料"
        },
        {
            "name": "safety_stock_threshold",
            "type": "float",
            "required": False,
            "description": "安全库存阈值，为空则使用物料自身的安全库存"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 缺料预测函数实现 - 使用 Ontology SDK + OR-Tools
import json
from datetime import datetime, timedelta
from ortools.linear_solver import pywraplp

# 使用 SDK
from my_ontology_sdk import OntologyClient

def execute_predict_material_shortage(parameters):
    """
    缺料预测 - LP模型
    
    数学模型:
    - 决策变量: I[m,t]库存量, G[m,t]缺料量
    - 目标函数: Minimize ΣG[m,t] (虚拟目标)
    - 约束条件:
      1. 库存平衡: I[m,t] = I[m,t-1] + R[m,t] - D[m,t]
      2. 缺料计算: G[m,t] >= safety_stock - I[m,t]
      3. 非负约束: G[m,t] >= 0
    
    Args:
        parameters: 包含forecast_days, material_ids等参数
    Returns:
        dict: 缺料预测结果
    """
    try:
        # 1. 解析参数
        forecast_days = parameters.get("forecast_days", 30)
        material_ids = parameters.get("material_ids", [])
        safety_stock_threshold = parameters.get("safety_stock_threshold")
        
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
        
        # 4. 创建LP求解器
        solver = pywraplp.Solver.CreateSolver('GLOP')
        if not solver:
            return {"success": False, "error": "无法创建求解器"}
        
        # 5. 准备数据
        days = range(forecast_days)
        materials_list = list(materials)
        
        # 6. 创建决策变量
        inventory = {}  # I[m,t]
        shortage = {}   # G[m,t]
        
        for m in materials_list:
            # 获取当前库存
            inv_records = client.models.Inventory.find(material_id=m.material_id)
            current_inv = inv_records[0].available_quantity if inv_records else 0
            
            # 初始库存 (t=0)
            inventory[m.material_id, 0] = solver.NumVar(0, 1000000, f'inv_{m.material_id}_0')
            inventory[m.material_id, 0].ub = current_inv
            inventory[m.material_id, 0].lb = current_inv
            
            for t in days:
                if t > 0:
                    inventory[m.material_id, t] = solver.NumVar(
                        0, 1000000, f'inv_{m.material_id}_{t}'
                    )
                
                # 缺料量变量
                shortage[m.material_id, t] = solver.NumVar(
                    0, 1000000, f'short_{m.material_id}_{t}'
                )
        
        # 7. 添加约束
        
        # 约束1: 库存平衡方程
        for m in materials_list:
            for t in days:
                if t == 0:
                    continue
                
                # 计算当天的需求（从生产计划）
                demand = _get_production_demand(client, m.material_id, t)
                
                # 计算当天的到货（在途采购）
                receipt = _get_po_receipts(client, m.material_id, t)
                
                # 库存平衡: I[t] = I[t-1] + receipt - demand
                solver.Add(
                    inventory[m.material_id, t] == 
                    inventory[m.material_id, t-1] + receipt - demand
                )
        
        # 约束2: 缺料量计算
        for m in materials_list:
            safety_stock = safety_stock_threshold if safety_stock_threshold else m.safety_stock_level or 0
            
            for t in days:
                # G[m,t] >= safety_stock - I[m,t]
                solver.Add(
                    shortage[m.material_id, t] >= safety_stock - inventory[m.material_id, t]
                )
                # G[m,t] >= 0 (已通过变量定义保证)
        
        # 8. 目标函数（虚拟：最小化总缺料量）
        objective = solver.Objective()
        for m in materials_list:
            for t in days:
                objective.SetCoefficient(shortage[m.material_id, t], 1)
        objective.SetMinimization()
        
        # 9. 求解
        solver.SetTimeLimit(5000)  # 5秒
        status = solver.Solve()
        
        # 10. 解析结果
        if status != pywraplp.Solver.OPTIMAL:
            return {"success": False, "error": "求解失败"}
        
        shortages = []
        for m in materials_list:
            for t in days:
                gap = shortage[m.material_id, t].solution_value()
                if gap > 0.1:  # 阈值过滤
                    inv_level = inventory[m.material_id, t].solution_value()
                    
                    # 查询影响的工单
                    affected_wos = _get_affected_work_orders(client, m.material_id, t)
                    
                    shortages.append({
                        "material_id": m.material_id,
                        "material_name": m.material_name,
                        "date_offset_days": t,
                        "shortage_qty": round(gap, 2),
                        "inventory_level": round(inv_level, 2),
                        "safety_stock": safety_stock,
                        "affected_work_orders": affected_wos
                    })
        
        # 11. 构建返回结果
        result = {
            "forecast_days": forecast_days,
            "total_shortages": len(shortages),
            "shortage_details": shortages,
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "message": f"缺料预测完成，发现 {len(shortages)} 个缺料点",
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": f"执行失败: {str(e)}"}


def _get_production_demand(client, material_id, day_offset):
    """
    计算某天该物料的生产需求量
    
    逻辑: 
    1. 查询使用该物料的工单工序
    2. 根据工序计划时间计算当天的需求
    """
    try:
        # 查询使用该物料的工单物料需求
        woms = client.models.WorkOrderMaterial.find(material_id=material_id)
        
        total_demand = 0
        for wom in woms:
            # 获取关联的工单工序
            wo_op = client.models.WorkOrderOperation.get(wom.wo_op_id)
            if wo_op and wo_op.planned_start:
                # 计算工序开始日期
                start_date = datetime.fromisoformat(wo_op.planned_start) if isinstance(wo_op.planned_start, str) else wo_op.planned_start
                today = datetime.now()
                days_diff = (start_date - today).days
                
                if days_diff == day_offset:
                    total_demand += wom.required_quantity or 0
        
        return total_demand
    except:
        return 0


def _get_po_receipts(client, material_id, day_offset):
    """
    计算某天的采购到货量
    
    逻辑:
    1. 查询该物料的在途采购订单
    2. 根据预期交货日期计算当天的到货
    """
    try:
        # 查询采购订单行
        po_lines = client.models.PurchaseOrderLine.find(material_id=material_id)
        
        total_receipt = 0
        today = datetime.now()
        
        for line in po_lines:
            if line.status in ['已确认', '运输中']:
                # 获取采购订单
                po = client.models.PurchaseOrder.get(line.po_id)
                if po and po.expected_delivery_date:
                    delivery_date = datetime.fromisoformat(po.expected_delivery_date) if isinstance(po.expected_delivery_date, str) else po.expected_delivery_date
                    days_diff = (delivery_date - today).days
                    
                    if days_diff == day_offset:
                        total_receipt += line.quantity - (line.received_quantity or 0)
        
        return total_receipt
    except:
        return 0


def _get_affected_work_orders(client, material_id, day_offset):
    """
    查询受缺料影响的工单列表
    """
    try:
        woms = client.models.WorkOrderMaterial.find(material_id=material_id)
        affected_wos = []
        
        for wom in woms:
            if wom.shortage_quantity and wom.shortage_quantity > 0:
                wo = client.models.WorkOrder.get(wom.work_order_id)
                if wo:
                    affected_wos.append({
                        "work_order_id": wo.work_order_id,
                        "product_id": wo.product_id,
                        "status": wo.status
                    })
        
        return affected_wos[:5]  # 最多返回5个
    except:
        return []


# 必须定义result变量供Action框架使用
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
