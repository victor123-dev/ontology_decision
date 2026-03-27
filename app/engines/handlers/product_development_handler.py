"""产品研发Agent处理器"""
from datetime import datetime
import json
import re
from typing import Dict, Any, List
from app.models.agent import Agent
from app.models.drive_logic import Task
from app.utils.data_source_manager import data_source_manager
from app.utils.llm_translator import llm_translator
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProductDevelopmentHandler:
    """产品研发Agent处理器"""
    
    def __init__(self):
        pass
    
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
                if req_specs.issubset(product_specs):
                    return result
            
            # 如果没有完全匹配的，返回第一个结果
            return results[0]
            
        except Exception as e:
            logger.error(f"查找匹配产品失败: {str(e)}")
            return None
    
    def execute_product_development(self, agent: Agent, task: Task, event: Dict[str, Any], trace_id: str = None, creation_log_id: str = None) -> Dict[str, Any]:
        """产品研发Agent执行逻辑"""

        demand_data = event.get('record_data', {})
        demand_id = demand_data.get('id')
        demand_no = demand_data.get('demand_no')
        spec_requirement = demand_data.get('spec_requirement')

        if task.name == "产品研发任务":
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
        elif task.name == "产品匹配任务":
            # 需要基于spec_requirement找到匹配的product
            product_info = self._find_matching_product(spec_requirement)
            if not product_info:
                return {
                    'success': False,
                    'error': f'未找到匹配规格要求的产品: {spec_requirement}',
                    'executed_at': datetime.now().isoformat()
                }
            product_id = product_info.get('id')
            product_code = product_info.get('product_code')
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
            logger.error(f"智能配方研发Agent执行失败: {str(task.name)}")
            return {
                'success': False,
                'error': "未知的任务类型",
                'executed_at': datetime.now().isoformat()
            }