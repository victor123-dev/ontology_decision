"""
导入紧急采购Action到本体

Action: emergencyPurchase
功能: 创建紧急采购订单（快速响应低库存预警）
难度: ⭐
"""
import requests
from datetime import datetime
import uuid

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "emergency_purchase",
    "api_name": "EmergencyPurchase",
    "name": "紧急采购",
    "description": "创建紧急采购订单，快速响应低库存预警。自动设置较高的优先级和较短的期望交期，确保物料快速到货。当库存低于安全库存、需要紧急补货或产线缺料时使用。返回采购订单ID和预计到货时间。",
    "action_type": "function",
    "operation": "create",
    "target_model_id": "purchase_order",
    "parameters": [
        {
            "name": "material_id",
            "type": "string",
            "required": True,
            "description": "需要采购的物料ID。示例：'MAT-DIE-BGA'"
        },
        {
            "name": "quantity",
            "type": "float",
            "required": True,
            "description": "采购数量。示例：100.0"
        },
        {
            "name": "supplier_id",
            "type": "string",
            "required": True,
            "description": "供应商ID。示例：'SUP-001'"
        },
        {
            "name": "urgency_level",
            "type": "string",
            "required": False,
            "description": "紧急程度：'high'（紧急，3天交期）或'normal'（普通，7天交期）。默认'high'"
        },
        {
            "name": "reason",
            "type": "string",
            "required": False,
            "description": "采购原因说明。示例：'库存低于安全库存，需要紧急补货'"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 紧急采购 - 创建紧急采购订单
import json
import uuid
from datetime import datetime, timedelta
from my_ontology_sdk import OntologyClient

def execute_emergency_purchase(parameters):
    """
    紧急采购 - 创建高优先级采购订单
    
    业务逻辑:
    1. 验证物料和供应商是否存在
    2. 查询供应商-物料关系获取价格和交期
    3. 创建采购订单（状态=已创建，优先级=紧急）
    4. 创建采购订单行
    5. 计算期望交期（紧急3天，普通7天）
    6. 返回采购订单详情
    """
    try:
        # 1. 解析参数
        material_id = parameters.get("material_id")
        quantity = parameters.get("quantity")
        supplier_id = parameters.get("supplier_id")
        urgency_level = parameters.get("urgency_level", "high")
        reason = parameters.get("reason", "紧急补货")
        
        if not material_id or not quantity or not supplier_id:
            return {"success": False, "error": "请提供物料ID、采购数量和供应商ID"}
        
        if quantity <= 0:
            return {"success": False, "error": "采购数量必须大于0"}
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # 3. 验证物料是否存在
        materials = client.models.Material.find(material_id=material_id)
        if not materials:
            return {"success": False, "error": f"物料 {material_id} 不存在"}
        
        material = materials[0]
        material_name = getattr(material, 'material_name', material_id)
        
        # 4. 验证供应商是否存在
        suppliers = client.models.Supplier.find(supplier_id=supplier_id)
        if not suppliers:
            return {"success": False, "error": f"供应商 {supplier_id} 不存在"}
        
        supplier = suppliers[0]
        supplier_name = getattr(supplier, 'supplier_name', supplier_id)
        
        # 5. 查询供应商-物料关系（获取价格和交期）
        supplier_materials = client.models.SupplierMaterial.find(
            supplier_id=supplier_id,
            material_id=material_id
        )
        
        if not supplier_materials:
            return {
                "success": False,
                "error": f"供应商 {supplier_name} 不供应物料 {material_name}"
            }
        
        sm = supplier_materials[0]
        unit_price = getattr(sm, 'unit_price', 0)
        standard_lead_time = getattr(sm, 'lead_time_days', 7)
        
        # 6. 计算期望交期
        if urgency_level == "high":
            lead_time_days = min(3, standard_lead_time)  # 紧急最多3天
            priority = 1  # 最高优先级
            order_type = "紧急采购"
        else:
            lead_time_days = standard_lead_time
            priority = 2  # 普通优先级
            order_type = "普通采购"
        
        # TODO expected_delivery_date = datetime.now() + timedelta(days=lead_time_days)
        expected_delivery_date = datetime(2026, 4, 26) + timedelta(days=lead_time_days)
        
        # 7. 生成采购订单ID
        # 使用UUID避免并发冲突
        po_id = f"PO-EMG-{uuid.uuid4().hex[:8].upper()}"
        
        # 8. 创建采购订单
        po_data = {
            "po_id": po_id,
            "supplier_id": supplier_id,
            "order_date": datetime(2026, 4, 26).isoformat(),  # TODO datetime.now().isoformat(),
            "expected_delivery_date": expected_delivery_date.isoformat(),
            "status": "已创建",
            "total_amount": round(quantity * unit_price, 2),
            "created_by": "紧急采购系统",
            "note": f"{reason} | 紧急程度: {urgency_level} | 优先级: {priority} | 类型: {order_type}"
        }
        
        # 使用SDK创建采购订单
        created_po = client.models.PurchaseOrder.create(**po_data)
        
        if not created_po:
            return {"success": False, "error": "创建采购订单失败"}
        
        # 9. 创建采购订单行
        line_id = f"POL-{po_id}-001"
        pol_data = {
            "line_id": line_id,
            "po_id": po_id,
            "material_id": material_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "received_quantity": 0.0,
            "status": "未开始"
        }
        
        created_pol = client.models.PurchaseOrderLine.create(**pol_data)
        
        if not created_pol:
            return {
                "success": False,
                "error": "创建采购订单行失败",
                "po_id": po_id,
                "line_id": line_id
            }
        
        # 10. 构建结果数据
        result = {
            "po_id": po_id,
            "line_id": line_id,
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "material_id": material_id,
            "material_name": material_name,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_amount": round(quantity * unit_price, 2),
            "expected_delivery_date": expected_delivery_date.isoformat(),
            "lead_time_days": lead_time_days,
            "priority": priority,
            "order_type": order_type,
            "urgency_level": urgency_level,
            "created_at": datetime.now().isoformat()
        }
        
        # 11. 返回成功结果
        return {
            "success": True,
            "message": f"紧急采购订单创建成功",
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": f"创建紧急采购订单失败: {str(e)}"}

result = execute_emergency_purchase(parameters)
'''
}


def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入紧急采购Action")
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
            print("\n[SUCCESS] 紧急采购Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   求解器类型: 业务逻辑")
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
