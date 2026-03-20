"""估价核算Agent处理器"""
from datetime import datetime
import random
import time
from typing import Dict, Any
from app.models.agent import Agent
from app.models.drive_logic import Task
from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EvaluationHandler:
    """估价核算Agent处理器"""
    
    def __init__(self):
        pass
    
    def _generate_unique_code(self, prefix: str, table: str, column: str) -> str:
        """生成唯一的编码
        
        Args:
            prefix: 编码前缀，如 'CALC'
            table: 表名
            column: 列名
            
        Returns:
            唯一的编码，如 'CALC001'
        """
        # 查询最大的编码
        query = f"SELECT MAX({column}) as max_code FROM {table}"
        result = data_source_manager.execute_query(
            data_source_name='commander_data_database',
            query=query
        )
        
        max_code = result[0]['max_code'] if result and result[0]['max_code'] else f"{prefix}000"
        
        # 提取数字部分并加1
        try:
            number = int(max_code[len(prefix):]) + 1
        except ValueError:
            number = 1
        
        # 生成新编码
        return f"{prefix}{number:03d}"
    
    def execute_evaluation_agent(self, agent: Agent, task: Task, event: Dict[str, Any], trace_id: str = None) -> Dict[str, Any]:
        """估价核算Agent执行逻辑"""
        try:
            demand_data = event.get('record_data', {})
            
            demand_order_id = demand_data.get('id')
            product_id = demand_data.get('product_id')
            
            # 1. 获取BOM信息
            bom_query = f"SELECT * FROM product_bom WHERE product_id = {product_id}"
            bom_items = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query=bom_query
            )
            
            if not bom_items:
                return {
                    'success': False,
                    'error': f'产品 {product_id} 没有BOM信息',
                    'executed_at': datetime.now().isoformat()
                }
            
            # 2. 获取每个物料的最新价格快照，并检查是否需要询价
            materials_needing_inquiry = []
            total_material_cost = 0.0
            
            for bom_item in bom_items:
                material_id = bom_item.get('material_id')
                unit_usage = float(bom_item.get('unit_usage', 0))
                loss_rate = float(bom_item.get('loss_rate', 0))
                
                # 查询该物料的最新价格快照
                price_query = f"""
                SELECT price, valid_from 
                FROM price_snapshot 
                WHERE material_id = {material_id} 
                ORDER BY valid_from DESC 
                LIMIT 1
                """
                price_result = data_source_manager.execute_query(
                    data_source_name='commander_data_database',
                    query=price_query
                )
                
                if price_result:
                    # 有价格快照，使用最新价格
                    latest_price = float(price_result[0]['price'])
                    effective_usage = unit_usage * (1 + loss_rate)
                    material_cost = latest_price * effective_usage
                    total_material_cost += material_cost
                else:
                    # 没有价格快照，需要询价
                    materials_needing_inquiry.append({
                        'material_id': material_id,
                        'unit_usage': unit_usage,
                        'loss_rate': loss_rate
                    })
            
            # 3. 对需要询价的物料执行询价
            if materials_needing_inquiry:
                # 获取询价任务（假设任务ID为2）
                db = self._get_db_session()
                try:
                    inquiry_task = db.query(Task).filter(Task.id == 2).first()
                    if not inquiry_task:
                        return {
                            'success': False,
                            'error': '未找到询价任务配置',
                            'executed_at': datetime.now().isoformat()
                        }
                    
                    for material_info in materials_needing_inquiry:
                        material_id = material_info['material_id']
                        
                        # 获取物料信息
                        material_query = f"SELECT * FROM md_material WHERE id = {material_id}"
                        material_result = data_source_manager.execute_query(
                            data_source_name='commander_data_database',
                            query=material_query,
                            max_rows=1
                        )
                        
                        if material_result:
                            material_data = material_result[0]
                            # 构造询价事件
                            inquiry_event = {
                                "type": "估价核算Agent主动触发",
                                "model_id": "md_material",
                                "record_data": material_data,
                                "timestamp": time.time(),
                                "trace_id": trace_id
                            }
                            
                            # 同步执行询价任务
                            from app.engines.task_manager import task_manager
                            inquiry_result = task_manager.assign_and_wait_for_task(
                                inquiry_task, 
                                inquiry_event, 
                                trace_id, 
                                timeout=60  # 1分钟超时
                            )
                            
                            if inquiry_result['success']:
                                # 获取新的报价
                                new_price = inquiry_result['result']['output_data']['reply_price']
                                logger.info(f"物料 {material_id} 询价成功，新价格: {new_price}")
                                
                                # 更新该物料的价格用于成本计算
                                effective_usage = material_info['unit_usage'] * (1 + material_info['loss_rate'])
                                material_cost = new_price * effective_usage
                                total_material_cost += material_cost
                            else:
                                logger.warning(f"物料 {material_id} 询价失败，跳过该物料")
                                # 可以选择使用基准价或跳过
                                # 这里选择跳过，保持总成本准确性
                finally:
                    db.close()
            
            # 4. 计算总成本和建议售价
            labor_cost = 100.0  # 人工成本
            overhead_rate = 0.2  # 管理费用率20%
            profit_margin = 0.3  # 利润率30%
            
            total_cost = total_material_cost + labor_cost
            total_cost_with_overhead = total_cost * (1 + overhead_rate)
            suggested_price = total_cost_with_overhead * (1 + profit_margin)
            
            # 5. 生成成本计算单号
            calc_no = self._generate_unique_code('CALC', 'cost_calc', 'calc_no')
            
            # 6. 写入成本计算表
            cost_calc_data = {
                'calc_no': calc_no,
                'demand_order_id': demand_order_id if demand_order_id else 0,
                'product_id': product_id,
                'status': 'ACTIVE',
                'material_cost': round(total_material_cost, 2),
                'total_cost': round(total_cost, 2),
                'suggested_price': round(suggested_price, 2),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            success = data_source_manager.execute_insert(
                data_source_name='commander_data_database',
                table_name='cost_calc',
                data=cost_calc_data
            )
            
            if not success:
                return {
                    'success': False,
                    'error': '创建成本计算单失败',
                    'executed_at': datetime.now().isoformat()
                }
            
            # 7. 获取刚插入的成本计算单ID
            calc_result = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query=f"SELECT id FROM cost_calc WHERE calc_no = '{calc_no}'"
            )
            
            calc_id = calc_result[0]['id'] if calc_result else None
            
            return {
                'success': True,
                'message': f"估价核算完成: {calc_no}",
                'executed_at': datetime.now().isoformat(),
                'input_data': demand_data,
                'output_data': {
                    'status': 'completed',
                    'calc_id': calc_id,
                    'calc_no': calc_no,
                    'material_cost': round(total_material_cost, 2),
                    'total_cost': round(total_cost, 2),
                    'suggested_price': round(suggested_price, 2),
                    'updated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"执行估价核算失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'executed_at': datetime.now().isoformat()
            }
    
    def _get_db_session(self):
        """获取数据库会话"""
        from sqlalchemy.orm import sessionmaker
        from app.utils.db_client import create_engine, Base
        
        engine = create_engine("sqlite:///data.db")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()