"""报价Agent处理器"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.models.agent import Agent
from app.models.drive_logic import Task
from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QuoteHandler:
    """报价Agent处理器"""
    
    def __init__(self):
        pass
    
    def _generate_unique_code(self, prefix: str, table: str, column: str) -> str:
        """生成唯一的编码
        
        Args:
            prefix: 编码前缀，如 'QUOT'
            table: 表名
            column: 列名
            
        Returns:
            唯一的编码，如 'QUOT001'
        """
        # 查询最大的编码
        query = f"SELECT MAX({column}) as max_code FROM {table}"
        result = data_source_manager.execute_query(
            data_source_name='commander_data_database',
            query=query
        )
        
        # 安全地获取max_code值
        max_code = None
        if result and len(result) > 0:
            max_code = result[0].get('max_code')
        
        if not max_code:
            max_code = f"{prefix}000"
        
        # 提取数字部分并加1
        try:
            number = int(max_code[len(prefix):]) + 1
        except (ValueError, IndexError):
            number = 1
        
        # 生成新编码
        return f"{prefix}{number:03d}"
    
    def execute_quote_agents(self, agents: List[Agent], tasks: List[Task], event: Dict[str, Any], trace_id: str = None) -> Dict[str, Any]:
        """报价Agent执行逻辑"""
        try:
            # 获取cost_calc事件数据
            cost_calc_data = event.get('record_data', {})
            
            # 1. 基于demand_order_id找到对应的需求信息
            demand_order_id = cost_calc_data.get('demand_order_id')
            if not demand_order_id:
                return {
                    'success': False,
                    'error': '缺少demand_order_id',
                    'executed_at': datetime.now().isoformat()
                }
            
            # 查询需求订单信息
            demand_query = f"SELECT * FROM demand_order WHERE id = {demand_order_id}"
            demand_result = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query=demand_query,
                max_rows=1
            )
            
            if not demand_result:
                return {
                    'success': False,
                    'error': f'未找到需求订单: {demand_order_id}',
                    'executed_at': datetime.now().isoformat()
                }
            
            demand_order = demand_result[0]
            quantity = float(demand_order.get('quantity', 1))
            customer_id = demand_order.get('customer_id')
            product_id = demand_order.get('product_id')
            
            # 2. 计算单价（总价格/数量）
            suggested_price = float(cost_calc_data.get('suggested_price', 0))
            if quantity <= 0:
                return {
                    'success': False,
                    'error': '需求订单数量必须大于0',
                    'executed_at': datetime.now().isoformat()
                }
            
            unit_price = round(suggested_price / quantity, 2)
            total_price = suggested_price
            
            # 3. 设置有效日期为三天后
            valid_until = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            
            # 4. 生成报价单号
            quotation_no = self._generate_unique_code('QUOT', 'quotation', 'quotation_no')
            
            # 5. 写入询价表
            quotation_data = {
                'quotation_no': quotation_no,
                'demand_order_id': demand_order_id,
                'customer_id': customer_id,
                'product_id': product_id,
                'cost_calc_id': cost_calc_data.get('id'),
                'status': 'ACTIVE',
                'unit_price': unit_price,
                'total_price': total_price,
                'valid_until': valid_until,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            success = data_source_manager.execute_insert(
                data_source_name='commander_data_database',
                table_name='quotation',
                data=quotation_data
            )
            
            if not success:
                return {
                    'success': False,
                    'error': '创建报价单失败',
                    'executed_at': datetime.now().isoformat()
                }
            
            # 6. 获取刚插入的报价单ID
            quotation_result = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query=f"SELECT id FROM quotation WHERE quotation_no = '{quotation_no}'"
            )
            
            quotation_id = quotation_result[0]['id'] if quotation_result else None
            
            return {
                'success': True,
                'message': f"报价完成: {quotation_no}",
                'executed_at': datetime.now().isoformat(),
                'input_data': cost_calc_data,
                'output_data': {
                    'status': 'completed',
                    'quotation_id': quotation_id,
                    'quotation_no': quotation_no,
                    'unit_price': unit_price,
                    'total_price': total_price,
                    'valid_until': valid_until,
                    'updated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"执行报价失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'executed_at': datetime.now().isoformat()
            }