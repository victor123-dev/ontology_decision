# 文档导入规则配置功能设计文档

## 1. 功能概述

文档导入功能允许用户上传业务文档（PDF、Word、TXT等格式），系统通过大语言模型自动解析文档内容，提取业务规则，并生成相应的数据感知配置和驱动逻辑配置。

### 核心价值
- **降低配置门槛**: 业务人员可以通过自然语言文档描述需求，无需技术背景
- **提高配置效率**: 自动化生成配置，减少手动配置工作量
- **保证配置一致性**: 基于统一的文档标准生成配置，避免人为错误

## 2. 系统架构

### 2.1 整体流程
```
用户上传文档 → 文档解析服务 → LLM内容理解 → 规则提取 → 配置预览 → 应用配置
```

### 2.2 组件关系
- **前端**: DocumentImport组件（三步向导式界面）
- **后端API**: document_import.py（三个核心接口）
- **服务层**: DocumentParser（文档解析）、LLMTranslator扩展（规则生成）
- **数据层**: 复用现有的数据感知配置和驱动逻辑数据模型

## 3. 详细设计

### 3.1 文档解析服务 (app/services/document_parser.py)

**支持格式**:
- PDF: 使用PyPDF2库
- Word (.docx): 使用python-docx库  
- TXT: 直接读取文本

**接口设计**:
```python
class DocumentParser:
    def parse(self, file_path: str) -> str:
        """解析文档并返回纯文本内容"""
```

### 3.2 LLM规则生成逻辑

**扩展LLMTranslator类**，添加两个核心方法：

1. **extract_sensing_configs_from_document()**: 
   - 输入: 文档内容 + 可用业务模型列表
   - 输出: 数据感知配置列表
   - 提示词策略: 结合业务模型上下文，提取监控需求

2. **extract_drive_logics_from_document()**:
   - 输入: 文档内容 + 数据感知配置 + 可用任务列表  
   - 输出: 驱动逻辑配置列表
   - 提示词策略: 结合事件和任务上下文，提取业务规则

**提示词设计原则**:
- 明确角色定义: "专业的数据驱动系统配置专家"
- 提供上下文信息: 可用的业务模型、任务等
- 指定输出格式: 严格的JSON格式，便于解析
- 包含字段说明: 详细说明每个配置字段的含义

### 3.3 后端API接口 (app/api/document_import.py)

**三个核心接口**:

1. **POST /document-import/parse**
   - 功能: 解析上传的文档，返回原始文本
   - 参数: file (multipart/form-data)
   - 返回: {success: bool, content: str, filename: str}

2. **POST /document-import/generate-configs**  
   - 功能: 基于文档内容生成配置预览
   - 参数: document_content (form data)
   - 返回: {success: bool, sensing_configs: [], drive_logics: []}

3. **POST /document-import/apply-configs**
   - 功能: 将生成的配置应用到系统中
   - 参数: sensing_configs[], drive_logics[] (form data)
   - 返回: {success: bool, message: str}

### 3.4 前端组件 (frontend/src/components/DocumentImport/)

**三步向导式界面**:

**步骤1: 上传文档**
- 拖拽上传区域，支持PDF/DOCX/TXT
- 文件类型验证
- 上传后显示文件名

**步骤2: 生成配置**  
- 调用LLM生成配置
- 提供文档内容预览功能
- 支持重新上传

**步骤3: 确认应用**
- 列表展示生成的数据感知配置和驱动逻辑
- 显示配置详情（名称、类型、关联关系等）
- 确认应用或返回重新生成

## 4. 依赖管理

### 4.1 Python依赖
在 `requirements.txt` 中添加:
```txt
PyPDF2==3.0.1
python-docx==0.8.11
```

### 4.2 系统集成
- **路由注册**: 在 `app/main.py` 中添加 `document_import` 路由
- **菜单集成**: 在前端导航菜单中添加"文档导入"选项
- **权限控制**: 复用现有的API权限机制

## 5. 实施步骤

### 5.1 后端开发顺序
1. 创建 `app/services/document_parser.py`
2. 扩展 `app/utils/llm_translator.py` 添加规则生成方法
3. 创建 `app/api/document_import.py`  
4. 更新 `requirements.txt` 添加依赖
5. 在 `app/main.py` 中注册新路由

### 5.2 前端开发顺序
1. 创建 `frontend/src/components/DocumentImport/` 目录
2. 实现 `DocumentImport.jsx` 组件
3. 更新 `App.jsx` 添加路由和菜单项
4. 测试文件上传和API调用

### 5.3 测试验证
1. **单元测试**: 文档解析服务、LLM提示词生成
2. **集成测试**: 完整的文档导入流程
3. **边界测试**: 不支持的文件格式、大文件处理、LLM解析失败等情况

## 6. 错误处理与容错

### 6.1 文档解析错误
- 不支持的文件格式: 返回明确的错误信息
- 文件损坏: 捕获异常并提示用户重新上传
- 大文件处理: 设置文件大小限制（建议10MB）

### 6.2 LLM解析错误  
- JSON格式错误: 正则表达式提取JSON内容
- 内容为空: 返回空配置列表，允许用户手动调整
- API调用失败: 重试机制 + 用户友好的错误提示

### 6.3 配置应用错误
- 数据库约束冲突: 事务回滚，保持数据一致性
- 关联对象不存在: 验证配置中的ID有效性

## 7. 扩展考虑

### 7.1 性能优化
- **异步处理**: 对于大文档，可考虑异步处理模式
- **缓存机制**: 缓存文档解析结果，避免重复解析
- **批量处理**: 支持批量文档导入

### 7.2 功能增强
- **模板支持**: 提供文档模板，指导用户编写规范的业务文档
- **配置编辑**: 在预览阶段允许用户手动调整生成的配置
- **历史记录**: 保存文档导入历史，支持版本对比
- **多语言支持**: 支持不同语言的文档解析

### 7.3 安全考虑
- **文件类型白名单**: 严格限制支持的文件类型
- **内容安全检查**: 防止恶意内容注入
- **访问控制**: 确保只有授权用户可以使用此功能