"""询价Agent处理器"""
from datetime import datetime
import random
from typing import Dict, Any
from app.models.agent import Agent
from app.models.drive_logic import Task
from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InquiryHandler:
    """询价Agent处理器"""
    
    def __init__(self):
        pass
    
    def _generate_unique_code(self, prefix: str, table: str, column: str) -> str:
        """生成唯一的编码
        
        Args:
            prefix: 编码前缀，如 'INQ'
            table: 表名
            column: 列名
            
        Returns:
            唯一的编码，如 'INQ001'
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
    
    def execute_inquiry_agent(self, agent: Agent, task: Task, event: Dict[str, Any], trace_id: str = None, creation_log_id: str = None) -> Dict[str, Any]:
        """询价Agent执行逻辑"""
        try:
            material_data = event.get('record_data', {})
            material_id = material_data.get('id')
            material_code = material_data.get('material_code')
            base_price = float(material_data.get('base_price', 0))
            
            # 1. 获取活跃供应商（partner_type=SUPPLIER and status=ACTIVE）
            suppliers = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query="SELECT id FROM md_partner WHERE partner_type='SUPPLIER' AND status='ACTIVE'"
            )
            
            if not suppliers:
                return {
                    'success': False,
                    'error': '没有找到活跃的供应商',
                    'executed_at': datetime.now().isoformat()
                }
            
            # 随机选择一个供应商
            supplier = random.choice(suppliers)
            supplier_id = supplier['id']
            
            # 2. 获取价格规则
            price_rules = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query="SELECT threshold_percent FROM rule_price WHERE status='ACTIVE' LIMIT 1"
            )
            
            threshold_percent = 5.0  # 默认值
            if price_rules:
                threshold_percent = float(price_rules[0]['threshold_percent'])
            
            # 3. 计算reply_price（三种权重随机选择）
            # 权重：原值(0.3)、波动范围内(0.6)、波动范围外(0.1)
            rand_choice = random.random()
            reply_price = base_price
            
            if rand_choice < 0.3:
                # 使用原值
                reply_price = base_price
            elif rand_choice < 0.9:  # 0.3 + 0.6 = 0.9
                # 波动范围内：base_price ± threshold_percent%
                max_increase = base_price * (threshold_percent / 100)
                reply_price = base_price + random.uniform(-max_increase, max_increase)
            else:
                # 波动范围外：超过threshold_percent%的范围
                max_increase = base_price * (threshold_percent / 100)
                # 随机选择高于或低于范围
                if random.random() < 0.5:
                    # 高于范围
                    reply_price = base_price + max_increase + random.uniform(0, max_increase)
                else:
                    # 低于范围
                    reply_price = base_price - max_increase - random.uniform(0, max_increase)
            
            # 确保价格不为负数
            reply_price = max(reply_price, 0.01)
            
            # 4. 生成询价单号
            inquiry_no = self._generate_unique_code('INQ', 'inquiry_order', 'inquiry_no')
            
            # 5. 写入询价表
            inquiry_data = {
                'inquiry_no': inquiry_no,
                'demand_order_id': 0,  # 设置为空（使用0表示无关联需求单）
                'supplier_id': supplier_id,
                'material_id': material_id,
                'status': 'REPLIED',
                'reply_price': round(reply_price, 2),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            success = data_source_manager.execute_insert(
                data_source_name='commander_data_database',
                table_name='inquiry_order',
                data=inquiry_data
            )
            
            if not success:
                return {
                    'success': False,
                    'error': '创建询价单失败',
                    'executed_at': datetime.now().isoformat()
                }
            
            # 6. 获取刚插入的询价单ID
            inquiry_result = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query=f"SELECT id FROM inquiry_order WHERE inquiry_no = '{inquiry_no}'"
            )
            
            if not inquiry_result:
                return {
                    'success': False,
                    'error': '获取询价单ID失败',
                    'executed_at': datetime.now().isoformat()
                }
            
            inquiry_id = inquiry_result[0]['id']
            
            # 7. 写入价格快照表
            snapshot_data = {
                'material_id': material_id,
                'price': round(reply_price, 2),
                'valid_from': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source_type': 'INQUIRY',
                'source_id': inquiry_id
            }
            
            success = data_source_manager.execute_insert(
                data_source_name='commander_data_database',
                table_name='price_snapshot',
                data=snapshot_data
            )
            
            if not success:
                logger.warning(f"写入价格快照失败，但询价单已创建: {inquiry_no}")
            
            return {
                'success': True,
                'message': f"询价完成: {inquiry_no}",
                'executed_at': datetime.now().isoformat(),
                'input_data': material_data,
                'output_data': {
                    'status': 'completed',
                    'inquiry_id': inquiry_id,
                    'inquiry_no': inquiry_no,
                    'supplier_id': supplier_id,
                    'reply_price': round(reply_price, 2),
                    'updated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"执行询价失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'executed_at': datetime.now().isoformat()
            }