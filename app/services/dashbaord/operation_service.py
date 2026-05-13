"""
供应链运营服务类
提供采购、库存、工单、销售订单等业务数据的查询和统计
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter

from app.services.dashbaord.sdk_client import get_ontology_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OperationService:
    """供应链运营服务类"""
    
    def __init__(self):
        self.client = get_ontology_client()
    
    # ==================== 采购相关 ====================
    
    def get_po_execution_rate(self) -> float:
        """获取采购订单执行率(已入库/总数)"""
        try:
            all_pos = self.client.models.PurchaseOrder.find()
            if not all_pos:
                return 0.0
            
            # 数据库中的状态是: 已入库, 已创建
            delivered_count = sum(1 for po in all_pos if getattr(po, 'status', '') == '已入库')
            return round(delivered_count / len(all_pos) * 100, 2)
        except Exception as e:
            logger.error(f"获取采购订单执行率失败: {e}")
            return 0.0
    
    def get_delayed_purchase_orders(self, limit: int = 20) -> List[Dict]:
        """获取延迟交付的采购订单"""
        try:
            all_pos = self.client.models.PurchaseOrder.find()
            now = datetime.now()
            
            delayed_orders = []
            for po in all_pos:
                status = getattr(po, 'status', '')
                expected_date_str = getattr(po, 'expected_delivery_date', '')
                
                # 跳过已入库的订单
                if status == '已入库':
                    continue
                
                # 检查是否延迟
                if expected_date_str:
                    try:
                        expected_date = datetime.fromisoformat(expected_date_str.replace('Z', '+00:00').replace('+00:00', ''))
                        # 将期望日期设置为当天23:59:59,避免时间部分影响计算
                        expected_date_end = expected_date.replace(hour=23, minute=59, second=59)
                        if expected_date_end < now:
                            # 获取供应商信息
                            supplier = po.GetSupplier()
                            supplier_name = getattr(supplier, 'supplier_name', '') if supplier else ''
                            
                            # 计算延迟天数:使用日期部分计算,忽略时间
                            from datetime import date
                            delay_days = (now.date() - expected_date.date()).days
                            
                            delayed_orders.append({
                                'po_id': getattr(po, 'po_id', ''),
                                'supplier_id': getattr(po, 'supplier_id', ''),
                                'supplier_name': supplier_name,
                                'order_date': getattr(po, 'order_date', ''),
                                'expected_delivery_date': expected_date_str,
                                'actual_delivery_date': getattr(po, 'actual_delivery_date', ''),
                                'status': status,
                                'total_amount': getattr(po, 'total_amount', 0),
                                'delay_days': delay_days
                            })
                    except:
                        continue
            
            # 按延迟天数排序
            delayed_orders.sort(key=lambda x: x.get('delay_days', 0), reverse=True)
            return delayed_orders[:limit]
        except Exception as e:
            logger.error(f"获取延迟采购订单失败: {e}")
            return []
    
    def get_supplier_delivery_performance(self, limit: int = 5) -> List[Dict]:
        """获取供应商交付表现TOP5"""
        try:
            all_pos = self.client.models.PurchaseOrder.find()
            now = datetime.now()
            
            supplier_stats = {}
            
            for po in all_pos:
                supplier_id = getattr(po, 'supplier_id', '')
                if not supplier_id:
                    continue
                
                if supplier_id not in supplier_stats:
                    supplier_stats[supplier_id] = {
                        'total': 0,
                        'on_time': 0,
                        'delayed': 0
                    }
                
                supplier_stats[supplier_id]['total'] += 1
                
                status = getattr(po, 'status', '')
                expected_date_str = getattr(po, 'expected_delivery_date', '')
                
                if status == '已入库':
                    actual_date_str = getattr(po, 'actual_delivery_date', '')
                    if expected_date_str and actual_date_str:
                        try:
                            expected_date = datetime.fromisoformat(expected_date_str.replace('Z', '+00:00').replace('+00:00', ''))
                            actual_date = datetime.fromisoformat(actual_date_str.replace('Z', '+00:00').replace('+00:00', ''))
                            if actual_date <= expected_date:
                                supplier_stats[supplier_id]['on_time'] += 1
                            else:
                                supplier_stats[supplier_id]['delayed'] += 1
                        except:
                            pass
            
            # 计算准时交付率并排序
            result = []
            for supplier_id, stats in supplier_stats.items():
                if stats['total'] > 0:
                    supplier = self.client.models.Supplier.find(supplier_id=supplier_id)
                    supplier_name = getattr(supplier[0], 'supplier_name', '') if supplier else ''
                    
                    on_time_rate = round(stats['on_time'] / stats['total'] * 100, 2)
                    result.append({
                        'supplier_id': supplier_id,
                        'supplier_name': supplier_name,
                        'total_orders': stats['total'],
                        'on_time_count': stats['on_time'],
                        'on_time_rate': on_time_rate
                    })
            
            result.sort(key=lambda x: x['on_time_rate'], reverse=True)
            return result[:limit]
        except Exception as e:
            logger.error(f"获取供应商交付表现失败: {e}")
            return []
    
    # ==================== 库存相关 ====================
    
    def get_inventory_health_rate(self) -> float:
        """获取库存健康度(高于安全库存的物料占比)"""
        try:
            all_inventories = self.client.models.Inventory.find()
            if not all_inventories:
                return 0.0
            
            healthy_count = 0
            total_count = 0
            
            for inv in all_inventories:
                material_id = getattr(inv, 'material_id', '')
                if not material_id:
                    continue
                
                # 获取物料的安全库存
                materials = self.client.models.Material.find(material_id=material_id)
                if not materials:
                    continue
                
                material = materials[0]
                safety_stock = getattr(material, 'safety_stock_level', 0)
                available_qty = getattr(inv, 'available_quantity', 0)
                
                total_count += 1
                if available_qty >= safety_stock:
                    healthy_count += 1
            
            return round(healthy_count / total_count * 100, 2) if total_count > 0 else 0.0
        except Exception as e:
            logger.error(f"获取库存健康度失败: {e}")
            return 0.0
    
    def get_low_inventory_alerts(self, limit: int = 20) -> List[Dict]:
        """获取低库存预警物料"""
        try:
            all_inventories = self.client.models.Inventory.find()
            
            low_inventory_items = []
            for inv in all_inventories:
                material_id = getattr(inv, 'material_id', '')
                if not material_id:
                    continue
                
                # 获取物料信息
                materials = self.client.models.Material.find(material_id=material_id)
                if not materials:
                    continue
                
                material = materials[0]
                safety_stock = getattr(material, 'safety_stock_level', 0)
                available_qty = getattr(inv, 'available_quantity', 0)
                
                # 只返回低于安全库存的物料
                if available_qty < safety_stock and safety_stock > 0:
                    # 计算在途采购数量（基于采购订单行状态）
                    in_transit_qty = 0
                    in_transit_details = []
                    
                    try:
                        # 查询该物料的所有采购订单行
                        all_pol = self.client.models.PurchaseOrderLine.find(material_id=material_id)
                        
                        for pol in all_pol:
                            pol_status = getattr(pol, 'status', '')
                            # 只统计未开始、待收货、部分到货的订单行（排除全部到货）
                            if pol_status in ['未开始', '待收货', '部分到货']:
                                quantity = getattr(pol, 'quantity', 0)
                                received_qty = getattr(pol, 'received_quantity', 0) or 0
                                
                                # 在途数量 = 订单数量 - 已收货数量
                                transit = quantity - received_qty
                                if transit > 0:
                                    in_transit_qty += transit
                                    
                                    # 获取PO信息
                                    po_id = getattr(pol, 'po_id', '')
                                    in_transit_details.append({
                                        'po_id': po_id,
                                        'line_id': getattr(pol, 'line_id', ''),
                                        'quantity': quantity,
                                        'received_quantity': received_qty,
                                        'in_transit': transit,
                                        'status': pol_status
                                    })
                    except Exception as e:
                        logger.warning(f"查询在途采购失败 {material_id}: {e}")
                    
                    # 健康度计算：基于当前库存，但在途数量提供加分
                    health_ratio = round(available_qty / safety_stock * 100, 2)
                    
                    # 在途加分：每10%安全库存的在途数量加5分，最多额外加30分
                    if in_transit_qty > 0:
                        transit_bonus = min(
                            round((in_transit_qty / safety_stock) * 50, 2),
                            30.0
                        )
                        adjusted_health_ratio = min(health_ratio + transit_bonus, 100.0)
                    else:
                        adjusted_health_ratio = health_ratio
                    
                    low_inventory_items.append({
                        'inventory_id': getattr(inv, 'inventory_id', ''),
                        'material_id': material_id,
                        'material_name': getattr(material, 'material_name', ''),
                        'material_type': getattr(material, 'material_type', ''),
                        'available_quantity': available_qty,
                        'safety_stock_level': safety_stock,
                        'reserved_quantity': getattr(inv, 'reserved_quantity', 0),
                        'in_transit_quantity': in_transit_qty,
                        'in_transit_details': in_transit_details,  # 在途明细
                        'health_ratio': health_ratio,  # 基于当前库存的健康度
                        'adjusted_health_ratio': adjusted_health_ratio,  # 考虑在途后的健康度
                        'location': getattr(inv, 'location', ''),
                        'is_healthy': False  # 低于安全库存就是不健康
                    })
            
            # 按健康度排序(越低越紧急)
            low_inventory_items.sort(key=lambda x: x['health_ratio'])
            return low_inventory_items[:limit]
        except Exception as e:
            logger.error(f"获取低库存预警失败: {e}")
            return []
    
    # ==================== 工单相关 ====================
    
    def get_wo_on_time_delivery_rate(self) -> float:
        """获取工单准时交付率"""
        try:
            all_wos = self.client.models.WorkOrder.find()
            if not all_wos:
                return 0.0
            
            completed_wos = [wo for wo in all_wos if getattr(wo, 'status', '') == '已完成']
            if not completed_wos:
                return 0.0
            
            on_time_count = 0
            for wo in completed_wos:
                planned_end_str = getattr(wo, 'planned_completion_date', '')
                actual_end_str = getattr(wo, 'actual_completion_date', '')
                
                if planned_end_str and actual_end_str:
                    try:
                        planned_end = datetime.fromisoformat(planned_end_str.replace('Z', '+00:00').replace('+00:00', ''))
                        actual_end = datetime.fromisoformat(actual_end_str.replace('Z', '+00:00').replace('+00:00', ''))
                        if actual_end <= planned_end:
                            on_time_count += 1
                    except:
                        pass
            
            return round(on_time_count / len(completed_wos) * 100, 2)
        except Exception as e:
            logger.error(f"获取工单准时交付率失败: {e}")
            return 0.0
    
    def get_delayed_work_orders(self, limit: int = 20) -> List[Dict]:
        """获取延期工单"""
        try:
            all_wos = self.client.models.WorkOrder.find()
            now = datetime.now()
            
            delayed_wos = []
            for wo in all_wos:
                status = getattr(wo, 'status', '')
                planned_end_str = getattr(wo, 'planned_completion_date', '')
                
                # 跳过已完成的工单
                if status == '已完成':
                    continue
                
                if planned_end_str:
                    try:
                        planned_end = datetime.fromisoformat(planned_end_str.replace('Z', '+00:00').replace('+00:00', ''))
                        # 将计划完成日期设置为当天23:59:59,避免时间部分影响计算
                        planned_end_of_day = planned_end.replace(hour=23, minute=59, second=59)
                        if planned_end_of_day < now:
                            # 获取产品信息
                            product_id = getattr(wo, 'product_id', '')
                            product_name = ''
                            if product_id:
                                products = self.client.models.Product.find(product_id=product_id)
                                if products:
                                    product_name = getattr(products[0], 'product_name', '')
                            
                            # 计算延迟天数:使用日期部分计算,忽略时间
                            delay_days = (now.date() - planned_end.date()).days
                            
                            delayed_wos.append({
                                'work_order_id': getattr(wo, 'work_order_id', ''),
                                'product_id': product_id,
                                'product_name': product_name,
                                'planned_quantity': getattr(wo, 'planned_quantity', 0),
                                'expected_output_qty': getattr(wo, 'expected_output_qty', 0),
                                'planned_start_date': getattr(wo, 'planned_start_date', ''),
                                'planned_completion_date': planned_end_str,
                                'actual_start_date': getattr(wo, 'actual_start_date', ''),
                                'status': status,
                                'delay_days': delay_days
                            })
                    except:
                        continue
            
            # 按延迟天数排序
            delayed_wos.sort(key=lambda x: x.get('delay_days', 0), reverse=True)
            return delayed_wos[:limit]
        except Exception as e:
            logger.error(f"获取延期工单失败: {e}")
            return []
    
    # ==================== 销售订单相关 ====================
    
    def get_monthly_customer_order_amount(self) -> float:
        """获取本月客户订单总金额"""
        try:
            now = datetime.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            all_orders = self.client.models.CustomerOrder.find()
            total_amount = 0
            
            for order in all_orders:
                order_date_str = getattr(order, 'order_date', '')
                if order_date_str:
                    try:
                        order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00').replace('+00:00', ''))
                        if order_date >= month_start:
                            quantity = getattr(order, 'quantity', 0)
                            unit_price = getattr(order, 'unit_price', 0)
                            total_amount += quantity * unit_price
                    except:
                        continue
            
            return round(total_amount, 2)
        except Exception as e:
            logger.error(f"获取本月客户订单金额失败: {e}")
            return 0.0
    
    def get_customer_order_trend(self, days: int = 30) -> List[Dict]:
        """获取客户订单交付趋势(近N天)"""
        try:
            now = datetime.now()
            start_date = now - timedelta(days=days)
            
            all_orders = self.client.models.CustomerOrder.find()
            
            # 按日期统计订单状态
            daily_stats = {}
            for i in range(days):
                date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                daily_stats[date] = {
                    'date': date,
                    'completed': 0,    # 已完成
                    'shipping': 0,     # 部分发货/已发货
                    'producing': 0,    # 生产中
                    'delayed': 0       # 延期
                }
            
            for order in all_orders:
                required_date_str = getattr(order, 'required_date', '')
                if not required_date_str:
                    continue
                
                try:
                    required_date = datetime.fromisoformat(required_date_str.replace('Z', '+00:00').replace('+00:00', ''))
                    date_key = required_date.strftime('%Y-%m-%d')
                    
                    if date_key not in daily_stats:
                        continue
                    
                    status = getattr(order, 'status', '')
                    
                    # 判断是否延期
                    if required_date < now and status not in ['已完成', '已发货', '部分发货']:
                        daily_stats[date_key]['delayed'] += 1
                    elif status in ['已完成', '已发货']:
                        daily_stats[date_key]['completed'] += 1
                    elif status == '部分发货':
                        daily_stats[date_key]['shipping'] += 1
                    elif status in ['生产中', '已确认']:
                        daily_stats[date_key]['producing'] += 1
                except:
                    continue
            
            # 转换为列表并排序
            trend_data = sorted(daily_stats.values(), key=lambda x: x['date'])
            return trend_data
            
        except Exception as e:
            logger.error(f"获取客户订单交付趋势失败: {e}")
            return []
    
    def get_upcoming_customer_orders(self, days: int = 7) -> List[Dict]:
        """获取即将到期的客户订单"""
        try:
            now = datetime.now()
            deadline = now + timedelta(days=days)
            
            all_orders = self.client.models.CustomerOrder.find()
            upcoming_orders = []
            
            for order in all_orders:
                status = getattr(order, 'status', '')
                required_date_str = getattr(order, 'required_date', '')
                
                # 跳过已完成的订单
                if status == '已完成':
                    continue
                
                if required_date_str:
                    try:
                        required_date = datetime.fromisoformat(required_date_str.replace('Z', '+00:00').replace('+00:00', ''))
                        if now <= required_date <= deadline:
                            # 获取客户信息
                            customer_id = getattr(order, 'customer_id', '')
                            customer_name = getattr(order, 'customer_name', '')
                            
                            # 获取产品信息
                            product_id = getattr(order, 'product_id', '')
                            product_name = ''
                            if product_id:
                                products = self.client.models.Product.find(product_id=product_id)
                                if products:
                                    product_name = getattr(products[0], 'product_name', '')
                            
                            quantity = getattr(order, 'quantity', 0)
                            unit_price = getattr(order, 'unit_price', 0)
                            
                            upcoming_orders.append({
                                'order_id': getattr(order, 'order_id', ''),
                                'customer_id': customer_id,
                                'customer_name': customer_name,
                                'customer_po_number': getattr(order, 'customer_po_number', ''),
                                'product_id': product_id,
                                'product_name': product_name,
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'total_amount': round(quantity * unit_price, 2),
                                'order_date': getattr(order, 'order_date', ''),
                                'required_date': required_date_str,
                                'status': status,
                                'days_remaining': (required_date - now).days
                            })
                    except:
                        continue
            
            # 按剩余天数排序
            upcoming_orders.sort(key=lambda x: x.get('days_remaining', 999))
            return upcoming_orders
        except Exception as e:
            logger.error(f"获取即将到期订单失败: {e}")
            return []
    
    # ==================== 生产排产甘特图 ====================
    
    def get_production_gantt_data(self, view_type: str = "machine", base_date: str = "2026-04-25", days: int = 7) -> Dict:
        """
        获取生产排产甘特图数据
        
        参数:
        - view_type: 视图类型 (machine=机台视图, work_order=工单视图)
        - base_date: 基准日期 (默认2026-04-25，与仿真数据衔接)
        - days: 规划天数 (默认7天)
        
        返回:
        - 包含tasks和resources的甘特图数据结构
        """
        try:
            # 解析时间范围
            base_dt = datetime.fromisoformat(base_date)
            end_dt = base_dt + timedelta(days=days)
            
            # 1. 查询时间范围内的所有生产任务（状态不为"已取消"）
            all_tasks = self.client.models.ProductionTask.find(
                planned_start_time__gte=base_dt.isoformat(),
                planned_start_time__lte=end_dt.isoformat()
            )
            
            if not all_tasks:
                return {
                    "view_type": view_type,
                    "time_range": {
                        "start": base_dt.isoformat(),
                        "end": end_dt.isoformat()
                    },
                    "resources": [],
                    "tasks": []
                }
            
            # 过滤时间范围内的任务
            tasks_in_range = []
            for task in all_tasks:
                start_str = getattr(task, 'planned_start_time', '')
                end_str = getattr(task, 'planned_end_time', '')
                
                if not start_str or not end_str:
                    continue
                
                try:
                    task_start = datetime.fromisoformat(start_str.replace('Z', '+00:00').replace('+00:00', ''))
                    task_end = datetime.fromisoformat(end_str.replace('Z', '+00:00').replace('+00:00', ''))
                    
                    # 检查是否在时间范围内
                    if task_start < end_dt and task_end > base_dt:
                        tasks_in_range.append(task)
                except:
                    continue
            
            # 2. 批量查询关联数据
            # 查询工单信息
            wo_ids = list(set([getattr(t, 'work_order_id', '') for t in tasks_in_range]))
            wo_map = {}
            if wo_ids:
                work_orders = self.client.models.WorkOrder.find(work_order_id__in=wo_ids)
                wo_map = {wo.work_order_id: wo for wo in work_orders}
            
            # 查询工单工序信息
            wo_op_ids = list(set([getattr(t, 'wo_op_id', '') for t in tasks_in_range]))
            wo_op_map = {}
            if wo_op_ids:
                wo_ops = self.client.models.WorkOrderOperation.find(wo_op_id__in=wo_op_ids)
                wo_op_map = {op.wo_op_id: op for op in wo_ops}
            
            # 查询工序步骤信息
            step_ids = list(set([getattr(op, 'step_id', '') for op in wo_op_map.values() if getattr(op, 'step_id', '')]))
            step_map = {}
            if step_ids:
                steps = self.client.models.RouteStep.find(step_id__in=step_ids)
                step_map = {s.step_id: s for s in steps}
            
            # 查询机台信息
            machine_ids = list(set([getattr(t, 'machine_id', '') for t in tasks_in_range]))
            machine_map = {}
            if machine_ids:
                machines = self.client.models.Machine.find(machine_id__in=machine_ids)
                machine_map = {m.machine_id: m for m in machines}
            
            # 3. 根据视图类型组织数据
            resources = []
            tasks = []
            
            if view_type == "machine":
                # 机台视图：以机台为分组
                resource_set = {}
                for task in tasks_in_range:
                    machine_id = getattr(task, 'machine_id', '')
                    if machine_id and machine_id not in resource_set:
                        machine = machine_map.get(machine_id)
                        machine_name = getattr(machine, 'machine_name', machine_id) if machine else machine_id
                        resource_set[machine_id] = {
                            "id": machine_id,
                            "name": machine_name,
                            "type": "machine"
                        }
                
                resources = list(resource_set.values())
                
                # 构建任务列表
                for task in tasks_in_range:
                    machine_id = getattr(task, 'machine_id', '')
                    work_order_id = getattr(task, 'work_order_id', '')
                    wo_op_id = getattr(task, 'wo_op_id', '')
                    
                    wo = wo_map.get(work_order_id)
                    wo_op = wo_op_map.get(wo_op_id)
                    step = step_map.get(getattr(wo_op, 'step_id', '')) if wo_op else None
                    machine = machine_map.get(machine_id)
                    
                    # 计算进度
                    status = getattr(task, 'status', '已排程')
                    progress = self._calculate_task_progress(status, task)
                    
                    # 构建任务名称
                    product_id = getattr(wo, 'product_id', '') if wo else ''
                    step_name = getattr(step, 'step_name', '') if step else ''
                    sequence_no = getattr(wo_op, 'sequence_no', 0) if wo_op else 0
                    task_name = f"{work_order_id}-{step_name or '工序'}-S{sequence_no}"
                    
                    start_str = getattr(task, 'planned_start_time', '')
                    end_str = getattr(task, 'planned_end_time', '')
                    
                    tasks.append({
                        "id": getattr(task, 'task_id', ''),
                        "resource_id": machine_id,
                        "name": task_name,
                        "start": start_str,
                        "end": end_str,
                        "progress": progress,
                        "status": status,
                        "work_order_id": work_order_id,
                        "product_id": product_id,
                        "product_name": product_id,
                        "step_name": step_name,
                        "sequence_no": sequence_no,
                        "planned_quantity": getattr(task, 'planned_quantity', 0),
                        "machine_name": getattr(machine, 'machine_name', machine_id) if machine else machine_id
                    })
            
            elif view_type == "work_order":
                # 工单视图：以工单为分组
                resource_set = {}
                for task in tasks_in_range:
                    work_order_id = getattr(task, 'work_order_id', '')
                    if work_order_id and work_order_id not in resource_set:
                        wo = wo_map.get(work_order_id)
                        product_id = getattr(wo, 'product_id', '') if wo else ''
                        resource_set[work_order_id] = {
                            "id": work_order_id,
                            "name": f"{work_order_id}-{product_id}",
                            "type": "work_order"
                        }
                
                resources = list(resource_set.values())
                
                # 构建任务列表
                for task in tasks_in_range:
                    work_order_id = getattr(task, 'work_order_id', '')
                    wo_op_id = getattr(task, 'wo_op_id', '')
                    machine_id = getattr(task, 'machine_id', '')
                    
                    wo = wo_map.get(work_order_id)
                    wo_op = wo_op_map.get(wo_op_id)
                    step = step_map.get(getattr(wo_op, 'step_id', '')) if wo_op else None
                    machine = machine_map.get(machine_id)
                    
                    # 计算进度
                    status = getattr(task, 'status', '已排程')
                    progress = self._calculate_task_progress(status, task)
                    
                    # 构建任务名称
                    step_name = getattr(step, 'step_name', '') if step else ''
                    sequence_no = getattr(wo_op, 'sequence_no', 0) if wo_op else 0
                    task_name = f"{step_name or '工序'}-S{sequence_no}({machine_id})"
                    
                    start_str = getattr(task, 'planned_start_time', '')
                    end_str = getattr(task, 'planned_end_time', '')
                    
                    tasks.append({
                        "id": getattr(task, 'task_id', ''),
                        "resource_id": work_order_id,
                        "name": task_name,
                        "start": start_str,
                        "end": end_str,
                        "progress": progress,
                        "status": status,
                        "work_order_id": work_order_id,
                        "product_id": getattr(wo, 'product_id', '') if wo else '',
                        "product_name": getattr(wo, 'product_id', '') if wo else '',
                        "step_name": step_name,
                        "sequence_no": sequence_no,
                        "planned_quantity": getattr(task, 'planned_quantity', 0),
                        "machine_name": getattr(machine, 'machine_name', machine_id) if machine else machine_id
                    })
            
            # 4. 按时间排序
            tasks.sort(key=lambda x: x['start'])
            
            return {
                "view_type": view_type,
                "time_range": {
                    "start": base_dt.isoformat(),
                    "end": end_dt.isoformat()
                },
                "resources": resources,
                "tasks": tasks
            }
            
        except Exception as e:
            logger.error(f"获取生产排产甘特图数据失败: {e}")
            return {
                "view_type": view_type,
                "time_range": {},
                "resources": [],
                "tasks": [],
                "error": str(e)
            }
    
    def _calculate_task_progress(self, status: str, task) -> int:
        """计算任务进度百分比"""
        status_progress = {
            '已排程': 0,
            '待执行': 0,
            '执行中': 50,
            '已完成': 100,
            '已取消': 0,
            '已延期': 50
        }
        
        base_progress = status_progress.get(status, 0)
        
        # 对于执行中的任务，可以根据实际时间计算更精确的进度
        if status == '执行中':
            try:
                start_str = getattr(task, 'planned_start_time', '')
                end_str = getattr(task, 'planned_end_time', '')
                actual_start_str = getattr(task, 'actual_start_time', '')
                
                if start_str and end_str and actual_start_str:
                    start = datetime.fromisoformat(start_str.replace('Z', '+00:00').replace('+00:00', ''))
                    end = datetime.fromisoformat(end_str.replace('Z', '+00:00').replace('+00:00', ''))
                    actual_start = datetime.fromisoformat(actual_start_str.replace('Z', '+00:00').replace('+00:00', ''))
                    
                    total_duration = (end - start).total_seconds()
                    elapsed = (datetime.now() - actual_start).total_seconds()
                    
                    if total_duration > 0:
                        time_progress = min(int((elapsed / total_duration) * 100), 100)
                        return max(base_progress, time_progress)
            except:
                pass
        
        return base_progress
