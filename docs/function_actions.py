from app.dao.action_dao import get_action_dao

def create_emergency_procurement_function_action():
    """Create emergency procurement function action"""
    function_code = '''
# 紧急采购函数实现 - 使用 Ontology SDK
import json
from datetime import datetime

# 使用 SDK（必须在脚本末尾定义 result 变量）
from my_ontology_sdk import OntologyClient

def execute_emergency_procurement(parameters):
    """
    执行紧急采购流程
    Args:
        parameters: 包含对齐模型字段的参数字典
    Returns:
        dict: 执行结果
    """
    try:
        # 验证必需参数（使用模型字段名）
        required_params = ['item_code', 'item_name', 'quantity', 
                          'work_order_number', 'order_number', 'customer',
                          'urgency_level', 'demand_date']
        
        for param in required_params:
            if param not in parameters:
                return {"success": False, "error": f"Missing required parameter: {param}"}
        
        # 初始化 SDK 客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # 1. 创建请购单 (requisition) - 直接使用参数
        requisition_number = f"REQ-EMG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        requisition_data = {
            "requisition_number": requisition_number,
            "document_date": parameters.get("document_date", datetime.now().strftime('%Y-%m-%d')),
            "purchaser": parameters.get("purchaser", "SYSTEM"),
            "supplier": parameters.get("supplier", "SUP0001"),
            "source_document": "work_order",
            "source_number": parameters["work_order_number"],
            "status": "紧急"
        }
        
        requisition = client.models.Requisition.create(**requisition_data)
        if not requisition:
            return {"success": False, "error": "Failed to create requisition"}
        
        # 2. 创建请购单明细 (requisition_detail) - 直接使用参数
        requisition_detail_data = {
            "requisition_number": requisition_number,
            "sequence_number": parameters.get("sequence_number", 1),
            "item_code": parameters["item_code"],
            "item_name": parameters["item_name"],
            "specification": parameters.get("specification", ""),
            "unit_of_measure": parameters.get("unit_of_measure", "PCS"),
            "quantity": parameters["quantity"],
            "demand_date": parameters["demand_date"],
            "source_document": "work_order",
            "source_number": parameters["work_order_number"]
        }
        
        requisition_detail = client.models.RequisitionDetail.create(**requisition_detail_data)
        if not requisition_detail:
            return {"success": False, "error": "Failed to create requisition detail"}
        
        # 3. 创建采购订单 (purchase_order) - 直接使用参数
        purchase_order_number = f"PO-EMG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        purchase_order_data = {
            "purchase_order_number": purchase_order_number,
            "document_date": parameters.get("document_date", datetime.now().strftime('%Y-%m-%d')),
            "purchaser": parameters.get("purchaser", "SYSTEM"),
            "supplier": parameters.get("supplier", "SUP0001"),
            "delivery_address": parameters.get("delivery_address", "厂区A栋收货区"),
            "source_document": "requisition",
            "source_number": requisition_number,
            "status": "已创建"
        }
        
        purchase_order = client.models.PurchaseOrder.create(**purchase_order_data)
        if not purchase_order:
            return {"success": False, "error": "Failed to create purchase order"}
        
        # 4. 创建采购订单明细 (purchase_order_detail) - 直接使用参数
        po_detail_data = {
            "purchase_order_number": purchase_order_number,
            "sequence_number": parameters.get("sequence_number", 1),
            "item_code": parameters["item_code"],
            "item_name": parameters["item_name"],
            "specification": parameters.get("specification", ""),
            "unit_of_measure": parameters.get("unit_of_measure", "PCS"),
            "unit_price": parameters.get("unit_price", 0.0),
            "quantity": parameters["quantity"],
            "amount": parameters.get("amount", 0.0),
            "expected_delivery_date": parameters["demand_date"]
        }
        
        po_detail = client.models.PurchaseOrderDetail.create(**po_detail_data)
        if not po_detail:
            return {"success": False, "error": "Failed to create purchase order detail"}
        
        # 5. 记录预警消息 (alert_message) - 直接使用参数
        alert_message_data = {
            "message_id": f"ALERT-EMG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message_title": parameters.get("message_title", "紧急采购启动"),
            "message_content": parameters.get("message_content", f"已为工单 {parameters['work_order_number']} 启动紧急采购流程，物料: {parameters['item_code']}"),
            "rule_code": "EMERGENCY_PROCUREMENT",
            "recipient": parameters.get("purchaser", "SYSTEM"),
            "risk_level": parameters["urgency_level"]
        }
        
        alert_message = client.models.AlertMessage.create(**alert_message_data)
        
        return {
            "success": True,
            "message": "紧急采购流程已启动",
            "result": {
                "requisition_number": requisition_number,
                "purchase_order_number": purchase_order_number,
                "item_code": parameters["item_code"],
                "work_order_number": parameters["work_order_number"],
                "customer": parameters["customer"]
            }
        }
    
    except Exception as e:
        return {"success": False, "error": f"Emergency procurement failed: {str(e)}"}

# 执行函数并定义 result 变量（必须）
result = execute_emergency_procurement(parameters)
'''
    
    action_data = {
        "id": "emergency_procurement",
        "api_name": "EmergencyProcurement",
        "name": "紧急采购",
        "description": "为关键物料供应中断触发紧急采购流程，参数与业务模型字段完全对齐",
        "action_type": "function",
        "function_code": function_code,
        "parameters": [
            # Requisition/RequisitionDetail 字段
            {
                "name": "item_code",
                "type": "string",
                "required": True,
                "description": "品号"
            },
            {
                "name": "item_name",
                "type": "string",
                "required": True,
                "description": "品名"
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": True,
                "description": "数量"
            },
            {
                "name": "work_order_number",
                "type": "string",
                "required": True,
                "description": "工单编号"
            },
            {
                "name": "order_number",
                "type": "string",
                "required": True,
                "description": "销售订单编号"
            },
            {
                "name": "customer",
                "type": "string",
                "required": True,
                "description": "客户"
            },
            {
                "name": "urgency_level",
                "type": "string",
                "required": True,
                "description": "风险等级"   
            },
            {
                "name": "demand_date",
                "type": "date",
                "required": True,
                "description": "需求日期"
            },
            # 可选字段
            {
                "name": "document_date",
                "type": "date",
                "required": False,
                "default_value": "",
                "description": "单据日期"
            },
            {
                "name": "purchaser",
                "type": "string",
                "required": False,
                "default_value": "SYSTEM",
                "description": "采购员"
            },
            {
                "name": "supplier",
                "type": "string",
                "required": False,
                "default_value": "SUP0001",
                "description": "供应商"
            },
            {
                "name": "specification",
                "type": "string",
                "required": False,
                "default_value": "",
                "description": "规格"
            },
            {
                "name": "unit_of_measure",
                "type": "string",
                "required": False,
                "default_value": "PCS",
                "description": "计量单位"
            },
            {
                "name": "unit_price",
                "type": "float",
                "required": False,
                "default_value": "0.0",
                "description": "单价"
            },
            {
                "name": "amount",
                "type": "float",
                "required": False,
                "default_value": "0.0",
                "description": "金额"
            },
            {
                "name": "delivery_address",
                "type": "string",
                "required": False,
                "default_value": "厂区A栋收货区",
                "description": "到货地址"
            },
            {
                "name": "sequence_number",
                "type": "integer",
                "required": False,
                "default_value": "1",
                "description": "序号"
            },
            {
                "name": "message_title",
                "type": "string",
                "required": False,
                "default_value": "紧急采购启动",
                "description": "消息标题"
            },
            {
                "name": "message_content",
                "type": "string",
                "required": False,
                "default_value": "",
                "description": "消息内容"
            }
        ],
        "submission_criteria": []
    }
    return action_data

def create_material_substitution_function_action():
    """Create material substitution function action"""
    function_code = '''
# 物料替代方案函数实现 - 使用 Ontology SDK
import json
from datetime import datetime

# 使用 SDK（必须在脚本末尾定义 result 变量）
from my_ontology_sdk import OntologyClient

def execute_material_substitution(parameters):
    """
    执行物料替代方案
    Args:
        parameters: 包含对齐模型字段的参数字典
    Returns:
        dict: 执行结果
    """
    try:
        # 验证必需参数（使用模型字段名）
        required_params = ['original_item_code', 'substitute_item_code', 
                          'substitute_item_name', 'work_order_number']
        
        for param in required_params:
            if param not in parameters:
                return {"success": False, "error": f"Missing required parameter: {param}"}
        
        # 初始化 SDK 客户端
        client = OntologyClient("http://localhost:8080")
        
        # 1. 验证替代物料的认证状态（简化逻辑）
        certification_status = parameters.get("certification_status", "NotCertified")
        if certification_status != "Certified":
            return {"success": False, "error": f"替代物料未认证，当前状态: {certification_status}"}
        
        # 2. 检查替代物料库存（使用inventory模型字段）
        inventory_items = client.models.Inventory.find(item_code=parameters['substitute_item_code'])
        available_quantity = 0
        if inventory_items and len(inventory_items) > 0:
            available_quantity = getattr(inventory_items[0], 'safety_stock_level', 0)
        
        required_quantity = parameters.get("required_quantity", 0)
        if available_quantity < required_quantity:
            return {"success": False, "error": f"替代物料库存不足，可用: {available_quantity}, 需求: {required_quantity}"}
        
        # 3. 更新工单的物料信息 (work_order) - 直接使用参数
        work_order = client.models.WorkOrder.get(parameters["work_order_number"])
        if not work_order:
            return {"success": False, "error": f"工单未找到: {parameters['work_order_number']}"}
        
        update_data = {
            "item_code": parameters["substitute_item_code"],
            "item_name": parameters["substitute_item_name"],
            "production_quantity": required_quantity
        }
        
        success = work_order.update(**update_data)
        if not success:
            return {"success": False, "error": "Failed to update work order"}
        
        # 4. 创建材料明细记录 (material_detail) - 直接使用参数
        material_detail_data = {
            "work_order_number": parameters["work_order_number"],
            "sequence_number": parameters.get("sequence_number", 1),
            "item_code": parameters["substitute_item_code"],
            "item_name": parameters["substitute_item_name"],
            "unit_of_measure": parameters.get("unit_of_measure", "PCS"),
            "required_quantity": required_quantity
        }
        
        material_detail = client.models.MaterialDetail.create(**material_detail_data)
        if not material_detail:
            return {"success": False, "error": "Failed to create material detail"}
        
        # 5. 记录替代方案日志 (alert_message) - 直接使用参数
        alert_message_data = {
            "message_id": f"ALERT-SUB-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message_title": "物料替代实施",
            "message_content": f"工单 {parameters['work_order_number']} 已启用替代物料 {parameters['substitute_item_code']} 替代 {parameters['original_item_code']}",
            "rule_code": "MATERIAL_SUBSTITUTION",
            "recipient": parameters.get("responsible_person", "SYSTEM"),
            "risk_level": "Medium"
        }
        
        alert_message = client.models.AlertMessage.create(**alert_message_data)
        
        return {
            "success": True,
            "message": "物料替代方案已实施",
            "result": {
                "original_item_code": parameters["original_item_code"],
                "substitute_item_code": parameters["substitute_item_code"],
                "work_order_number": parameters["work_order_number"],
                "available_quantity": available_quantity,
                "used_quantity": required_quantity
            }
        }
    
    except Exception as e:
        return {"success": False, "error": f"Material substitution failed: {str(e)}"}

# 执行函数并定义 result 变量（必须）
result = execute_material_substitution(parameters)
'''
    
    action_data = {
        "id": "material_substitution",
        "api_name": "MaterialSubstitution",
        "name": "物料替代方案",
        "description": "为供应中断的关键物料启用已认证的替代物料方案，参数与业务模型字段完全对齐",
        "action_type": "function",
        "function_code": function_code,
        "parameters": [
            # 核心必需字段
            {
                "name": "original_item_code",
                "type": "string",
                "required": True,
                "description": "原始品号"
            },
            {
                "name": "substitute_item_code",
                "type": "string",
                "required": True,
                "description": "替代品号"
            },
            {
                "name": "substitute_item_name",
                "type": "string",
                "required": True,
                "description": "替代品名"
            },
            {
                "name": "work_order_number",
                "type": "string",
                "required": True,
                "description": "工单编号"
            },
            {
                "name": "required_quantity",
                "type": "integer",
                "required": False,
                "default_value": "0",
                "description": "需用数量"
            },
            {
                "name": "certification_status",
                "type": "string",
                "required": True,
                "description": "认证状态"
            },
            # 可选字段
            {
                "name": "sequence_number",
                "type": "integer",
                "required": False,
                "default_value": "1",
                "description": "序号"
            },
            {
                "name": "unit_of_measure",
                "type": "string",
                "required": False,
                "default_value": "PCS",
                "description": "计量单位"
            },
            {
                "name": "responsible_person",
                "type": "string",
                "required": False,
                "default_value": "SYSTEM",
                "description": "负责人"
            }
        ],
        "submission_criteria": []
    }
    return action_data

def create_production_schedule_adjustment_function_action():
    """Create production schedule adjustment function action"""
    function_code = '''
# 生产计划调整函数实现 - 使用 Ontology SDK
import json
from datetime import datetime

# 使用 SDK（必须在脚本末尾定义 result 变量）
from my_ontology_sdk import OntologyClient

def execute_production_schedule_adjustment(parameters):
    """
    执行生产计划调整
    Args:
        parameters: 包含对齐模型字段的参数字典
    Returns:
        dict: 执行结果
    """
    try:
        # 验证必需参数（使用模型字段名）
        required_params = ['work_order_number', 'planned_start_date', 'planned_completion_date']
        
        for param in required_params:
            if param not in parameters:
                return {"success": False, "error": f"Missing required parameter: {param}"}
        
        # 初始化 SDK 客户端
        client = OntologyClient("http://localhost:8080")
        
        # 1. 获取并更新工单 (work_order) - 直接使用参数
        work_order = client.models.WorkOrder.get(parameters["work_order_number"])
        if not work_order:
            return {"success": False, "error": f"工单未找到: {parameters['work_order_number']}"}
        
        update_data = {
            "planned_start_date": parameters["planned_start_date"],
            "planned_completion_date": parameters["planned_completion_date"]
        }
        
        success = work_order.update(**update_data)
        if not success:
            return {"success": False, "error": "Failed to update work order"}
        
        # 2. 创建生产计划记录 (production_plan) - 直接使用参数
        plan_data = {
            "plan_id": f"PLAN-ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "calculation_id": "MANUAL_ADJUSTMENT",
            "item_code": getattr(work_order, 'item_code', parameters.get("item_code", "")),
            "item_name": getattr(work_order, 'item_name', parameters.get("item_name", "")),
            "unit_of_measure": getattr(work_order, 'unit_of_measure', parameters.get("unit_of_measure", "PCS")),
            "production_quantity": getattr(work_order, 'production_quantity', parameters.get("production_quantity", 0)),
            "demand_date": parameters["planned_completion_date"],
            "planned_start_date": parameters["planned_start_date"],
            "demand_source_document": "work_order",
            "demand_source_number": parameters["work_order_number"]
        }
        
        production_plan = client.models.ProductionPlan.create(**plan_data)
        
        # 3. 记录计划调整预警 (alert_message) - 直接使用参数
        alert_message_data = {
            "message_id": f"ALERT-SCH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message_title": "生产计划调整",
            "message_content": f"工单 {parameters['work_order_number']} 计划已调整，新完工日期: {parameters['planned_completion_date']}",
            "rule_code": "SCHEDULE_ADJUSTMENT",
            "recipient": parameters.get("responsible_person", "SYSTEM"),
            "risk_level": "High"
        }
        
        alert_message = client.models.AlertMessage.create(**alert_message_data)
        
        return {
            "success": True,
            "message": "生产计划调整已完成",
            "result": {
                "work_order_number": parameters["work_order_number"],
                "planned_start_date": parameters["planned_start_date"],
                "planned_completion_date": parameters["planned_completion_date"],
                "affected_materials": parameters.get("affected_materials", "")
            }
        }
    
    except Exception as e:
        return {"success": False, "error": f"Schedule adjustment failed: {str(e)}"}

# 执行函数并定义 result 变量（必须）
result = execute_production_schedule_adjustment(parameters)
'''
    
    action_data = {
        "id": "production_schedule_adjustment",
        "api_name": "ProductionScheduleAdjustment",
        "name": "生产计划调整",
        "description": "根据物料供应情况调整受影响工单的生产计划，参数与业务模型字段完全对齐",
        "action_type": "function",
        "function_code": function_code,
        "parameters": [
            # Work Order 字段
            {
                "name": "work_order_number",
                "type": "string",
                "required": True,
                "description": "工单编号"
            },
            {
                "name": "planned_start_date",
                "type": "date",
                "required": True,
                "description": "预计开工日"
            },
            {
                "name": "planned_completion_date",
                "type": "date",
                "required": True,
                "description": "预计完工日"
            },
            # Production Plan 字段（可选）
            {
                "name": "item_code",
                "type": "string",
                "required": False,
                "default_value": "",
                "description": "品号"
            },
            {
                "name": "item_name",
                "type": "string",
                "required": False,
                "default_value": "",
                "description": "品名"
            },
            {
                "name": "unit_of_measure",
                "type": "string",
                "required": False,
                "default_value": "PCS",
                "description": "计量单位"
            },
            {
                "name": "production_quantity",
                "type": "integer",
                "required": False,
                "default_value": "0",
                "description": "生产数量"   
            },
            {
                "name": "responsible_person",
                "type": "string",
                "required": False,
                "default_value": "SYSTEM",
                "description": "负责人"
            },
            {
                "name": "affected_materials",
                "type": "string",
                "required": False,
                "default_value": "",
                "description": "受影响物料列表"
            }
        ],
        "submission_criteria": []
    }
    return action_data

def create_customer_communication_function_action():
    """Create customer communication function action"""
    function_code = '''
# 客户沟通函数实现 - 使用 Ontology SDK
import json
from datetime import datetime

# 使用 SDK（必须在脚本末尾定义 result 变量）
from my_ontology_sdk import OntologyClient

def execute_customer_communication(parameters):
    """
    执行客户沟通流程
    Args:
        parameters: 包含对齐模型字段的参数字典
    Returns:
        dict: 执行结果
    """
    try:
        # 验证必需参数（使用模型字段名）
        required_params = ['customer', 'order_number', 'work_order_number', 
                          'item_code', 'message_content', 'action_description']
        
        for param in required_params:
            if param not in parameters:
                return {"success": False, "error": f"Missing required parameter: {param}"}
        
        # 初始化 SDK 客户端
        client = OntologyClient("http://localhost:8080")
        
        # 1. 创建客户通知记录 (alert_message) - 直接使用参数
        alert_message_data = {
            "message_id": f"NOTIFY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message_title": f"客户通知 - {parameters['customer']}",
            "message_content": parameters["message_content"],
            "rule_code": "CUSTOMER_COMMUNICATION",
            "recipient": parameters.get("sales_representative", ""),
            "risk_level": parameters.get("risk_level", "Medium")
        }
        
        alert_message = client.models.AlertMessage.create(**alert_message_data)
        
        # 2. 更新销售订单状态 (sales_order) - 直接使用参数
        sales_order = client.models.SalesOrder.get(parameters["order_number"])
        if sales_order:
            order_update = {
                "status": "风险预警"
            }
            sales_order.update(**order_update)
        
        # 3. 创建建议行动记录 (suggested_action) - 直接使用参数
        suggested_action_data = {
            "action_id": f"ACTION-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "related_alert_message_id": alert_message_data["message_id"],
            "action_description": parameters["action_description"]
        }
        
        suggested_action = client.models.SuggestedAction.create(**suggested_action_data)
        
        return {
            "success": True,
            "message": "客户沟通流程已启动",
            "result": {
                "customer": parameters["customer"],
                "order_number": parameters["order_number"],
                "work_order_number": parameters["work_order_number"],
                "item_code": parameters["item_code"],
                "notification_id": alert_message_data["message_id"]
            }
        }
    
    except Exception as e:
        return {"success": False, "error": f"Customer communication failed: {str(e)}"}

# 执行函数并定义 result 变量（必须）
result = execute_customer_communication(parameters)
'''
    
    action_data = {
        "id": "customer_communication",
        "api_name": "CustomerCommunication",
        "name": "客户沟通",
        "description": "向受影响的客户发送供应中断通知并提供解决方案，参数与业务模型字段完全对齐",
        "action_type": "function",
        "function_code": function_code,
        "parameters": [
            # Sales Order 字段
            {
                "name": "customer",
                "type": "string",
                "required": True,
                "description": "客户"
            },
            {
                "name": "order_number",
                "type": "string",
                "required": True,
                "description": "单据编号"
            },
            # Work Order 字段
            {
                "name": "work_order_number",
                "type": "string",
                "required": True,
                "description": "工单编号"
            },
            # Inventory 字段
            {
                "name": "item_code",
                "type": "string",
                "required": True,
                "description": "品号"
            },
            # Alert Message 字段
            {
                "name": "message_content",
                "type": "string",
                "required": True,
                "description": "消息内容"
            },
            {
                "name": "risk_level",
                "type": "string",
                "required": False,
                "default_value": "Medium",
                "description": "风险等级"
            },
            # Suggested Action 字段
            {
                "name": "action_description",
                "type": "string",
                "required": True,
                "description": "建议行动描述"
            },
            # Sales Order 字段（可选）
            {
                "name": "sales_representative",
                "type": "string",
                "required": False,
                "default_value": "",
                "description": "业务员"
            }
        ],
        "submission_criteria": []
    }
    return action_data

def main():
    dao = get_action_dao()
    
    # Delete existing function actions first
    action_ids_to_delete = [
        "emergency_procurement",
        "material_substitution", 
        "production_schedule_adjustment",
        "customer_communication"
    ]
    
    for action_id in action_ids_to_delete:
        try:
            dao.delete_action(action_id)
            print(f"Deleted existing action: {action_id}")
        except Exception as e:
            print(f"Error deleting action {action_id}: {str(e)}")
    
    # Create all four function actions
    actions = [
        create_emergency_procurement_function_action(),
        create_material_substitution_function_action(),
        create_production_schedule_adjustment_function_action(),
        create_customer_communication_function_action()
    ]
    
    for action in actions:
        try:
            result = dao.create_action(action)
            if result:
                print(f"Successfully created function action: {action['id']}")
            else:
                print(f"Failed to create function action: {action['id']}")
        except Exception as e:
            print(f"Error creating function action {action['id']}: {str(e)}")

if __name__ == "__main__":
    main()