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
你是一位资深的数据架构师和业务分析师，请基于以下数据库表结构信息，分析并推断表之间的业务关系。

## 数据库表结构信息

{formatted_tables}

## 分析要求

1. **关系识别**: 仔细分析字段名、表名的语义，识别潜在的业务关系
2. **基数判断**: 根据业务逻辑判断正确的基数类型
3. **多对多检测**: 特别注意识别中间表（包含两个外键引用的表）
4. **业务语义**: 使用清晰、准确的中文描述业务含义

## 基数类型定义

- **one-to-one (一对一)**: 一个记录对应另一个表的一个记录（如：用户 ↔ 用户详情）
- **one-to-many (一对多)**: 一个记录对应另一个表的多个记录（如：客户 → 多个订单）
- **many-to-one (多对一)**: 多个记录对应另一个表的一个记录（如：多个订单 → 一个客户）
- **many-to-many (多对多)**: 多个记录对应另一个表的多个记录，通过中间表实现（如：产品 ↔ 物料）

## 输出格式要求

请严格按照以下JSON格式输出，不要包含任何其他内容：

{{
  "relationships": [
    {{
      "source_table": "源表名",
      "source_field": "源字段名",
      "target_table": "目标表名", 
      "target_field": "目标字段名",
      "cardinality": "基数类型",
      "name": "关系中文名称",
      "description": "关系详细业务说明",
      "intermediate_table": "中间表名（仅many-to-many时提供）",
      "intermediate_source_key": "中间表中指向源表的外键字段（仅many-to-many时提供）",
      "intermediate_target_key": "中间表中指向目标表的外键字段（仅many-to-many时提供）"
    }}
  ]
}}

## 输出示例

{{
  "relationships": [
    {{
      "source_table": "md_partner",
      "source_field": "id", 
      "target_table": "demand_order",
      "target_field": "customer_id",
      "cardinality": "one-to-many",
      "name": "客户发起需求单",
      "description": "`md_partner`表中类型为\"CUSTOMER\"的合作伙伴作为客户，发起`demand_order`表中的需求单；一个客户可发起多个需求单，一个需求单仅属于一个客户。"
    }},
    {{
      "source_table": "product",
      "source_field": "id",
      "target_table": "md_material", 
      "target_field": "id",
      "cardinality": "many-to-many",
      "name": "产品由物料组成",
      "description": "`product`表中的产品通过`product_bom`表（中间载体）与`md_material`表中的物料关联；一个产品由多个物料组成，一个物料可用于多个产品。",
      "intermediate_table": "product_bom",
      "intermediate_source_key": "product_id",
      "intermediate_target_key": "material_id"
    }}
  ]
}}

## 特别注意事项

1. **字段匹配**: 优先匹配字段名相似的字段（如 customer_id → id）
2. **业务逻辑**: 考虑实际业务场景，不要仅依赖技术约束
3. **完整性**: 尽可能发现所有合理的业务关系
4. **准确性**: 确保基数类型符合业务实际
5. **中间表识别**: 如果发现某个表包含两个外键引用，考虑它是否是中间表

现在请基于上述表结构信息，输出完整的业务关系分析结果。
"""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_client.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的数据架构师和业务分析师"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                extra_body={"enable_thinking": False}
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 提取JSON部分（处理可能的markdown代码块）
            if result_text.startswith("```json"):
                result_text = result_text[7:]  # 移除 ```json
                if result_text.endswith("```"):
                    result_text = result_text[:-3]  # 移除 ```
            
            result_json = json.loads(result_text)
            return result_json.get("relationships", [])
            
        except Exception as e:
            logger.error(f"Failed to infer relationships: {e}")
            return []
    
    def _format_tables_for_prompt(self, tables_info: Dict[str, Any]) -> str:
        """将表信息格式化为提示词友好的格式"""
        formatted = []
        
        for table_name, table_info in tables_info.items():
            columns = table_info.get('columns', [])
            pk = table_info.get('primary_key')
            fk_info = table_info.get('foreign_keys', [])
            
            table_str = f"### 表: {table_name}\n"
            table_str += f"- **主键**: {pk if pk else '无'}\n"
            table_str += "- **字段列表**:\n"
            
            for col in columns:
                col_info = f"  - `{col}`"
                # 添加外键信息（如果有）
                fk_target = None
                for fk in fk_info:
                    if col in fk.get('constrained_columns', []):
                        referred_table = fk.get('referred_table', '未知')
                        fk_target = f" → {referred_table}"
                        break
                
                if fk_target:
                    col_info += f" {fk_target}"
                table_str += f"{col_info}\n"
            
            formatted.append(table_str)
        
        return "\n".join(formatted)
    
    def batch_translate(self, texts: List[str]) -> Dict[str, str]:
        """批量翻译多个英文术语为中文（带缓存）"""
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        # 检查缓存
        cache_key = _generate_cache_key('batch_translate', texts)
        if cache_key in _batch_translate_cache:
            return _batch_translate_cache[cache_key]
        
        prompt = "请将以下英文技术术语批量翻译为中文，保持专业准确性，不要添加任何英文原文或解释，只返回中文翻译结果。\n\n"
        for i, text in enumerate(texts):
            prompt += f"{i+1}. {text}\n"
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手，能够批量翻译术语"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        
        result = {}
        lines = response.choices[0].message.content.strip().split('\n')
        for i, line in enumerate(lines):
            if i < len(texts):
                # 提取翻译结果，假设格式为 "1. 翻译结果"
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    result[texts[i]] = parts[1].strip()
                else:
                    result[texts[i]] = line.strip()
        
        # 存入缓存
        _batch_translate_cache[cache_key] = result
        return result
    
    def batch_generate_descriptions(self, texts: List[str]) -> Dict[str, str]:
        """批量为多个术语生成中文描述（带缓存）"""
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        # 检查缓存
        cache_key = _generate_cache_key('batch_description', texts)
        if cache_key in _batch_description_cache:
            return _batch_description_cache[cache_key]
        
        prompt = "请为以下数据库表名或字段名批量生成简洁的中文描述（每个1-2句话），只返回描述内容，不要包含字段名。\n\n"
        for i, text in enumerate(texts):
            prompt += f"{i+1}. {text}\n"
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手，能够批量生成描述"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        
        result = {}
        lines = response.choices[0].message.content.strip().split('\n')
        for i, line in enumerate(lines):
            if i < len(texts):
                # 提取描述结果，假设格式为 "1. 描述内容"
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    result[texts[i]] = parts[1].strip()
                else:
                    result[texts[i]] = line.strip()
        
        # 存入缓存
        _batch_description_cache[cache_key] = result
        return result
    
    def _generate_sensing_config_prompt(self, document_content: str, business_models: List[Dict]) -> str:
        """生成数据感知配置的提示词"""
        models_info = "\n".join([
            f"- 模型ID: {model['id']}, 名称: {model['name']}, 字段: {', '.join([f'{f['field_id']}({f['data_type']})' for f in model.get('fields', [])])}"
            for model in business_models
        ])
        
        return f"""
你是一个专业的数据驱动系统配置专家。请根据以下文档内容和可用的业务模型，生成数据感知配置。

文档内容：
{document_content}

可用业务模型：
{models_info}

请分析文档中提到的数据监控需求，并生成JSON格式的数据感知配置。每个配置应包含：
- name: 配置名称
- type: 感知类型 ("data_change" 或 "threshold")
- model_id: 关联的业务模型ID
- config: 配置参数（必须严格按照以下格式）

**对于数据变化感知 (type: "data_change")，config必须包含：**
- trigger_conditions: 触发条件数组，可选值: ["create", "update", "delete"]
- monitored_fields: 监控字段数组，使用业务模型中的field_id
- check_interval: 检查间隔（秒），数字类型，默认5

**对于阈值触发感知 (type: "threshold")，config必须包含：**
- monitored_field: 监控字段，使用业务模型中的field_id
- threshold_type: 阈值类型，"static"（固定阈值）或"dynamic"（动态阈值）
- 如果threshold_type是"static"，则包含:
  - threshold_value: 固定阈值，数字类型
- 如果threshold_type是"dynamic"，则包含:
  - threshold_field: 阈值字段，使用业务模型中的field_id  
- operator: 操作符，可选值: "gt"（大于）, "lt"（小于）, "eq"（等于）, "ne"（不等于）, "gte"（大于等于）, "lte"（小于等于）
- check_interval: 检查间隔（秒），数字类型，默认5

- description: 配置描述

只返回JSON数组，不要包含任何其他文本。
"""

    def _generate_drive_logic_prompt(self, document_content: str, sensing_configs: List[Dict], tasks: List[Dict]) -> str:
        """生成驱动逻辑的提示词"""
        # 注意：sensing_configs 是新生成的配置，使用临时ID进行标识
        configs_info = "\n".join([
            f"- 临时ID: {config['temp_id']}, 名称: {config['name']}, 类型: {config['type']}, 模型ID: {config.get('model_id', 'N/A')}"
            for config in sensing_configs
        ])
        
        tasks_info = "\n".join([
            f"- 任务ID: {task['id']}, 名称: {task['name']}, 所需能力: {', '.join(task.get('capability_names', []))}"
            for task in tasks
        ])
        
        return f"""
你是一个专业的数据驱动系统配置专家。请根据以下文档内容、数据感知配置和可用任务，生成驱动逻辑配置。

文档内容：
{document_content}

可用数据感知配置：
{configs_info}

可用任务：
{tasks_info}

请分析文档中的业务规则，并生成JSON格式的驱动逻辑配置。每个配置应包含：
- name: 逻辑名称
- type: 逻辑类型 ("first_order" 或 "script")
- config: 逻辑配置参数（必须严格按照以下格式）
- description: 逻辑描述
- event_temp_ids: 关联的数据感知配置临时ID列表（使用上面列出的临时ID）
- task_ids: 关联的任务ID列表

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

只返回JSON数组，不要包含任何其他文本。
"""

    def extract_sensing_configs_from_document(self, document_content: str, business_models: List[Dict]) -> List[Dict]:
        """从文档内容中提取数据感知配置"""
        prompt = self._generate_sensing_config_prompt(document_content, business_models)
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够从文档中提取结构化配置"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        
        try:
            result_text = response.choices[0].message.content.strip()
            # 提取JSON部分
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return []
        except Exception as e:
            logger.error(f"解析数据感知配置失败: {e}")
            return []

    def extract_drive_logics_from_document(self, document_content: str, sensing_configs: List[Dict], tasks: List[Dict]) -> List[Dict]:
        """从文档内容中提取驱动逻辑配置"""
        prompt = self._generate_drive_logic_prompt(document_content, sensing_configs, tasks)
        response = self.llm_client.chat.completions.create(
            model=self.llm_client.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够从文档中提取结构化配置"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            extra_body={"enable_thinking": False}
        )
        
        try:
            result_text = response.choices[0].message.content.strip()
            # 提取JSON部分
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return []
        except Exception as e:
            logger.error(f"解析驱动逻辑配置失败: {e}")
            return []
    
    def _build_sensing_config_parsing_prompt_with_examples(self, natural_language: str, business_models: List[Dict]) -> str:
        """构建数据感知配置解析提示词（带少样本示例和详细约束）"""
        models_info = "\n".join([
            f"- 模型ID: {model['id']}, 名称: {model['name']}, 字段: {', '.join([f'{f['field_id']}({f['data_type']})' for f in model.get('fields', [])])}"
            for model in business_models
        ])
        
        return f"""
你是一个专业的数据驱动系统配置专家。请根据以下自然语言描述和可用的业务模型，生成数据感知配置。

可用业务模型：
{models_info}

请分析自然语言描述中的数据监控需求，并生成JSON格式的数据感知配置。每个配置必须包含以下字段：

- name: 配置名称
- type: 感知类型 ("data_change" 或 "threshold") 
- model_id: 关联的业务模型ID
- config: 配置参数（必须严格按照以下格式）
- description: 配置描述

**对于数据变化感知 (type: "data_change")，config必须包含：**
- trigger_conditions: 触发条件数组，可选值: ["create", "update", "delete"]
- monitored_fields: 监控字段数组，使用业务模型中的field_id
- check_interval: 检查间隔（秒），数字类型，默认5

**对于阈值触发感知 (type: "threshold")，config必须包含：**
- monitored_field: 监控字段，使用业务模型中的field_id
- threshold_type: 阈值类型，"static"（固定阈值）或"dynamic"（动态阈值）
- 如果threshold_type是"static"，则包含:
  - threshold_value: 固定阈值，数字类型
- 如果threshold_type是"dynamic"，则包含:
  - threshold_field: 阈值字段，使用业务模型中的field_id  
- operator: 操作符，可选值: "gt"（大于）, "lt"（小于）, "eq"（等于）, "ne"（不等于）, "gte"（大于等于）, "lte"（小于等于）
- check_interval: 检查间隔（秒），数字类型，默认5

【示例1】
输入: "监控订单表的所有变更"
输出: {{
  "name": "订单变更监控",
  "type": "data_change", 
  "model_id": "orders",
  "config": {{
    "trigger_conditions": ["create", "update", "delete"],
    "monitored_fields": [],
    "check_interval": 5
  }},
  "description": "监控订单表的所有数据变更"
}}

【示例2】
输入: "当温度超过100度时告警"
输出: {{
  "name": "高温告警",
  "type": "threshold",
  "model_id": "sensors", 
  "config": {{
    "monitored_field": "temperature",
    "operator": "gt",
    "threshold_value": 100,
    "check_interval": 5,
    "threshold_type": "static"
  }},
  "description": "当温度超过100度时触发告警"
}}

【示例3】
输入: "当库存低于50时通知"
输出: {{
  "name": "低库存通知",
  "type": "threshold",
  "model_id": "inventory",
  "config": {{
    "monitored_field": "stock_level",
    "operator": "lt", 
    "threshold_value": 50,
    "check_interval": 10,
    "threshold_type": "static"
  }},
  "description": "当库存低于50时发送通知"
}}

现在请处理以下输入：
输入: "{natural_language}"
输出: 
"""

    def _build_drive_logic_parsing_prompt_with_examples(self, natural_language: str, tasks: List[Dict], events: List[Dict]) -> str:
        """构建驱动逻辑解析提示词（带少样本示例和详细约束）"""
        tasks_info = "\n".join([
            f"- 任务ID: {task['id']}, 名称: {task['name']}, 所需能力: {', '.join(task.get('capability_names', []))}"
            for task in tasks
        ])
        
        events_info = "\n".join([
            f"- 事件ID: {event['id']}, 名称: {event['name']}, 类型: {event['type']}, 模型ID: {event.get('model_id', 'N/A')}"
            for event in events
        ])
        
        return f"""
你是一个专业的数据驱动系统配置专家。请根据以下自然语言描述、可用任务和事件，生成驱动逻辑配置。

可用任务：
{tasks_info}

可用事件：
{events_info}

请分析自然语言描述中的业务规则，并生成JSON格式的驱动逻辑配置。每个配置必须包含以下字段：

- name: 逻辑名称
- type: 逻辑类型 ("first_order" 或 "script")
- config: 逻辑配置参数（必须严格按照以下格式）
- description: 逻辑描述
- event_ids: 关联的数据感知配置ID列表
- task_ids: 关联的任务ID列表

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
  "task_ids": [2]
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
  "task_ids": [4]
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
  "task_ids": [6, 7]
}}

现在请处理以下输入：
输入: "{natural_language}"
输出: 
"""

    def _build_sensing_config_explanation_prompt(self, config: Dict) -> str:
        """构建数据感知配置解释提示词"""
        config_json = json.dumps(config, ensure_ascii=False, indent=2)
        return f"""
你是一个专业的数据驱动系统配置专家。请将以下数据感知配置转换为简洁明了的中文自然语言描述。

配置信息：
{config_json}

请用一句简洁的中文描述这个配置的作用，避免使用技术术语，使用业务友好的语言。
只返回描述文本，不要包含任何其他内容。
"""

    def _build_drive_logic_explanation_prompt(self, logic: Dict) -> str:
        """构建驱动逻辑解释提示词"""
        logic_json = json.dumps(logic, ensure_ascii=False, indent=2)
        return f"""
你是一个专业的数据驱动系统配置专家。请将以下驱动逻辑配置转换为简洁明了的中文自然语言描述。

配置信息：
{logic_json}

请用一句简洁的中文描述这个逻辑的作用，避免使用技术术语，使用业务友好的语言。
只返回描述文本，不要包含任何其他内容。
"""

    def validate_sensing_config(self, config: Dict) -> Tuple[bool, str]:
        """验证数据感知配置的完整性"""
        required_fields = ['name', 'type', 'model_id', 'config']
        for field in required_fields:
            if field not in config:
                return False, f"缺少必需字段: {field}"
        
        config_type = config['type']
        if config_type == 'data_change':
            data_change_required = ['trigger_conditions', 'check_interval']
            for field in data_change_required:
                if field not in config['config']:
                    return False, f"data_change类型缺少必需字段: {field}"
        elif config_type == 'threshold':
            threshold_required = ['monitored_field', 'operator', 'check_interval', 'threshold_type']
            for field in threshold_required:
                if field not in config['config']:
                    return False, f"threshold类型缺少必需字段: {field}"
            
            # 验证阈值类型
            if config['config']['threshold_type'] == 'static' and 'threshold_value' not in config['config']:
                return False, "static阈值类型需要threshold_value字段"
            elif config['config']['threshold_type'] == 'dynamic' and 'threshold_field' not in config['config']:
                return False, "dynamic阈值类型需要threshold_field字段"
        
        return True, "验证通过"

    def validate_drive_logic(self, logic: Dict) -> Tuple[bool, str]:
        """验证驱动逻辑配置的完整性"""
        required_fields = ['name', 'type', 'config', 'event_ids', 'task_ids']
        for field in required_fields:
            if field not in logic:
                return False, f"缺少必需字段: {field}"
        
        logic_type = logic['type']
        if logic_type == 'first_order':
            # first_order类型可以没有pre_condition，但如果有必须是字符串
            if 'pre_condition' in logic['config'] and not isinstance(logic['config']['pre_condition'], str):
                return False, "first_order类型的pre_condition必须是字符串"
        elif logic_type == 'script':
            if 'script_content' not in logic['config']:
                return False, "script类型缺少script_content字段"
            if not isinstance(logic['config']['script_content'], str):
                return False, "script_content必须是字符串"
        
        # 验证event_ids和task_ids是数组
        if not isinstance(logic['event_ids'], list) or not isinstance(logic['task_ids'], list):
            return False, "event_ids和task_ids必须是数组"
        
        return True, "验证通过"

    def parse_natural_language_to_sensing_config(self, natural_language: str, business_models: List[Dict]) -> Dict:
        """将自然语言解析为数据感知配置（带少样本示例和详细约束验证）"""
        prompt = self._build_sensing_config_parsing_prompt_with_examples(natural_language, business_models)
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
                config = json.loads(json_match.group())
                # 验证配置
                is_valid, message = self.validate_sensing_config(config)
                if not is_valid:
                    logger.warning(f"配置验证失败: {message}")
                    return {}
                return config
            else:
                return {}
        except Exception as e:
            logger.error(f"解析数据感知配置失败: {e}")
            return {}

    def parse_natural_language_to_drive_logic(self, natural_language: str, tasks: List[Dict], events: List[Dict]) -> Dict:
        """将自然语言解析为驱动逻辑配置（带少样本示例和验证）"""
        prompt = self._build_drive_logic_parsing_prompt_with_examples(natural_language, tasks, events)
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


# 全局翻译器实例
llm_translator = LLMTranslator()
