from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.models.agent import Agent
from app.config import settings
from app.models.drive_logic import Task
from app.utils.data_source_manager import data_source_manager
from app.utils.logger import get_logger
from app.utils.llm_translator import llm_translator
from app.engines.task_manager import task_manager
import json
import random

logger = get_logger(__name__)


class AgentExecutor:
    """Agent执行器 - 处理不同Agent的模拟执行逻辑"""
    
    def __init__(self):
        self.stats = {
            'executions': 0,
            'success': 0,
            'failed': 0
        }
    
    def _get_system_db_session(self):
        from app.utils.db_client import create_engine, sessionmaker
        engine = create_engine("sqlite:///data.db")
        Session = sessionmaker(bind=engine)
        return Session()
    
    def execute_agent_task(self, agent: Agent, task: Task, event: Dict[str, Any], trace_id: str = None) -> Dict[str, Any]:
        """
        执行Agent任务的具体逻辑 - 根据Agent名称和能力类型进行不同的模拟
        
        Args:
            agent: Agent对象
            task: 任务对象
            event: 触发事件
            trace_id: 追踪ID
            
        Returns:
            执行结果字典
        """
        try:
            self.stats['executions'] += 1
            
            # 根据Agent名称进行特定的模拟执行逻辑
            agent_name = agent.name
            
            # 可以在这里添加针对特定Agent名称的自定义逻辑
            if agent_name == "智能配方研发Agent":
                execution_result = self._execute_product_development(agent, task, event, trace_id)
            if agent_name == "询价Agent":
                execution_result = self._execute_quote_agent(agent, task, event, trace_id)
            if agent_name == "估价核算Agent	":
                execution_result = self._execute_evaluation_agent(agent, task, event, trace_id)
            # 添加更多特定Agent的执行逻辑...
            
            if execution_result.get('success', True):
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1
                
            return execution_result
            
        except Exception as e:
            logger.error(f"执行Agent任务失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'executed_at': datetime.now().isoformat()
            }
    
    def _default_execute(self, agent: Agent, task: Task, event: Dict[str, Any], trace_id: str = None) -> Dict[str, Any]:
        """默认执行逻辑"""
        return {
            'success': True,
            'message': f"Agent '{agent.name}' 成功执行了任务 '{task.name}'",
            'executed_at': datetime.now().isoformat(),
            'input_data': event.get('data', {}),
            'output_data': {
                'status': 'completed',
                'result': f"任务 '{task.name}' 已完成"
            }
        }
    
    def _generate_unique_code(self, prefix: str, table: str, column: str) -> str:
        """生成唯一的编码
        
        Args:
            prefix: 编码前缀，如 'PROD' 或 'MAT'
            table: 表名
            column: 列名
            
        Returns:
            唯一的编码，如 'PROD001' 或 'MAT004'
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
    
    def _execute_product_development(self, agent: Agent, task: Task, event: Dict[str, Any], trace_id: str = None) -> Dict[str, Any]:
        """产品研发Agent执行逻辑"""

        demand_data = event.get('data', {})
        demand_id = demand_data.get('id')
        demand_no = demand_data.get('demand_no')
        spec_requirement = demand_data.get('spec_requirement')

        if task.name == "智能配方研发任务":
            try:
                # 1. 获取现有物料
                materials = data_source_manager.execute_query(
                    data_source_name='commander_data_database',
                    query="SELECT * FROM md_material WHERE status = 'ACTIVE'"
                )
                
                # 2. 调用大模型生成BOM
                bom_result = self._generate_bom_with_llm(demand_data, materials)
                
                if not bom_result.get('success', False):
                    return {
                        'success': False,
                        'error': f'生成BOM失败: {bom_result.get("error", "未知错误")}',
                        'executed_at': datetime.now().isoformat()
                    }
                
                bom_items = bom_result.get('bom_items', [])
                new_materials = bom_result.get('new_materials', [])
                
                # 3. 创建新产品（初始状态DRAFT）
                # 生成唯一的product_code
                product_code = self._generate_unique_code('PROD', 'product', 'product_code')
                
                product_name = self._generate_product_name(spec_requirement)
                
                product_data = {
                    'product_code': product_code,
                    'product_name': product_name,
                    'specification': spec_requirement,
                    'product_type': 'CUSTOM',
                    'unit': '个',
                    'status': 'DRAFT',
                    'rnd_owner': '张三'
                }
                
                success = data_source_manager.execute_insert(
                    data_source_name='commander_data_database',
                    table_name='product',
                    data=product_data
                )
                
                if not success:
                    return {
                        'success': False,
                        'error': '创建产品失败',
                        'executed_at': datetime.now().isoformat()
                    }
                
                # 获取新创建的产品ID
                product_result = data_source_manager.execute_query(
                    data_source_name='commander_data_database',
                    query=f"SELECT id FROM product WHERE product_code = '{product_code}'"
                )
                if not product_result:
                    return {
                        'success': False,
                        'error': '获取产品ID失败',
                        'executed_at': datetime.now().isoformat()
                    }
                product_id = product_result[0]['id']
                
                # 4. 插入新物料/价格快照（如果有）并获取新物料ID
                material_code_to_id = {}
                for new_material in new_materials:
                    # 生成唯一的material_code
                    material_code = self._generate_unique_code('MAT', 'md_material', 'material_code')
                    new_material['material_code'] = material_code
                    
                    material_data = {
                        'material_code': material_code,
                        'material_name': new_material['material_name'],
                        'specification': new_material['specification'],
                        'unit': new_material['unit'],
                        'base_price': round(new_material['base_price'], 2),
                        'status': 'ACTIVE'
                    }
                    data_source_manager.execute_insert(
                    data_source_name='commander_data_database',
                        table_name='md_material',
                        data=material_data
                    )
                    
                    # 查询新插入的物料ID
                    material_result = data_source_manager.execute_query(
                        data_source_name='commander_data_database',
                        query=f"SELECT id FROM md_material WHERE material_code = '{material_code}'"
                    )
                    if material_result:
                        material_code_to_id[material_code] = material_result[0]['id']

                    # 写入价格快照表
                    snapshot_data = {
                        'material_id': material_result[0]['id'],
                        'price': round(new_material['base_price'], 2),
                        'valid_from': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source_type': 'BASE',
                        'source_id': material_result[0]['id']
                    }
                    
                    success = data_source_manager.execute_insert(
                        data_source_name='commander_data_database',
                        table_name='price_snapshot',
                        data=snapshot_data
                    )
                
                # 5. 维护产品BOM明细
                for item in bom_items:
                    # 如果是新物料，使用material_code获取ID
                    material_id = item['material_id']
                    if material_id is None and 'material_code' in item:
                        material_id = material_code_to_id.get(item['material_code'])
                    
                    if material_id is not None:
                        bom_data = {
                            'product_id': product_id,
                            'material_id': material_id,
                            'unit_usage': item['unit_usage'],
                            'loss_rate': item['loss_rate']
                        }
                        data_source_manager.execute_insert(
                            data_source_name='commander_data_database',
                            table_name='product_bom',
                            data=bom_data
                        )
                
                # 6. 产品研发完成，状态更新为ACTIVE
                product_update_data = {
                    'id': product_id,
                    'status': 'ACTIVE',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                data_source_manager.execute_update(
                    data_source_name='commander_data_database',
                    table_name='product',
                    data=product_update_data
                )
                
                # 7. 需求单关联产品
                demand_update_data = {
                    'id': demand_id,
                    'product_id': product_id
                }
                data_source_manager.execute_update(
                    data_source_name='commander_data_database',
                    table_name='demand_order',
                    data=demand_update_data
                )
                
                return {
                    'success': True,
                    'message': f"产品研发完成: {demand_no}",
                    'executed_at': datetime.now().isoformat(),
                    'input_data': demand_data,
                    'output_data': {
                        'status': 'completed',
                        'product_id': product_id,
                        'product_code': product_code,
                        'product_name': product_name,
                        'bom_count': len(bom_items),
                        'new_materials_count': len(new_materials),
                        'updated_at': datetime.now().isoformat()
                    }
                }
            except Exception as e:
                logger.error(f"执行产品研发失败: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'executed_at': datetime.now().isoformat()
                }
        elif task.name == "产品推荐任务":
            # 需要基于spec_requirement找到匹配的product
            product_info = self._find_matching_product(spec_requirement)
            if not product_info:
                return {
                    'success': False,
                    'error': f'未找到匹配规格要求的产品: {spec_requirement}',
                    'executed_at': datetime.now().isoformat()
                }
            product_id = product_info.get('id')
            product_code     = product_info.get('product_code')
            product_name = product_info.get('product_name')
            # 需求单关联产品
            demand_update_data = {
                'id': demand_id,
                'product_id': product_id
            }
            data_source_manager.execute_update(
                data_source_name='commander_data_database',
                table_name='demand_order',
                data=demand_update_data
            )
            
            return {
                'success': True,
                'message': f"产品推荐成功: {demand_no}",
                'executed_at': datetime.now().isoformat(),
                'input_data': demand_data,
                'output_data': {
                    'status': 'completed',
                    'product_id': product_id,
                    'product_code': product_code,
                    'product_name': product_name,
                    'updated_at': datetime.now().isoformat()
                }
            }
        else:
            logger.error(f"产品研发Agent执行失败: {str(task.name)}")
            return {
                'success': False,
                'error': "未知的任务类型",
                'executed_at': datetime.now().isoformat()
            }
    def _generate_bom_with_llm(self, demand_data: Dict[str, Any], existing_materials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """调用大模型生成BOM"""
        try:
            spec_requirement = demand_data.get('spec_requirement', '')
            
            # 构建现有物料列表
            materials_info = []
            for material in existing_materials:
                materials_info.append(
                    f"ID:{material['id']}, 编码:{material['material_code']}, 名称:{material['material_name']}, "
                    f"规格:{material['specification']}, 单位:{material['unit']}, 基准价:{material['base_price']}"
                )
            
            materials_str = "\n".join(materials_info)
            
            # 构建提示词
            prompt = f"""
你是一个专业的产品研发专家Demo，需要为以下需求设计产品BOM（物料清单）,请尽可能使用现有物料。

需求信息：
- 需求规格：{spec_requirement}

现有可用物料：
{materials_str}

请基于以上信息完成以下任务：
1. 分析需求规格，确定需要哪些物料
2. 优先使用现有物料，如果现有物料无法满足需求，可以建议新物料
3. 为每个物料确定单位用量和损耗率
4. 返回JSON格式的结果，包含以下字段：
   - bom_items: BOM明细列表，每个item包含：
     - material_id: 物料ID（使用现有物料时）
     - material_code: 物料编码（新物料时）（格式：MAT+3位数字，如MAT004）
     - material_name: 物料名称（新物料时）
     - specification: 物料规格（新物料时）
     - unit: 单位（新物料时）
     - base_price: 基准价（新物料时）
     - unit_usage: 单位用量
     - loss_rate: 损耗率（0-0.1之间的小数）

请只返回JSON格式的结果，不要包含任何其他说明注释、文字。
"""

            # 调用大模型
            response = llm_translator.llm_client.chat.completions.create(
                model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的产品研发专家，能够根据需求规格设计产品BOM"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 解析JSON结果
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError as e:
                # 尝试提取JSON部分
                import re
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    logger.error("无法解析大模型返回的JSON结果，使用模拟BOM生成逻辑")
                    return {
                        'success': False,
                        'error': str(e)
                    }
            
            # 处理BOM明细
            bom_items = []
            new_materials = []
            
            for item in result.get('bom_items', []):
                if 'material_id' in item and item['material_id']:
                    # 使用现有物料
                    bom_items.append({
                        'material_id': item['material_id'],
                        'unit_usage': item['unit_usage'],
                        'loss_rate': item['loss_rate']
                    })
                else:
                    # 新物料，需要先创建
                    new_materials.append({
                        'material_code': item['material_code'],
                        'material_name': item['material_name'],
                        'specification': item['specification'],
                        'unit': item['unit'],
                        'base_price': item['base_price']
                    })
                    # 新物料的ID会在插入后获取，这里先占位
                    bom_items.append({
                        'material_id': None,  # 稍后更新
                        'unit_usage': item['unit_usage'],
                        'loss_rate': item['loss_rate'],
                        'material_code': item['material_code']  # 用于后续匹配
                    })
            
            return {
                'success': True,
                'bom_items': bom_items,
                'new_materials': new_materials
            }
            
        except Exception as e:
            logger.error(f"调用大模型生成BOM失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_product_name(self, spec_requirement: str) -> str:
        """调用大模型生成产品名"""
        try:
            # 构建提示词
            prompt = f"""
请根据以下需求规格生成一个简洁、专业的产品名：

需求规格：{spec_requirement}

要求：
1. 产品名应准确反映产品的主要功能和特点
2. 产品名应简洁明了，不超过10个汉字
3. 产品名应专业、正式，适合商业使用
4. 请只返回产品名，不要包含任何其他说明文字
"""

            # 调用大模型
            response = llm_translator.llm_client.chat.completions.create(
                model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的产品命名专家，能够根据需求规格生成合适的产品名"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            product_name = response.choices[0].message.content.strip()
            return product_name
        except Exception as e:
            logger.error(f"调用大模型生成产品名失败: {str(e)}")
            # 降级方案：使用需求规格中的逗号改为-拼接作为产品名
            return spec_requirement.replace('，', '-')
    
    def _execute_quote_agent(self, agent: Agent, task: Task, event: Dict[str, Any], trace_id: str = None) -> Dict[str, Any]:
        """询价Agent执行逻辑"""
        try:
            material_data = event.get('data', {})
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
            import random
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
                return {
                    'success': False,
                    'error': '创建价格快照失败',
                    'executed_at': datetime.now().isoformat()
                }
            
            return {
                'success': True,
                'message': f"询价完成: {material_code}",
                'executed_at': datetime.now().isoformat(),
                'input_data': material_data,
                'output_data': {
                    'status': 'completed',
                    'inquiry_no': inquiry_no,
                    'supplier_id': supplier_id,
                    'reply_price': round(reply_price, 2),
                    'material_id': material_id,
                    'inquiry_id': inquiry_id,
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
    
    def _find_matching_product(self, spec_requirement: str) -> Dict[str, Any]:
        """
        基于规格要求查找匹配的产品
        """
        try:
            if spec_requirement is None:
                return None
                
            # 解析规格要求
            req_specs = set([spec.strip() for spec in spec_requirement.split('，') if spec.strip()])
            if not req_specs:
                return None
            
            # 构建带有过滤条件的查询
            keywords = list(req_specs)
            if keywords:
                where_conditions = []
                for keyword in keywords:
                    where_conditions.append(f"specification LIKE '%{keyword}%'")
                
                where_clause = " WHERE " + " AND ".join(where_conditions)
                query = f"SELECT * FROM product{where_clause} AND status = 'ACTIVE'"
            else:
                query = "SELECT * FROM product WHERE status = 'ACTIVE'"
            
            results = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query=query,
                max_rows=1000
            )
            
            if not results:
                return None
            
            # 检查每个产品的规格是否覆盖要求
            for result in results:
                product_spec = result.get('specification', '')
                if not product_spec:
                    continue
                
                product_specs = set([spec.strip() for spec in product_spec.split('，') if spec.strip()])
                
                # 检查规格要求是否完全被产品规格覆盖
                if req_specs.issubset(product_specs):
                    return result
            
            return None
        except Exception as e:
            logger.error(f"查找匹配产品失败: {str(e)}")
            return None
    
    def _check_material_price_fluctuation_with_date(self, material_id: int) -> bool:
        """
        检查物料价格波动，同时检查最新价格快照是否超过一天
        """
        try:
            if material_id is None:
                return True
            
            # 查询最新的三笔价格快照，包含valid_from日期
            price_query = f"""
            SELECT price, valid_from 
            FROM price_snapshot 
            WHERE material_id = {material_id} 
            ORDER BY valid_from DESC 
            LIMIT 3
            """
            
            price_results = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query=price_query,
                max_rows=3
            )
            
            # 若查到小于三笔，返回true
            if len(price_results) < 3:
                return True
            
            # 获取价格阈值
            threshold_query = """
            SELECT threshold_percent 
            FROM rule_price 
            WHERE status = 'ACTIVE' 
            LIMIT 1
            """
            
            threshold_results = data_source_manager.execute_query(
                data_source_name='commander_data_database',
                query=threshold_query,
                max_rows=1
            )
            
            threshold_percent = 5.0
            if threshold_results:
                threshold_percent = threshold_results[0].get('threshold_percent', 5.0)
            
            # 提取价格并计算波动
            prices = [result.get('price', 0) for result in price_results]
            
            # 计算价格间的波动
            price_fluctuation_exceeds = False
            for i in range(len(prices) - 1):
                price1 = prices[i]
                price2 = prices[i + 1]
                
                if price2 == 0:
                    continue
                    
                fluctuation = abs((price1 - price2) / price2 * 100)
                if fluctuation > threshold_percent:
                    price_fluctuation_exceeds = True
                    break
            
            # 检查最新价格快照是否超过一天
            latest_valid_from = price_results[0].get('valid_from', '')
            if latest_valid_from:
                try:
                    latest_date = datetime.strptime(latest_valid_from, '%Y-%m-%d %H:%M:%S')
                    one_day_ago = datetime.now() - timedelta(days=1)
                    price_snapshot_too_old = latest_date < one_day_ago
                except:
                    price_snapshot_too_old = True
            else:
                price_snapshot_too_old = True
            
            # 如果价格波动超过阈值且最新价格快照超过一天，则返回true
            if price_fluctuation_exceeds and price_snapshot_too_old:
                return True
            
            # 如果价格快照少于3笔，也返回true（已经在前面处理了）
            return False
            
        except Exception as e:
            logger.error(f"检查物料价格波动和日期失败: {str(e)}")
            return True
    
    def _execute_evaluation_agent(self, agent: Agent, task: Task, event: Dict[str, Any], trace_id: str = None) -> Dict[str, Any]:
        """估价核算Agent执行逻辑"""
        try:
            demand_data = event.get('data', {})
            
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
                
                price_results = data_source_manager.execute_query(
                    data_source_name='commander_data_database',
                    query=price_query,
                    max_rows=1
                )
                
                current_price = 0.0
                if price_results:
                    current_price = float(price_results[0].get('price', 0))
                
                # 检查是否需要询价
                need_inquiry = False
                
                # 查询最新的三笔价格快照数量
                three_prices_query = f"""
                SELECT COUNT(*) as count 
                FROM price_snapshot 
                WHERE material_id = {material_id}
                """
                count_result = data_source_manager.execute_query(
                    data_source_name='commander_data_database',
                    query=three_prices_query,
                    max_rows=1
                )
                price_count = count_result[0].get('count', 0) if count_result else 0
                
                if price_count < 3:
                    need_inquiry = True
                else:
                    # 检查价格波动和日期
                    if self._check_material_price_fluctuation_with_date(material_id):
                        need_inquiry = True
                
                if need_inquiry:
                    materials_needing_inquiry.append({
                        'material_id': material_id,
                        'current_price': current_price
                    })
                
                # 计算物料成本（即使需要询价，也先用当前价格计算）
                effective_usage = unit_usage * (1 + loss_rate)
                material_cost = effective_usage * current_price
                total_material_cost += material_cost
            
            # 3. 如果有物料需要询价，同步执行询价任务并获取新价格
            if materials_needing_inquiry:
                logger.info(f"发现 {len(materials_needing_inquiry)} 个物料需要询价，开始同步询价...")
                
                # 获取询价任务
                db = self._get_system_db_session()
                try:
                    quote_task = db.query(Task).filter(Task.name == "物料询价").first()
                    if not quote_task:
                        logger.warning("未找到询价任务，跳过询价")
                    else:
                        # 为每个需要询价的物料执行询价
                        for material_info in materials_needing_inquiry:
                            material_id = material_info['material_id']
                            
                            # 获取物料详细信息
                            material_query = f"SELECT * FROM md_material WHERE id = {material_id}"
                            material_result = data_source_manager.execute_query(
                                data_source_name='commander_data_database',
                                query=material_query,
                                max_rows=1
                            )
                            
                            if material_result:
                                material_data = material_result[0]
                                # 构造询价事件
                                quote_event = {
                                    "data": material_data
                                }
                                
                                # 同步执行询价任务
                                quote_result = task_manager.assign_and_wait_for_task(
                                    quote_task, 
                                    quote_event, 
                                    trace_id, 
                                    timeout=60  # 1分钟超时
                                )
                                
                                if quote_result['success']:
                                    # 获取新的报价
                                    new_price = quote_result['result']['output_data']['reply_price']
                                    logger.info(f"物料 {material_id} 询价成功，新价格: {new_price}")
                                    
                                    # 更新该物料的价格用于成本计算
                                    # 找到对应的BOM项并更新价格
                                    for bom_item in bom_items:
                                        if bom_item.get('material_id') == material_id:
                                            unit_usage = float(bom_item.get('unit_usage', 0))
                                            loss_rate = float(bom_item.get('loss_rate', 0))
                                            effective_usage = unit_usage * (1 + loss_rate)
                                            # 从总成本中减去旧价格，加上新价格
                                            old_material_cost = effective_usage * material_info['current_price']
                                            new_material_cost = effective_usage * new_price
                                            total_material_cost = total_material_cost - old_material_cost + new_material_cost
                                            break
                                else:
                                    logger.warning(f"物料 {material_id} 询价失败: {quote_result.get('error', 'Unknown error')}")
                finally:
                    db.close()
            
            # 4. 计算总成本和建议报价
            # 材料成本就是总成本（简化模型）
            total_cost = total_material_cost
            # 上浮20%利润
            suggested_price = total_cost * 1.2
            
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
                'input_data': event_data,
                'output_data': {
                    'status': 'completed',
                    'calc_no': calc_no,
                    'calc_id': calc_id,
                    'product_id': product_id,
                    'demand_order_id': demand_order_id,
                    'material_cost': round(total_material_cost, 2),
                    'total_cost': round(total_cost, 2),
                    'suggested_price': round(suggested_price, 2),
                    'materials_needing_inquiry': len(materials_needing_inquiry),
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
    
# 全局Agent执行器实例
agent_executor = AgentExecutor()