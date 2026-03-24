# 自然语言规则接口功能代码样例（增强版）

## 1. 扩展LLMTranslator类 (app/utils/llm_translator.py)

在现有 `LLMTranslator` 类中添加以下方法，使用少样本提示词和配置验证：

```python
import re
import json
from app.utils.logger import get_logger

logger = get_logger(__name__)

def _build_sensing_config_parsing_prompt_with_examples(self, natural_language: str, business_models: List[Dict]) -> str:
    """构建数据感知配置解析提示词（带少样本示例）"""
    models_info = "\n".join([
        f"- 模型ID: {model['id']}, 名称: {model['name']}, 字段: {', '.join([f'{f['field_id']}({f['data_type']})' for f in model.get('fields', [])])}"
        for model in business_models
    ])
    
    return f"""
你是一个专业的数据驱动系统配置专家。请根据以下自然语言描述和可用的业务模型，生成数据感知配置。

可用业务模型：
{models_info}

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
    """构建驱动逻辑解析提示词（带少样本示例）"""
    tasks_info = "\n".join([
        f"- 任务ID: {task['id']}, 名称: {task['name']}"
        for task in tasks
    ])
    
    events_info = "\n".join([
        f"- 事件ID: {event['id']}, 名称: {event['name']}"
        for event in events
    ])
    
    return f"""
你是一个专业的数据驱动系统配置专家。请根据以下自然语言描述、可用任务和事件，生成驱动逻辑配置。

可用任务：
{tasks_info}

可用事件：
{events_info}

【示例1】
输入: "如果订单金额大于10000，则需要经理审批"
输出: {{
  "name": "大额订单审批",
  "type": "first_order",
  "config": {{
    "pre_condition": "order_amount > 10000"
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
    "pre_condition": "temperature > 100 or temperature < 0"
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
    "script_content": "def calculate_risk_score(data):\\n    # 计算风险评分逻辑\\n    score = data.get('amount', 0) * 0.1 + data.get('frequency', 0) * 0.2\\n    return score > 50"
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

def validate_sensing_config(self, config: Dict) -> tuple[bool, str]:
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

def validate_drive_logic(self, logic: Dict) -> tuple[bool, str]:
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
    """将自然语言解析为数据感知配置（带少样本示例和验证）"""
    prompt = self._build_sensing_config_parsing_prompt_with_examples(natural_language, business_models)
    response = self.llm_client.chat.completions.create(
        model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
        messages=[
            {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够准确解析自然语言并生成结构化配置"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
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
        model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
        messages=[
            {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够准确解析自然语言并生成结构化配置"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
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
        model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
        messages=[
            {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够将技术配置转换为业务友好的自然语言描述"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def convert_drive_logic_to_natural_language(self, logic: Dict) -> str:
    """将驱动逻辑配置转换为自然语言描述"""
    prompt = self._build_drive_logic_explanation_prompt(logic)
    response = self.llm_client.chat.completions.create(
        model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
        messages=[
            {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够将技术配置转换为业务友好的自然语言描述"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()
```

## 2. 后端API接口 (app/api/nl_rule_interface.py)

保持原有接口不变，但内部调用已增强的方法：

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.utils.llm_translator import llm_translator
from app.models.business_model import BusinessModel
from app.models.data_sensing import DataSensingConfig
from app.models.drive_logic import DriveLogic, Task

router = APIRouter()

def get_db():
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/nl-rule-interface/parse-sensing-config")
def parse_natural_language_to_sensing_config(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """将自然语言解析为数据感知配置"""
    natural_language = request_data.get("natural_language", "")
    if not natural_language:
        raise HTTPException(status_code=400, detail="自然语言描述不能为空")
    
    try:
        # 获取所有业务模型
        business_models = []
        models = db.query(BusinessModel).all()
        for model in models:
            db.refresh(model)
            business_models.append({
                "id": model.id,
                "name": model.name,
                "fields": [{"field_id": f.field_id, "name": f.name, "data_type": f.data_type} for f in model.fields] if model.fields else []
            })
        
        # 调用LLM解析（已包含少样本示例和验证）
        config = llm_translator.parse_natural_language_to_sensing_config(
            natural_language, business_models
        )
        
        if not config:
            raise HTTPException(status_code=400, detail="无法解析自然语言描述，请参考示例格式")
        
        return {
            "success": True,
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@router.post("/nl-rule-interface/parse-drive-logic")
def parse_natural_language_to_drive_logic(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """将自然语言解析为驱动逻辑配置"""
    natural_language = request_data.get("natural_language", "")
    if not natural_language:
        raise HTTPException(status_code=400, detail="自然语言描述不能为空")
    
    try:
        # 获取所有任务和事件
        tasks = []
        task_list = db.query(Task).all()
        for task in task_list:
            db.refresh(task)
            tasks.append({
                "id": task.id,
                "name": task.name
            })
        
        events = []
        event_list = db.query(DataSensingConfig).all()
        for event in event_list:
            db.refresh(event)
            events.append({
                "id": event.id,
                "name": event.name
            })
        
        # 调用LLM解析（已包含少样本示例和验证）
        logic = llm_translator.parse_natural_language_to_drive_logic(
            natural_language, tasks, events
        )
        
        if not logic:
            raise HTTPException(status_code=400, detail="无法解析自然语言描述，请参考示例格式")
        
        return {
            "success": True,
            "logic": logic
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@router.post("/nl-rule-interface/explain-sensing-config")
def explain_sensing_config_in_natural_language(
    config: dict
):
    """将数据感知配置转换为自然语言描述"""
    try:
        explanation = llm_translator.convert_sensing_config_to_natural_language(config)
        return {
            "success": True,
            "explanation": explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")

@router.post("/nl-rule-interface/explain-drive-logic")
def explain_drive_logic_in_natural_language(
    logic: dict
):
    """将驱动逻辑配置转换为自然语言描述"""
    try:
        explanation = llm_translator.convert_drive_logic_to_natural_language(logic)
        return {
            "success": True,
            "explanation": explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")
```

## 3. 前端API服务 (frontend/src/services/nlRuleApi.js)

保持不变：

```javascript
import api from './api';

const nlRuleApi = {
  parseSensingConfig: (naturalLanguage) => {
    return api.post('/nl-rule-interface/parse-sensing-config', { natural_language: naturalLanguage });
  },
  
  parseDriveLogic: (naturalLanguage) => {
    return api.post('/nl-rule-interface/parse-drive-logic', { natural_language: naturalLanguage });
  },
  
  explainSensingConfig: (config) => {
    return api.post('/nl-rule-interface/explain-sensing-config', config);
  },
  
  explainDriveLogic: (logic) => {
    return api.post('/nl-rule-interface/explain-drive-logic', logic);
  }
};

export default nlRuleApi;
```

## 4. 数据感知配置页面集成 (DataSensing.jsx)

增强错误处理和用户提示：

```jsx
// 在组件顶部导入
import nlRuleApi from '../../services/nlRuleApi';

// 在组件内部添加状态
const [naturalLanguage, setNaturalLanguage] = useState('');

// 添加配置验证函数
const isValidSensingConfig = (config) => {
  if (!config.name || !config.type || !config.model_id || !config.config) {
    return false;
  }
  
  if (config.type === 'data_change') {
    return config.config.trigger_conditions && config.config.check_interval;
  } else if (config.type === 'threshold') {
    const hasStatic = config.config.threshold_type === 'static' && config.config.threshold_value !== undefined;
    const hasDynamic = config.config.threshold_type === 'dynamic' && config.config.threshold_field;
    return config.config.monitored_field && config.config.operator && config.config.check_interval && (hasStatic || hasDynamic);
  }
  
  return true;
};

// 添加自然语言处理函数
const handleNaturalLanguageChange = (value) => {
  setNaturalLanguage(value);
};

const handleParseNaturalLanguage = async () => {
  if (!naturalLanguage.trim()) {
    message.warning('请输入自然语言描述');
    return;
  }
  
  setLoading(true);
  try {
    const response = await nlRuleApi.parseSensingConfig(naturalLanguage);
    if (response.data.success && response.data.config) {
      const parsedConfig = response.data.config;
      
      // 验证配置是否完整
      if (!isValidSensingConfig(parsedConfig)) {
        message.error('解析结果不完整，请尝试更明确的描述');
        return;
      }
      
      // 设置表单字段
      const formValues = {
        name: parsedConfig.name || '',
        type: parsedConfig.type || 'data_change',
        model_id: parsedConfig.model_id || '',
        description: parsedConfig.description || '',
        status: true
      };
      
      // 根据类型设置配置字段
      if (parsedConfig.type === 'data_change') {
        formValues.trigger_conditions = parsedConfig.config?.trigger_conditions || [];
        formValues.monitored_fields = parsedConfig.config?.monitored_fields || [];
        formValues.check_interval = parsedConfig.config?.check_interval || 5;
      } else if (parsedConfig.type === 'threshold') {
        formValues.monitored_field = parsedConfig.config?.monitored_field || '';
        formValues.operator = parsedConfig.config?.operator || 'gt';
        formValues.threshold_value = parsedConfig.config?.threshold_value;
        formValues.check_interval = parsedConfig.config?.check_interval || 5;
        formValues.threshold_type = parsedConfig.config?.threshold_type || 'static';
      }
      
      form.setFieldsValue(formValues);
      setSelectedType(parsedConfig.type || 'data_change');
      
      // 如果有模型ID，获取字段信息
      if (parsedConfig.model_id) {
        const model = businessModels.find(m => m.id === parsedConfig.model_id);
        if (model && model.fields) {
          setModelFields(model.fields);
        }
      }
      
      message.success('自然语言解析成功');
    } else {
      message.error('解析失败，请参考以下示例：\n• 当温度超过100度时告警\n• 监控订单表的所有变更\n• 当库存低于50时通知');
    }
  } catch (error) {
    message.error('解析失败: ' + error.response?.data?.detail || error.message);
  } finally {
    setLoading(false);
  }
};

// 在表单中添加自然语言输入区域（在模态框的Form中）
// 添加在name字段之后
<Form.Item label="自然语言描述">
  <Input.TextArea 
    value={naturalLanguage}
    onChange={(e) => handleNaturalLanguageChange(e.target.value)}
    placeholder="例如：当温度超过100度时触发告警"
    rows={3}
  />
</Form.Item>
<Button 
  type="primary" 
  onClick={handleParseNaturalLanguage} 
  loading={loading}
  style={{ marginBottom: 16 }}
>
  解析为配置
</Button>
```

## 5. 驱动逻辑配置页面集成 (DriveLogic.jsx)

增强错误处理和用户提示：

```jsx
// 在组件顶部导入
import nlRuleApi from '../../services/nlRuleApi';

// 在组件内部添加状态
const [naturalLanguage, setNaturalLanguage] = useState('');

// 添加配置验证函数
const isValidDriveLogic = (logic) => {
  if (!logic.name || !logic.type || !logic.config || !logic.event_ids || !logic.task_ids) {
    return false;
  }
  
  if (logic.type === 'first_order') {
    // first_order类型可以没有pre_condition
    return Array.isArray(logic.event_ids) && Array.isArray(logic.task_ids);
  } else if (logic.type === 'script') {
    return logic.config.script_content && Array.isArray(logic.event_ids) && Array.isArray(logic.task_ids);
  }
  
  return true;
};

// 添加自然语言处理函数
const handleNaturalLanguageChange = (value) => {
  setNaturalLanguage(value);
};

const handleParseNaturalLanguage = async () => {
  if (!naturalLanguage.trim()) {
    message.warning('请输入自然语言描述');
    return;
  }
  
  setLoading(true);
  try {
    const response = await nlRuleApi.parseDriveLogic(naturalLanguage);
    if (response.data.success && response.data.logic) {
      const parsedLogic = response.data.logic;
      
      // 验证配置是否完整
      if (!isValidDriveLogic(parsedLogic)) {
        message.error('解析结果不完整，请尝试更明确的描述');
        return;
      }
      
      // 设置表单字段
      const formValues = {
        name: parsedLogic.name || '',
        type: parsedLogic.type || 'first_order',
        description: parsedLogic.description || '',
        event_ids: parsedLogic.event_ids || [],
        task_ids: parsedLogic.task_ids || []
      };
      
      // 根据类型设置配置字段
      if (parsedLogic.type === 'first_order') {
        formValues.pre_condition = parsedLogic.config?.pre_condition || '';
      } else if (parsedLogic.type === 'script') {
        formValues.script_content = parsedLogic.config?.script_content || '';
      }
      
      form.setFieldsValue(formValues);
      setSelectedType(parsedLogic.type || 'first_order');
      
      message.success('自然语言解析成功');
    } else {
      message.error('解析失败，请参考以下示例：\n• 如果订单金额大于10000，则需要经理审批\n• 当温度异常时发送邮件通知\n• 计算风险评分并根据结果分配不同处理流程');
    }
  } catch (error) {
    message.error('解析失败: ' + error.response?.data?.detail || error.message);
  } finally {
    setLoading(false);
  }
};

// 在表单中添加自然语言输入区域（在模态框的Form中）
// 添加在description字段之后
<Form.Item label="自然语言描述">
  <Input.TextArea 
    value={naturalLanguage}
    onChange={(e) => handleNaturalLanguageChange(e.target.value)}
    placeholder="例如：如果订单金额大于10000，则需要经理审批"
    rows={3}
  />
</Form.Item>
<Button 
  type="primary" 
  onClick={handleParseNaturalLanguage} 
  loading={loading}
  style={{ marginBottom: 16 }}
>
  解析为逻辑
</Button>
```

## 6. 路由注册 (app/main.py)

在现有的路由导入中添加：

```python
# 导入部分
from app.api import example, data_source, business_model, data_sensing, drive_logic, agent, test_data, drive_log, test_execution, nl_rule_interface

# 路由注册部分
app.include_router(nl_rule_interface.router, prefix="/api/v1", tags=["Natural Language Rule Interface"])
```

## 7. 使用说明

### 7.1 主要改进点
1. **少样本提示词**: 提供具体的输入输出示例，显著提高解析准确性
2. **配置验证**: 在后端和前端都添加了严格的配置验证机制
3. **错误处理**: 提供更友好的错误提示和使用示例
4. **可靠性提升**: 通过验证机制确保生成的配置能够被系统正确解析

### 7.2 测试用例
- **数据感知配置**: 
  - "当温度超过100度时告警" → 阈值触发配置
  - "监控订单表的所有变更" → 数据变化感知配置
  - "当库存低于50时通知" → 阈值触发配置

- **驱动逻辑配置**:
  - "如果订单金额大于10000，则需要经理审批" → 一阶函数配置
  - "当温度异常时发送邮件通知" → 一阶函数配置  
  - "计算风险评分并根据结果分配不同处理流程" → 脚本函数配置

### 7.3 实施建议
1. **先测试少样本效果**: 使用提供的示例测试解析准确性
2. **收集用户反馈**: 记录解析失败的案例，持续优化提示词
3. **逐步扩展示例**: 根据实际业务场景添加更多少样本示例
4. **监控日志**: 关注配置验证失败的日志，及时发现问题

这些增强后的代码样例可以直接复制使用，显著提高了自然语言解析的可靠性和用户体验。