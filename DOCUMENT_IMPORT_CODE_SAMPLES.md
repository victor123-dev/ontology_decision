# 文档导入功能代码样例

## 1. 文档解析服务 (app/services/document_parser.py)

```python
import os
from typing import Union
from PyPDF2 import PdfReader
from docx import Document

class DocumentParser:
    """文档解析服务"""
    
    def parse(self, file_path: str) -> str:
        """解析文档并返回文本内容"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self._parse_pdf(file_path)
        elif file_extension == '.docx':
            return self._parse_docx(file_path)
        elif file_extension == '.txt':
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_extension}")
    
    def _parse_pdf(self, file_path: str) -> str:
        """解析PDF文件"""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    
    def _parse_docx(self, file_path: str) -> str:
        """解析Word文档"""
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    
    def _parse_txt(self, file_path: str) -> str:
        """解析文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
```

## 2. 扩展LLMTranslator类 (app/utils/llm_translator.py)

在现有 `LLMTranslator` 类中添加以下方法：

```python
import re
import json
from app.utils.logger import get_logger

logger = get_logger(__name__)

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
- config: 配置参数（对于阈值触发，包含field, operator, threshold）
- description: 配置描述

只返回JSON数组，不要包含任何其他文本。
"""

def _generate_drive_logic_prompt(self, document_content: str, sensing_configs: List[Dict], tasks: List[Dict]) -> str:
    """生成驱动逻辑的提示词"""
    configs_info = "\n".join([
        f"- 配置ID: {config['id']}, 名称: {config['name']}, 类型: {config['type']}"
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
- config: 逻辑配置参数
- description: 逻辑描述
- event_ids: 关联的数据感知配置ID列表
- task_ids: 关联的任务ID列表

只返回JSON数组，不要包含任何其他文本。
"""

def extract_sensing_configs_from_document(self, document_content: str, business_models: List[Dict]) -> List[Dict]:
    """从文档内容中提取数据感知配置"""
    prompt = self._generate_sensing_config_prompt(document_content, business_models)
    response = self.llm_client.chat.completions.create(
        model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
        messages=[
            {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够从文档中提取结构化配置"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
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
        model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
        messages=[
            {"role": "system", "content": "你是一个专业的数据驱动系统配置专家，能够从文档中提取结构化配置"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
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
```

## 3. 后端API接口 (app/api/document_import.py)

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.utils.llm_translator import llm_translator
from app.models.business_model import BusinessModel
from app.models.data_sensing import DataSensingConfig
from app.models.drive_logic import DriveLogic, Task
from app.services.document_parser import DocumentParser

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

@router.post("/document-import/parse")
async def parse_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """解析文档内容，返回原始文本"""
    if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="不支持的文件格式，仅支持PDF、DOCX、TXT")
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # 解析文档
        parser = DocumentParser()
        document_content = parser.parse(temp_file_path)
        
        return {
            "success": True,
            "content": document_content,
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.post("/document-import/generate-configs")
def generate_configs_from_document(
    document_content: str = Form(...),
    db: Session = Depends(get_db)
):
    """基于文档内容生成配置预览"""
    try:
        # 获取所有业务模型
        business_models = []
        models = db.query(BusinessModel).all()
        for model in models:
            db.refresh(model)  # 确保加载字段
            business_models.append({
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "fields": [{"field_id": f.field_id, "name": f.name} for f in model.fields] if model.fields else []
            })
        
        # 获取所有任务
        tasks = []
        task_list = db.query(Task).all()
        for task in task_list:
            db.refresh(task)  # 确保加载能力
            tasks.append({
                "id": task.id,
                "name": task.name,
                "capability_ids": [cap.id for cap in task.capabilities] if task.capabilities else []
            })
        
        # 提取数据感知配置
        sensing_configs = llm_translator.extract_sensing_configs_from_document(
            document_content, business_models
        )
        
        # 提取驱动逻辑配置（需要先有感知配置）
        drive_logics = llm_translator.extract_drive_logics_from_document(
            document_content, sensing_configs, tasks
        )
        
        return {
            "success": True,
            "sensing_configs": sensing_configs,
            "drive_logics": drive_logics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置生成失败: {str(e)}")

@router.post("/document-import/apply-configs")
def apply_configs_from_document(
    sensing_configs: List[dict] = Form(...),
    drive_logics: List[dict] = Form(...),
    db: Session = Depends(get_db)
):
    """应用生成的配置到系统中"""
    try:
        # 创建数据感知配置
        created_sensing_configs = []
        for config_data in sensing_configs:
            db_config = DataSensingConfig(
                name=config_data.get("name"),
                type=config_data.get("type"),
                model_id=config_data.get("model_id"),
                config=config_data.get("config", {}),
                description=config_data.get("description"),
                status=True
            )
            db.add(db_config)
            db.commit()
            db.refresh(db_config)
            created_sensing_configs.append(db_config)
        
        # 创建驱动逻辑配置
        created_drive_logics = []
        for logic_data in drive_logics:
            db_logic = DriveLogic(
                name=logic_data.get("name"),
                type=logic_data.get("type"),
                config=logic_data.get("config", {}),
                description=logic_data.get("description")
            )
            db.add(db_logic)
            db.commit()
            db.refresh(db_logic)
            
            # 关联事件
            event_ids = logic_data.get("event_ids", [])
            if event_ids:
                events = db.query(DataSensingConfig).filter(DataSensingConfig.id.in_(event_ids)).all()
                db_logic.events = events
            
            # 关联任务
            task_ids = logic_data.get("task_ids", [])
            if task_ids:
                tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
                db_logic.tasks = tasks
            
            db.commit()
            db.refresh(db_logic)
            created_drive_logics.append(db_logic)
        
        return {
            "success": True,
            "message": f"成功创建 {len(created_sensing_configs)} 个数据感知配置和 {len(created_drive_logics)} 个驱动逻辑"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"配置应用失败: {str(e)}")
```

## 4. 前端组件 (frontend/src/components/DocumentImport/DocumentImport.jsx)

```jsx
import React, { useState } from 'react';
import { Card, Upload, Button, message, Spin, Steps, Modal, List, Typography } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Dragger } = Upload;
const { Step } = Steps;
const { Text } = Typography;

const DocumentImport = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [documentContent, setDocumentContent] = useState('');
  const [fileName, setFileName] = useState('');
  const [configs, setConfigs] = useState({ sensing_configs: [], drive_logics: [] });
  const [loading, setLoading] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);

  const handleFileUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      const response = await api.post('/document-import/parse', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setDocumentContent(response.data.content);
      setFileName(response.data.filename);
      setCurrentStep(1);
      message.success('文档解析成功');
    } catch (error) {
      message.error('文档解析失败: ' + error.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateConfigs = async () => {
    const formData = new FormData();
    formData.append('document_content', documentContent);

    setLoading(true);
    try {
      const response = await api.post('/document-import/generate-configs', formData);
      setConfigs(response.data);
      setCurrentStep(2);
      message.success('配置生成成功');
    } catch (error) {
      message.error('配置生成失败: ' + error.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyConfigs = async () => {
    const formData = new FormData();
    formData.append('sensing_configs', JSON.stringify(configs.sensing_configs));
    formData.append('drive_logics', JSON.stringify(configs.drive_logics));

    setLoading(true);
    try {
      await api.post('/document-import/apply-configs', formData);
      message.success('配置应用成功');
      setCurrentStep(0);
      setDocumentContent('');
      setFileName('');
      setConfigs({ sensing_configs: [], drive_logics: [] });
    } catch (error) {
      message.error('配置应用失败: ' + error.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  };

  const showPreview = () => {
    setPreviewVisible(true);
  };

  const steps = [
    {
      title: '上传文档',
      content: (
        <div>
          <Dragger 
            beforeUpload={(file) => {
              handleFileUpload(file);
              return false; // 阻止自动上传
            }}
            accept=".pdf,.docx,.txt"
            showUploadList={false}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">支持PDF、Word、TXT格式</p>
          </Dragger>
          {fileName && (
            <div style={{ marginTop: 16 }}>
              <Text strong>已选择文件:</Text> {fileName}
            </div>
          )}
        </div>
      )
    },
    {
      title: '生成配置',
      content: (
        <div>
          <Button type="primary" onClick={handleGenerateConfigs} loading={loading}>
            生成配置
          </Button>
          <Button style={{ marginLeft: 8 }} onClick={() => setCurrentStep(0)}>
            返回重新上传
          </Button>
          {documentContent && (
            <Button style={{ marginLeft: 8 }} onClick={showPreview}>
              预览文档内容
            </Button>
          )}
        </div>
      )
    },
    {
      title: '确认应用',
      content: (
        <div>
          <h4>数据感知配置 ({configs.sensing_configs.length} 个)</h4>
          <List
            dataSource={configs.sensing_configs}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={item.name}
                  description={`${item.type} - ${item.model_id}`}
                />
              </List.Item>
            )}
          />
          
          <h4>驱动逻辑配置 ({configs.drive_logics.length} 个)</h4>
          <List
            dataSource={configs.drive_logics}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={item.name}
                  description={`${item.type} - 关联事件: ${item.event_ids?.length || 0}, 关联任务: ${item.task_ids?.length || 0}`}
                />
              </List.Item>
            )}
          />
          
          <div style={{ marginTop: 16 }}>
            <Button type="primary" onClick={handleApplyConfigs} loading={loading}>
              应用配置
            </Button>
            <Button style={{ marginLeft: 8 }} onClick={() => setCurrentStep(1)}>
              返回重新生成
            </Button>
          </div>
        </div>
      )
    }
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2>文档导入规则配置</h2>
        <p>通过上传业务文档，系统将自动解析并生成数据感知配置和驱动逻辑规则</p>
      </div>
      
      <Card>
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          {steps.map((step) => (
            <Step key={step.title} title={step.title} />
          ))}
        </Steps>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
          </div>
        ) : (
          steps[currentStep].content
        )}
      </Card>
      
      <Modal
        title={`文档内容预览 - ${fileName}`}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        <div style={{ maxHeight: '60vh', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
          {documentContent}
        </div>
      </Modal>
    </div>
  );
};

export default DocumentImport;
```

## 5. 依赖更新 (requirements.txt)

```txt
# 在现有依赖基础上添加
PyPDF2==3.0.1
python-docx==0.8.11
```

## 6. 路由注册 (app/main.py)

在现有的路由导入中添加：

```python
# 导入部分
from app.api import example, data_source, business_model, data_sensing, drive_logic, agent, test_data, drive_log, test_execution, document_import

# 路由注册部分
app.include_router(document_import.router, prefix="/api/v1", tags=["Document Import"])
```

## 7. 前端路由集成 (frontend/src/App.jsx)

```jsx
// 导入组件
import DocumentImport from './components/DocumentImport/DocumentImport';

// 路由配置
<Route path="/document-import" element={<DocumentImport />} />

// 菜单配置
{
  key: 'document-import',
  label: '文档导入',
  icon: <FileTextOutlined />
}
```

## 使用说明

1. **后端开发**: 按照文件路径创建对应的Python文件，确保导入路径正确
2. **前端开发**: 创建对应的React组件文件，确保API调用路径正确
3. **依赖安装**: 运行 `pip install PyPDF2 python-docx` 安装文档解析依赖
4. **测试验证**: 上传测试文档，验证整个流程是否正常工作

这些代码样例可以直接复制使用，只需要根据实际的项目结构调整导入路径和配置即可。