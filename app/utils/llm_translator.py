from app.utils.llm_client import LLMClient, llm_client
from app.config import settings
from typing import Optional, List, Dict
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
            temperature=0.3
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
            temperature=0.3
        )
        result = response.choices[0].message.content.strip()
        
        # 存入缓存
        _description_cache[cache_key] = result
        return result
    
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
            temperature=0.3
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
            temperature=0.3
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
            f"- 模型ID: {model['id']}, 名称: {model['name']}, 字段: {', '.join([f['field_id'] for f in model.get('fields', [])])}"
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
            f"- 任务ID: {task['id']}, 名称: {task['name']}, 能力: {', '.join([str(cap_id) for cap_id in task.get('capability_ids', [])])}"
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


# 全局翻译器实例
llm_translator = LLMTranslator()
