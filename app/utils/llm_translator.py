from app.utils.llm_client import LLMClient, llm_client
from app.config import settings
from typing import Optional, List, Dict, Any, Tuple
from cachetools import TTLCache
from functools import wraps
import hashlib
import json
import re
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 创建缓存实例
# 翻译缓存：最多1000条，有效期1小时
_translate_cache = TTLCache(maxsize=1000, ttl=3600)
# 描述缓存：最多1000条，有效期1小时
_description_cache = TTLCache(maxsize=1000, ttl=3600)
# 批量翻译缓存：最多100条，有效期1小时
_batch_translate_cache = TTLCache(maxsize=100, ttl=3600)
# 批量描述缓存：最多100条，有效期1小时
_batch_description_cache = TTLCache(maxsize=100, ttl=3600)


def _generate_cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key_str.encode()).hexdigest()


class LLMTranslator:
    def __init__(self):
        self.llm_client = llm_client
    
    def translate_to_chinese(self, text: str) -> str:
        """将英文表名或字段名翻译为中文（带缓存）"""
        # 检查缓存
        cache_key = _generate_cache_key('translate', text)
        if cache_key in _translate_cache:
            return _translate_cache[cache_key]
        
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        prompt = f"请将以下英文技术术语翻译为中文，保持专业准确性，不要添加任何解释：{text}"
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        result = response.choices[0].message.content.strip()
        
        # 存入缓存
        _translate_cache[cache_key] = result
        return result
    
    def generate_description(self, text: str, context: Optional[str] = None) -> str:
        """基于表名或字段名生成中文描述（带缓存）"""
        # 检查缓存
        cache_key = _generate_cache_key('description', text, context)
        if cache_key in _description_cache:
            return _description_cache[cache_key]
        
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        if context:
            prompt = f"请基于以下上下文，为'{text}'生成一个简洁的中文描述（1-2句话）：{context}"
        else:
            prompt = f"请为'{text}'生成一个简洁的中文描述（1-2句话），假设它是数据库中的表名或字段名"
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        result = response.choices[0].message.content.strip()
        
        # 存入缓存
        _description_cache[cache_key] = result
        return result
    
    def infer_relationships(self, tables_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于表结构信息推断业务关系"""
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        # 格式化表信息用于提示词
        formatted_tables = self._format_tables_for_prompt(tables_info)
        
        prompt = f"""
你是一个数据库专家，请基于以下表结构信息推断业务关系。

表结构信息：
{formatted_tables}

请分析表之间的外键关系、业务语义，并生成JSON格式的关系列表。每个关系必须包含以下字段：
- source_table: 源表名
- source_field: 源字段名  
- target_table: 目标表名
- target_field: 目标字段名
- cardinality: 关系基数 ("one-to-one", "one-to-many", "many-to-one", "many-to-many")
- name: 关系名称（中文）
- description: 关系描述（中文）
- intermediate_table: 中间表名（仅many-to-many关系需要）

输出格式示例：
[
  {{
    "source_table": "orders",
    "source_field": "customer_id", 
    "target_table": "customers",
    "target_field": "id",
    "cardinality": "many-to-one",
    "name": "订单客户关系",
    "description": "订单属于某个客户"
  }}
]

请只输出JSON数组，不要包含其他内容。
"""
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的数据库架构师"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        
        try:
            result_text = response.choices[0].message.content.strip()
            # 提取JSON数组
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                relationships = json.loads(json_match.group())
                return relationships
            else:
                return []
        except Exception as e:
            logger.error(f"解析关系推断结果失败: {e}")
            return []
    
    def _format_tables_for_prompt(self, tables_info: Dict[str, Any]) -> str:
        """格式化表信息用于提示词"""
        formatted = []
        for table_name, info in tables_info.items():
            columns = info.get('columns', [])
            pk = info.get('primary_key')
            fks = info.get('foreign_keys', [])
            
            table_str = f"表名: {table_name}\n"
            table_str += f"  主键: {pk}\n"
            table_str += f"  字段: {', '.join(columns)}\n"
            if fks:
                fk_strs = []
                for fk in fks:
                    fk_strs.append(f"{fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}")
                table_str += f"  外键: {', '.join(fk_strs)}\n"
            formatted.append(table_str)
        
        return "\n".join(formatted)
    
    def batch_translate(self, texts: List[str]) -> Dict[str, str]:
        """批量翻译文本（带缓存）"""
        results = {}
        texts_to_translate = []
        
        # 先检查缓存
        for text in texts:
            cache_key = _generate_cache_key('translate', text)
            if cache_key in _translate_cache:
                results[text] = _translate_cache[cache_key]
            else:
                texts_to_translate.append(text)
        
        if not texts_to_translate:
            return results
        
        # 批量翻译未缓存的文本
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        prompt = "请将以下英文技术术语翻译为中文，保持专业准确性，每行一个翻译结果：\n" + "\n".join(texts_to_translate)
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        
        translations = response.choices[0].message.content.strip().split('\n')
        
        # 处理结果并存入缓存
        for i, text in enumerate(texts_to_translate):
            if i < len(translations):
                translation = translations[i].strip()
                results[text] = translation
                cache_key = _generate_cache_key('translate', text)
                _translate_cache[cache_key] = translation
            else:
                results[text] = text
        
        return results
    
    def batch_generate_descriptions(self, texts: List[str]) -> Dict[str, str]:
        """批量生成描述（带缓存）"""
        results = {}
        texts_to_describe = []
        
        # 先检查缓存
        for text in texts:
            cache_key = _generate_cache_key('description', text)
            if cache_key in _description_cache:
                results[text] = _description_cache[cache_key]
            else:
                texts_to_describe.append(text)
        
        if not texts_to_describe:
            return results
        
        # 批量生成未缓存的描述
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        prompt = "请为以下数据库字段名生成简洁的中文描述（1-2句话），每行一个描述：\n" + "\n".join(texts_to_describe)
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        
        descriptions = response.choices[0].message.content.strip().split('\n')
        
        # 处理结果并存入缓存
        for i, text in enumerate(texts_to_describe):
            if i < len(descriptions):
                description = descriptions[i].strip()
                results[text] = description
                cache_key = _generate_cache_key('description', text)
                _description_cache[cache_key] = description
            else:
                results[text] = ""
        
        return results
    
    def parse_natural_language_to_drive_logic(self, natural_language: str, actions: List[Dict], events: List[Dict]) -> Dict:
        """将自然语言解析为驱动逻辑配置（带少样本示例和验证）"""
        prompt = self._build_drive_logic_parsing_prompt_with_examples(natural_language, actions, events)
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够准确解析自然语言并生成结构化配置"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        
        try:
            result_text = response.choices[0].message.content.strip()
            # 提取JSON对象
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                logic = json.loads(json_match.group())
                # 验证配置
                is_valid, message = self.validate_drive_logic(logic)
                if not is_valid:
                    logger.warning(f"配置验证失败: {message}")
                    return {}
                return logic
            else:
                return {}
        except Exception as e:
            logger.error(f"解析驱动逻辑配置失败: {e}")
            return {}
    
    def _build_drive_logic_parsing_prompt_with_examples(self, natural_language: str, actions: List[Dict], events: List[Dict]) -> str:
        """构建驱动逻辑解析提示词（带少样本示例和详细约束）"""
        actions_info = "\n".join([
            f"- 行动ID: {action['id']}, 名称: {action['name']}, 目标模型: {action.get('target_model_id', 'N/A')}"
            for action in actions
        ])
        
        events_info = "\n".join([
            f"- 事件ID: {event['id']}, 名称: {event['name']}, 类型: {event['type']}, 模型ID: {event.get('model_id', 'N/A')}"
            for event in events
        ])
        
        return f"""
你是一个专业的数据驱动系统配置专家。请根据以下自然语言描述、可用行动和事件，生成驱动逻辑配置。

可用行动：
{actions_info}

可用事件：
{events_info}

请分析自然语言描述中的业务规则，并生成JSON格式的驱动逻辑配置。每个配置必须包含以下字段：

- name: 逻辑名称
- type: 逻辑类型 ("first_order" 或 "script")
- config: 逻辑配置参数（必须严格按照以下格式）
- description: 逻辑描述
- event_ids: 关联的数据感知配置ID列表
- action_ids: 关联的行动ID列表

**对于一阶函数 (type: "first_order")，config必须包含：**
- pre_condition: Python条件表达式（字符串类型，可选）
  - 必须是有效的Python表达式语法
  - 可以使用data字典访问事件数据，格式为: data.get('字段名', 默认值)
  - 支持比较操作符: ==, !=, >, <, >=, <=
  - 支持逻辑操作符: and, or, not
  - 示例: "data.get('status', '') == 'CONFIRMED'"
  - 示例: "data.get('total_amount', 0) > 10000 and data.get('currency', '') == 'CNY'"

**对于脚本函数 (type: "script")，config必须包含：**
- script_content: Python脚本内容（字符串类型，可选）
  - 脚本必须设置一个名为'result'的变量
  - result可以是布尔值，也可以是元组(True/False, processed_data)
  - 可以访问'event'变量（包含完整的事件数据）和'data_source'变量
  - 示例:
    ```python
    event_data = event.get('data', {{}})
    record_data = event_data.get('affected_records', [{{}}])[0].get('record', {{}})
    
    if record_data.get('total_amount', 0) > 10000:
        # 执行特殊审批和风险评估
        result = (True, event_data)
    else:
        result = (False, event_data)
    ```

【示例1】
输入: "如果订单金额大于10000，则需要经理审批"
输出: {{
  "name": "大额订单审批",
  "type": "first_order",
  "config": {{
    "pre_condition": "data.get('order_amount', 0) > 10000"
  }},
  "description": "当订单金额超过10000时触发经理审批流程",
  "event_ids": [1],
  "action_ids": [2]
}}

【示例2】
输入: "当温度异常时发送邮件通知"
输出: {{
  "name": "温度异常通知",
  "type": "first_order", 
  "config": {{
    "pre_condition": "data.get('temperature', 0) > 100 or data.get('temperature', 0) < 0"
  }},
  "description": "当温度超出正常范围时发送邮件告警",
  "event_ids": [3],
  "action_ids": [4]
}}

【示例3】
输入: "计算风险评分并根据结果分配不同处理流程"
输出: {{
  "name": "风险评分处理",
  "type": "script",
  "config": {{
    "script_content": "event_data = event.get('data', {{}})\\nrecord_data = event_data.get('affected_records', [{{}}])[0].get('record', {{}})\\n\\n# 计算风险评分\\namount = record_data.get('amount', 0)\\nfrequency = record_data.get('frequency', 0)\\nscore = amount * 0.1 + frequency * 0.2\\n\\nif score > 50:\\n    result = (True, event_data)\\nelse:\\n    result = (False, event_data)"
  }},
  "description": "基于多因素计算风险评分并决定处理流程",
  "event_ids": [5],
  "action_ids": [6, 7]
}}

现在请处理以下输入：
输入: "{natural_language}"
输出: 
"""

    def validate_drive_logic(self, logic: Dict) -> Tuple[bool, str]:
        """验证驱动逻辑配置的有效性"""
        required_fields = ['name', 'type', 'config', 'description', 'event_ids', 'action_ids']
        for field in required_fields:
            if field not in logic:
                return False, f"缺少必需字段: {field}"
        
        if logic['type'] not in ['first_order', 'script']:
            return False, "type必须是'first_order'或'script'"
        
        if not isinstance(logic['event_ids'], list):
            return False, "event_ids必须是列表"
        
        if not isinstance(logic['action_ids'], list):
            return False, "action_ids必须是列表"
        
        if logic['type'] == 'first_order':
            # first_order类型可以没有pre_condition
            if 'pre_condition' in logic['config'] and not isinstance(logic['config']['pre_condition'], str):
                return False, "pre_condition必须是字符串"
        elif logic['type'] == 'script':
            if 'script_content' not in logic['config']:
                return False, "script类型必须包含script_content"
            if not isinstance(logic['config']['script_content'], str):
                return False, "script_content必须是字符串"
        
        return True, "配置有效"

    def convert_sensing_config_to_natural_language(self, config: Dict) -> str:
        """将数据感知配置转换为自然语言描述"""
        prompt = self._build_sensing_config_explanation_prompt(config)
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够将技术配置转换为业务友好的自然语言描述"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        return response.choices[0].message.content.strip()

    def convert_drive_logic_to_natural_language(self, logic: Dict) -> str:
        """将驱动逻辑配置转换为自然语言描述"""
        prompt = self._build_drive_logic_explanation_prompt(logic)
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够将技术配置转换为业务友好的自然语言描述"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        return response.choices[0].message.content.strip()

    def _build_sensing_config_explanation_prompt(self, config: Dict) -> str:
        """构建数据感知配置解释提示词"""
        return f"""
你是一个专业的数据驱动系统配置专家。请将以下数据感知配置转换为业务友好的自然语言描述。

配置:
{json.dumps(config, ensure_ascii=False, indent=2)}

请用简洁明了的中文描述这个配置的作用，例如："监控订单表中订单金额的变化，当金额大于10000时触发告警"。

只输出描述文本，不要包含其他内容。
"""

    def _build_drive_logic_explanation_prompt(self, logic: Dict) -> str:
        """构建驱动逻辑配置解释提示词"""
        return f"""
你是一个专业的数据驱动系统配置专家。请将以下驱动逻辑配置转换为业务友好的自然语言描述。

配置:
{json.dumps(logic, ensure_ascii=False, indent=2)}

请用简洁明了的中文描述这个逻辑的作用，例如："当订单金额大于10000时，自动触发经理审批流程"。

只输出描述文本，不要包含其他内容。
"""


# 全局LLM翻译器实例
llm_translator = LLMTranslator()