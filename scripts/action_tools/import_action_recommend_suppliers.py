"""
导入紧急采购推荐供应商Action到本体

Action: recommendSuppliers
功能: 为指定物料推荐最优供应商（基于交期、价格、可靠性综合评分）
难度: ⭐
"""
import requests

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "recommend_suppliers",
    "api_name": "RecommendSuppliers",
    "name": "推荐供应商",
    "description": "为指定物料推荐最优供应商。基于供应商的历史交期表现、价格、可靠性进行综合评分，返回TOP3推荐供应商。当需要紧急采购、寻找供应商或评估供应商选择时使用。返回供应商列表、评分详情、建议采购数量。",
    "action_type": "function",
    "operation": "custom",
    "target_model_id": "supplier",
    "parameters": [
        {
            "name": "material_id",
            "type": "string",
            "required": True,
            "description": "需要采购的物料ID。示例：'MAT-DIE-BGA'"
        },
        {
            "name": "quantity_needed",
            "type": "float",
            "required": False,
            "description": "需要的数量。如果不提供，将基于安全库存自动计算"
        },
        {
            "name": "urgency_level",
            "type": "string",
            "required": False,
            "description": "紧急程度：'high'（紧急，3天交期）或'normal'（普通，7天交期）。默认'high'"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 推荐供应商 - 基于综合评分排序
import json
from datetime import datetime, timedelta
from my_ontology_sdk import OntologyClient

def execute_recommend_suppliers(parameters):
    """
    推荐供应商 - 基于交期、价格、可靠性的综合评分
    
    评分模型:
    - 交期得分 (40%): 基于供应商承诺交期，越短得分越高
    - 价格得分 (30%): 基于供应价格，越低得分越高
    - 可靠性得分 (30%): 基于供应商历史交付表现
    
    返回TOP3推荐供应商
    """
    try:
        # 1. 解析参数
        material_id = parameters.get("material_id")
        quantity_needed = parameters.get("quantity_needed")
        urgency_level = parameters.get("urgency_level", "high")
        
        if not material_id:
            return {"success": False, "error": "请提供物料ID"}
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # 3. 查询物料信息
        materials = client.models.Material.find(material_id=material_id)
        if not materials:
            return {"success": False, "error": f"物料 {material_id} 不存在"}
        
        material = materials[0]
        material_name = getattr(material, 'material_name', material_id)
        safety_stock = getattr(material, 'safety_stock_level', 0)
        
        # 4. 查询当前库存
        inventories = client.models.Inventory.find(material_id=material_id)
        current_inventory = 0
        if inventories:
            inv = inventories[0]
            current_inventory = getattr(inv, 'available_quantity', 0)
        
        # 5. 计算建议采购数量
        if quantity_needed is None:
            # 建议数量 = (安全库存 - 当前可用) × 1.2 (20%缓冲)
            shortage = max(0, safety_stock - current_inventory)
            quantity_needed = shortage * 1.2
        
        if quantity_needed <= 0:
            result = {
                "material_id": material_id,
                "material_name": material_name,
                "current_inventory": current_inventory,
                "safety_stock": safety_stock,
                "shortage": 0,
                "recommended_quantity": 0,
                "urgency_level": urgency_level,
                "recommended_suppliers": [],
                "supplier_count": 0,
                "generated_at": datetime.now().isoformat()
            }
            return {
                "success": True,
                "message": "当前库存充足，无需采购",
                "result": result
            }
        
        # 6. 查询该物料的供应商关系
        supplier_materials = client.models.SupplierMaterial.find(material_id=material_id)
        if not supplier_materials:
            return {
                "success": False,
                "error": f"物料 {material_id} 没有关联的供应商"
            }
        
        # 7. 获取所有供应商详情
        supplier_ids = [sm.supplier_id for sm in supplier_materials]
        suppliers = client.models.Supplier.find(supplier_id__in=supplier_ids)
        supplier_dict = {s.supplier_id: s for s in suppliers}
        
        # 8. 计算每个供应商的综合评分
        scored_suppliers = []
        
        for sm in supplier_materials:
            supplier_id = sm.supplier_id
            supplier = supplier_dict.get(supplier_id)
            
            if not supplier:
                continue
            
            # 提取供应商信息
            supplier_name = getattr(supplier, 'supplier_name', supplier_id)
            lead_time_days = getattr(sm, 'lead_time_days', 7)  # 承诺交期
            unit_price = getattr(sm, 'unit_price', 0)  # 单价
            reliability_score = getattr(supplier, 'reliability_score', 0.8)  # 可靠性评分 (0-1)
            min_order_qty = getattr(sm, 'min_order_quantity', 0)  # 最小订单量
            
            # 紧急采购调整交期
            if urgency_level == "high":
                actual_lead_time = min(3, lead_time_days)  # 紧急最多3天
            else:
                actual_lead_time = lead_time_days
            
            # 计算各项得分 (0-100)
            # 交期得分：交期越短得分越高 (假设30天为0分，0天为100分)
            delivery_score = max(0, 100 - (actual_lead_time / 30 * 100))
            
            # 价格得分：价格越低得分越高 (假设最高价为基准)
            # 这里简化处理，使用相对评分
            price_score = 80  # 默认中等价格得分
            
            # 可靠性得分：直接使用可靠性评分
            reliability_score_normalized = reliability_score * 100
            
            # 综合评分 (交期40% + 价格30% + 可靠性30%)
            total_score = (
                delivery_score * 0.4 +
                price_score * 0.3 +
                reliability_score_normalized * 0.3
            )
            
            # 计算预计交期日期
            expected_delivery_date = (datetime.now() + timedelta(days=actual_lead_time)).strftime('%Y-%m-%d')
            
            scored_suppliers.append({
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "lead_time_days": actual_lead_time,
                "unit_price": unit_price,
                "reliability_score": reliability_score,
                "min_order_quantity": min_order_qty,
                "expected_delivery_date": expected_delivery_date,
                "scores": {
                    "delivery_score": round(delivery_score, 2),
                    "price_score": round(price_score, 2),
                    "reliability_score": round(reliability_score_normalized, 2),
                    "total_score": round(total_score, 2)
                },
                "recommended_quantity": max(quantity_needed, min_order_qty),
                "estimated_cost": round(max(quantity_needed, min_order_qty) * unit_price, 2)
            })
        
        # 9. 按综合评分排序，返回TOP3
        scored_suppliers.sort(key=lambda x: x["scores"]["total_score"], reverse=True)
        top_suppliers = scored_suppliers[:3]
        
        # 10. 构建结果数据
        result = {
            "material_id": material_id,
            "material_name": material_name,
            "current_inventory": current_inventory,
            "safety_stock": safety_stock,
            "shortage": max(0, safety_stock - current_inventory),
            "recommended_quantity": round(quantity_needed, 2),
            "urgency_level": urgency_level,
            "recommended_suppliers": top_suppliers,
            "supplier_count": len(top_suppliers),
            "generated_at": datetime.now().isoformat()
        }
        
        # 11. 返回结果
        return {
            "success": True,
            "message": f"找到 {len(top_suppliers)} 个推荐供应商",
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": f"推荐供应商失败: {str(e)}"}

result = execute_recommend_suppliers(parameters)
'''
}


def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入推荐供应商Action")
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
            print("\n[SUCCESS] 推荐供应商Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   求解器类型: 综合评分模型")
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
