"""
导入新建工单（机会预测）Action到本体

Action: createWorkOrder
功能: 基于机会预测创建生产工单（自动展开工序、物料需求、WIP批次）
难度: ⭐⭐
"""
import requests
from datetime import datetime

API_URL = "http://localhost:8080/api/v1"

ACTION_DATA = {
    "id": "create_opportunity_work_order",
    "api_name": "CreateOpportunityWorkOrder",
    "name": "新建工单（机会预测）",
    "description": "基于机会预测创建生产工单。自动根据产品工艺路线展开工单工序、计算物料需求（考虑BOM有效期）、创建WIP批次。支持投入过量方案（根据工序总良率反推投入数量）。适用于销售预测、机会订单、备货生产等场景。返回工单ID、展开的工序数、物料需求数和批次号列表。",
    "action_type": "function",
    "operation": "create",
    "target_model_id": "work_order",
    "parameters": [
        {
            "name": "product_id",
            "type": "string",
            "required": True,
            "description": "产品ID。示例：'PROD-WAFER-001'"
        },
        {
            "name": "forecast_qty",
            "type": "float",
            "required": True,
            "description": "预测需求数量（预期产出量/良品数量）。系统将自动根据工艺路线良率计算计划投入量"
        },
        {
            "name": "priority",
            "type": "integer",
            "required": False,
            "description": "工单优先级（1-10，数字越小优先级越高）。默认5"
        },
        {
            "name": "planned_start_date",
            "type": "datetime",
            "required": False,
            "description": "计划开始日期（ISO格式）。默认当前时间+4小时"
        },
        {
            "name": "setup_group",
            "type": "string",
            "required": False,
            "description": "换线组（用于排程优化，同组工单可合并）。默认从产品配置读取"
        },
        {
            "name": "reason",
            "type": "string",
            "required": False,
            "description": "工单创建原因。示例：'Q2销售预测备货'"
        }
    ],
    "submission_criteria": [],
    "function_code": '''# 新建工单（机会预测）- 创建生产工单并展开工序、物料、批次
import json
import math
from datetime import datetime, timedelta
from my_ontology_sdk import OntologyClient

def execute_create_work_order(parameters):
    """
    新建工单（机会预测）- 创建生产工单
    
    业务逻辑:
    1. 验证产品是否存在
    2. 查询产品工艺路线
    3. 计算投入量（考虑良率损耗）
    4. 创建工单主记录
    5. 展开工单工序（按工艺路线）
    6. 展开工单物料需求（按BOM）
    7. 创建WIP批次
    8. 返回工单详情
    """
    try:
        # 1. 解析参数
        product_id = parameters.get("product_id")
        forecast_qty = parameters.get("forecast_qty")
        work_order_type = "预测"
        priority = parameters.get("priority", 5)
        planned_start_date = parameters.get("planned_start_date")
        setup_group = parameters.get("setup_group")
        reason = parameters.get("reason", "机会预测")
        
        if not product_id or not forecast_qty:
            return {"success": False, "error": "请提供产品ID和预测需求数量"}
        
        if forecast_qty <= 0:
            return {"success": False, "error": "预测需求数量必须大于0"}
        
        # 2. 初始化SDK客户端
        client = OntologyClient("http://localhost:8080", api_key="your-api-key")
        
        # 3. 验证产品是否存在
        products = client.models.Product.find(product_id=product_id)
        if not products:
            return {"success": False, "error": f"产品 {product_id} 不存在"}
        
        product = products[0]
        product_name = getattr(product, 'product_name', product_id)
        product_setup_group = getattr(product, 'setup_group', 'DEFAULT')
        
        if not setup_group:
            setup_group = product_setup_group
        
        # 4. 查询工艺路线（本体逻辑：通过ProcessRoute表查询）
        # 本体模型中：ProcessRoute表有product_id字段
        # 关系：product(1) → process_route(N)，每个产品有独立的工艺路线
        process_routes = client.models.ProcessRoute.find(product_id=product_id)
        if not process_routes:
            return {"success": False, "error": f"产品 {product_name} 未配置工艺路线"}
        
        # 选择第一个激活的工艺路线
        active_route = None
        for route in process_routes:
            if getattr(route, 'is_active', True):
                active_route = route
                break
        
        if not active_route:
            return {"success": False, "error": f"产品 {product_name} 没有激活的工艺路线"}
        
        route_id = getattr(active_route, 'route_id')
        
        # 5. 查询该工艺路线的所有工序
        route_steps = client.models.RouteStep.find(route_id=route_id)
        if not route_steps:
            return {"success": False, "error": f"工艺路线 {route_id} 没有工序配置"}
        
        # 按工序序号排序
        route_steps = sorted(route_steps, key=lambda x: getattr(x, 'sequence_no', 0))
        
        # 5. 计算计划投入量（基于预测需求量和工艺路线良率）
        # 仿真逻辑：calculate_required_input_qty
        # 公式：投入量 = 需求产出量 / 总良率
        # 总良率 = 工序1良率 × 工序2良率 × ... × 工序N良率
        
        # 计算总良率
        total_yield_rate = 1.0
        for step in route_steps:
            # 每道工序的良率 = 工序标准良率
            step_yield = getattr(step, 'yield_rate_standard', 0.98)
            total_yield_rate *= step_yield
        
        # 反推投入量
        required_input_qty = forecast_qty / total_yield_rate
        
        # 向上取整到Lot大小的倍数
        lot_size = 25  # 默认批次大小，与仿真一致
        planned_quantity = math.ceil(required_input_qty / lot_size) * lot_size
        
        # 6. 计算计划时间
        now_dt = datetime.now()
        if planned_start_date:
            if isinstance(planned_start_date, str):
                planned_start = datetime.fromisoformat(planned_start_date)
            else:
                planned_start = planned_start_date
        else:
            planned_start = now_dt + timedelta(hours=4)
        
        # 计算计划完工日期（简化的CTP估算）
        total_hours = 0
        cumulative_offset = 4.0  # 初始偏移4小时
        for step in route_steps:
            std_time = getattr(step, 'standard_time_hours', 0)
            wait_time = getattr(step, 'wait_time_hours', 0)
            transport_time = getattr(step, 'transport_time_hours', 0)
            queue_time = 0.5  # 工序间排队时间
            
            cumulative_offset += std_time + wait_time + transport_time + queue_time
            total_hours = cumulative_offset
        
        planned_completion = planned_start + timedelta(hours=total_hours)
        
        # 7. 生成工单ID
        all_wos = client.models.WorkOrder.find()
        wo_count = len(list(all_wos)) if all_wos else 0
        wo_id = f"WO-FORECAST-{wo_count + 1:04d}"
        
        # 8. 创建工单主记录
        wo_data = {
            "work_order_id": wo_id,
            "customer_order_id": None,  # 机会预测工单无关联订单
            "product_id": product_id,
            "work_order_type": work_order_type,
            "planned_quantity": planned_quantity,  # 计划投入量（基于良率计算）
            "expected_output_qty": forecast_qty,  # 预期产出量（预测需求量）
            "planned_start_date": planned_start.isoformat(),
            "planned_completion_date": planned_completion.isoformat(),
            "actual_start_date": None,
            "actual_completion_date": None,
            "status": "已下达",
            "priority": priority,
            "setup_group": setup_group,
            "current_step_id": route_steps[0].step_id if route_steps else None,
            "completed_quantity": 0.0,
            "scrapped_quantity": 0.0,
            "note": f"{reason} | 类型: {work_order_type} | 优先级: P{priority} | 预测量: {forecast_qty} → 投入量: {planned_quantity} (良率: {total_yield_rate:.2%})",
            "created_at": now_dt.isoformat()
        }
        
        created_wo = client.models.WorkOrder.create(**wo_data)
        
        if not created_wo:
            return {"success": False, "error": "创建工单失败"}
        
        # 9. 展开工单工序（优化：先构建所有数据，再逐条创建）
        created_operations = []
        input_qty = planned_quantity
        
        for i, step in enumerate(route_steps):
            wo_op_id = f"{wo_id}-OP{getattr(step, 'sequence_no', i+1):02d}"
            
            std_time = getattr(step, 'standard_time_hours', 0)
            wait_time = getattr(step, 'wait_time_hours', 0)
            transport_time = getattr(step, 'transport_time_hours', 0)
            
            # 计算工序计划时间（累积偏移）
            if i == 0:
                op_planned_start = planned_start
            else:
                prev_step = route_steps[i-1]
                prev_std_time = getattr(prev_step, 'standard_time_hours', 0)
                prev_wait_time = getattr(prev_step, 'wait_time_hours', 0)
                prev_transport_time = getattr(prev_step, 'transport_time_hours', 0)
                op_planned_start = op_planned_start + timedelta(
                    hours=prev_std_time + prev_wait_time + prev_transport_time + 0.5
                )
            
            planned_duration = std_time
            op_planned_end = op_planned_start + timedelta(hours=planned_duration + wait_time + transport_time)
            
            op_data = {
                "wo_op_id": wo_op_id,
                "work_order_id": wo_id,
                "step_id": getattr(step, 'step_id', ''),
                "sequence_no": getattr(step, 'sequence_no', i+1),
                "planned_start": op_planned_start.isoformat(),
                "planned_end": op_planned_end.isoformat(),
                "actual_start": None,
                "actual_end": None,
                "required_input_qty": round(input_qty, 4),
                "completed_output_qty": 0.0,
                "scrapped_qty": 0.0,
                "assigned_machine_id": None,
                "status": "待开工",
                "is_rework": False,
                "setup_completed": False,
                "material_issued": False
            }
            
            created_op = client.models.WorkOrderOperation.create(**op_data)
            if created_op:
                created_operations.append(wo_op_id)
            
            # 计算下一道工序的投入量（考虑良率损耗）
            yield_rate = getattr(step, 'yield_rate_standard', 0.98)
            input_qty *= yield_rate
        
        # 10. 展开工单物料需求（按BOM）
        boms = client.models.Bom.find(product_id=product_id)
        created_materials = []
        
        if boms:
            # P2-C7: 过滤BOM有效期
            order_date = now_dt.date() if hasattr(now_dt, 'date') else now_dt
            valid_boms = [
                b for b in boms
                if (getattr(b, 'effective_date', None) is None or 
                    (hasattr(b.effective_date, 'date') and b.effective_date.date() <= order_date) or
                    (isinstance(b.effective_date, str) and b.effective_date <= str(order_date)))
                and (getattr(b, 'expiry_date', None) is None or 
                     (hasattr(b.expiry_date, 'date') and b.expiry_date.date() >= order_date) or
                     (isinstance(b.expiry_date, str) and b.expiry_date >= str(order_date)))
            ]
            
            for idx, bom in enumerate(valid_boms):
                material_id = getattr(bom, 'material_id', '')
                quantity_per_unit = getattr(bom, 'quantity_per_unit', 0)
                required_qty = quantity_per_unit * planned_quantity  # 基于投入量计算物料需求
                step_id = getattr(bom, 'step_id', None)
                
                # 计算物料需求日期
                required_date = planned_start
                if step_id:
                    # 从step_id提取序号
                    try:
                        seq_no = int(step_id.split("-")[-1])
                    except:
                        seq_no = 10
                    
                    # 根据工序序号估算需求日期
                    offset_hours = (seq_no // 10 - 1) * 24
                    required_date = planned_start + timedelta(
                        hours=offset_hours - 2  # 提前2小时备料
                    )
                
                # 生成WO Op ID
                wo_op_id_for_material = None
                if step_id:
                    try:
                        seq_no = int(step_id.split("-")[-1])
                        wo_op_id_for_material = f"{wo_id}-OP{seq_no:02d}"
                    except:
                        pass
                
                wom_id = f"WOM-{wo_id}-{idx+1:03d}"
                wom_data = {
                    "wom_id": wom_id,
                    "work_order_id": wo_id,
                    "wo_op_id": wo_op_id_for_material,
                    "material_id": material_id,
                    "required_quantity": required_qty,
                    "allocated_quantity": 0.0,
                    "consumed_quantity": 0.0,
                    "shortage_quantity": 0.0,
                    "required_date": required_date.isoformat(),
                    "status": "待分配",
                    "note": None
                }
                
                created_wom = client.models.WorkOrderMaterial.create(**wom_data)
                if created_wom:
                    created_materials.append(wom_id)
        
        # 11. 创建WIP批次（基于投入量分解）
        lot_size = 25  # 默认批次大小，与仿真一致
        num_lots = int(planned_quantity // lot_size)
        remainder = planned_quantity % lot_size
        
        lots = []
        for i in range(num_lots):
            lots.append(lot_size)
        if remainder > 0:
            lots.append(remainder)
        
        created_lots = []
        
        for i, lqty in enumerate(lots):
            lot_id = f"{wo_id}-LOT{i+1:02d}"
            
            lot_data = {
                "lot_id": lot_id,
                "work_order_id": wo_id,
                "product_id": product_id,
                "lot_size": lot_size,
                "current_step_id": route_steps[0].step_id if route_steps else None,
                "current_machine_id": None,
                "lot_quantity": lqty,
                "actual_quantity": lqty,
                "lot_status": "排队中",
                "queue_start_time": now_dt.isoformat(),
                "processing_start_time": None,
                "completed_time": None,
                "hold_reason": None,
                "priority": priority,
                "created_at": now_dt.isoformat()
            }
            
            created_lot = client.models.WipLot.create(**lot_data)
            if created_lot:
                created_lots.append(lot_id)
        
        # 12. 构建结果数据
        result = {
            "work_order_id": wo_id,
            "product_id": product_id,
            "product_name": product_name,
            "work_order_type": work_order_type,
            "forecast_qty": forecast_qty,  # 预测需求量（预期产出）
            "total_yield_rate": round(total_yield_rate, 4),  # 总良率
            "planned_quantity": planned_quantity,  # 计划投入量（良率补偿后）
            "expected_output_qty": forecast_qty,  # 预期产出量
            "planned_start_date": planned_start.isoformat(),
            "planned_completion_date": planned_completion.isoformat(),
            "priority": priority,
            "setup_group": setup_group,
            "status": "已下达",
            "operations_count": len(created_operations),
            "materials_count": len(created_materials),
            "lots_count": len(created_lots),
            "created_at": now_dt.isoformat()
        }
        
        # 13. 返回成功结果
        return {
            "success": True,
            "message": f"工单创建成功：{wo_id}，预测需求{forecast_qty} → 计划投入{planned_quantity} (良率{total_yield_rate:.2%})，展开{len(created_operations)}个工序、{len(created_materials)}个物料需求、{len(created_lots)}个批次",
            "result": result,
            "operations": created_operations,
            "materials": created_materials,
            "lots": created_lots
        }
        
    except Exception as e:
        return {"success": False, "error": f"创建工单失败: {str(e)}"}

result = execute_create_work_order(parameters)
'''
}


def import_action():
    """导入Action"""
    print("=" * 60)
    print("开始导入新建工单（机会预测）Action")
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
            print("\n[SUCCESS] 新建工单（机会预测）Action导入成功")
            print(f"   Action ID: {ACTION_DATA['id']}")
            print(f"   Action Name: {ACTION_DATA['name']}")
            print(f"   求解器类型: 业务逻辑")
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
