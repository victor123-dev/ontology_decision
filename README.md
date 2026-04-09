# Python 项目模板

这是一个通用的 Python 项目模板，提供了完整的项目架构、日志系统、配置管理等基础设施，方便快速启动新的 Python 项目。

## 📋 功能特性

### 🏗️ 项目架构
- 模块化设计，清晰的目录结构
- 支持环境变量配置，可选服务自动初始化
- 统一的日志管理
- 请求上下文和日志中间件

### 🔧 基础设施
- FastAPI 框架，支持自动 API 文档
- 数据库客户端工具（Neo4j、Milvus）
- JSON 工具类
- 嵌入模型工具
- 大语言模型客户端
- 基础前端框架（React）

### 📦 开发工具
- 支持热重载
- 完善的错误处理
- CORS 中间件配置
- 可选服务自动检测和初始化

## 🛠️ 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 最新 |
| 配置管理 | Pydantic Settings | 最新 |
| 日志系统 | Python logging | 最新 |
| 数据库 | Neo4j (可选) | 5.x |
| 向量数据库 | Milvus (可选) | 最新 |
| 语言模型 | OpenAI (可选) | 最新 |
| 前端框架 | React | 最新 |
| 前端构建工具 | Vite | 最新 |

## 📁 项目结构

```
PyProjectTemplate/
├── app/                  # 主应用目录
│   ├── agents/           # Agent 相关代码（可扩展）
│   │   ├── __init__.py
│   │   └── base_agent.py     # 基础 Agent 类
│   ├── api/              # API 路由（可扩展）
│   │   ├── __init__.py
│   │   └── example.py        # 示例 API 路由
│   ├── middleware_config/ # 中间件配置
│   │   └── middleware.py      # 自定义中间件
│   ├── models/           # 数据模型（可扩展）
│   │   └── example.py        # 示例数据模型
│   ├── ontology/         # 本体管理（可扩展）
│   ├── utils/            # 工具函数
│   │   ├── __init__.py
│   │   ├── embedding.py       # 嵌入模型工具
│   │   ├── json_utils.py      # JSON 工具类
│   │   ├── llm_client.py      # LLM 客户端
│   │   ├── logger.py          # 日志工具
│   │   ├── milvus_client.py   # Milvus 客户端
│   │   └── neo4j_client.py    # Neo4j 客户端
│   ├── config.py         # 配置文件
│   ├── context_vars.py   # 上下文变量
│   └── main.py           # 应用入口
├── frontend/             # 前端应用
│   ├── public/            # 静态资源
│   ├── src/               # 前端源码
│   │   ├── App.css         # 应用样式
│   │   ├── App.jsx         # 应用组件
│   │   └── main.jsx        # 应用入口
│   ├── index.html         # HTML 模板
│   ├── package.json       # 前端依赖
│   └── vite.config.js     # Vite 配置
├── tests/                # 测试用例
│   ├── __init__.py
│   └── test_example.py     # 示例测试
├── .env.example          # 环境变量示例
├── .gitignore            # Git 忽略文件
├── requirements.txt      # Python 依赖
└── README.md             # 项目说明
```

## 🚀 快速开始

### 前提条件

- Python 3.12+
- Node.js 16+（用于前端开发）

### 安装与配置

1. **克隆仓库**

```bash
git clone <repository-url>
cd PyProjcetTemplate
```

2. **配置环境变量**

在项目根目录创建 `.env` 文件：

```env
# FastAPI配置
APP_NAME=Python Project Template
APP_VERSION=1.0.0
DEBUG=True
PORT=8080

# 可选配置（取消注释以启用相应服务）
# Neo4j配置
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=your-password
# NEO4J_DATA_DATABASE=neo4j

# Azure OpenAI配置
# AZURE_OPENAI_ENDPOINT=https://your-openai-endpoint.openai.azure.com/
# AZURE_OPENAI_API_KEY=your-api-key
# AZURE_OPENAI_API_VERSION=2024-12-01-preview
# AZURE_OPENAI_GPT_DEPLOYMENT=gpt-4.1-mini
# AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT=gpt-4.1
# AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-small

# Milvus配置
# MILVUS_URL=https://your-milvus-endpoint
# MILVUS_USER=your-username
# MILVUS_PASSWORD=your-password
```

3. **安装后端依赖**

```bash
pip install -r requirements.txt
```

4. **安装前端依赖** (可选)

```bash
cd frontend
npm install
```

### 运行服务

**后端服务**

```bash
# 启动后端服务
uvicorn app.main:app --host 0.0.0.0 --reload --port 8080 --reload-dir ./app/ --reload-dir ./tests/
```

**前端服务** (可选)

```bash
cd frontend
npm run dev
```

服务将在以下地址可用：
- 后端API: `http://localhost:8080`
- Swagger文档: `http://localhost:8080/docs`
- 前端界面: `http://localhost:5173` (如果运行了前端)

## 📖 使用指南

### 1. 添加新的 API 路由

在 `app/api/` 目录下创建新的路由文件，然后在 `app/main.py` 中包含该路由。

### 2. 添加新的模型

在 `app/models/` 目录下创建新的数据模型。

### 3. 配置可选服务

根据需要在 `.env` 文件中取消注释相应的配置，系统会自动检测并初始化对应的服务。

### 4. 使用数据库客户端

```python
from app.utils.neo4j_client import neo4j_client

if neo4j_client:
    # 使用neo4j_client执行查询
    result = neo4j_client.execute_query("MATCH (n) RETURN n LIMIT 5")
    print(result)
else:
    print("Neo4j客户端未初始化，请检查配置")
```

### 5. 使用 LLM 客户端

```python
from app.utils.llm_client import llm_client

if llm_client:
    # 使用llm_client调用大语言模型
    response = llm_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "Hello, world!"}]
    )
    print(response.choices[0].message.content)
else:
    print("LLM客户端未初始化，请检查配置")
```

### 6. 使用嵌入服务

```python
from app.utils.embedding import embedding_service

if embedding_service:
    # 使用embedding_service获取文本嵌入
    embedding = embedding_service.get_embedding("Hello, world!")
    print(embedding)
else:
    print("嵌入服务未初始化，请检查配置")
```

### 7. 使用 Milvus 客户端

```python
from app.utils.milvus_client import milvus_client

if milvus_client:
    # 使用milvus_client操作向量数据库
    collection = milvus_client.get_collection("my_collection")
    print(collection)
else:
    print("Milvus客户端未初始化，请检查配置")
```

## 🧪 测试

运行测试套件：

```bash
python -m unittest discover tests
```

## 📝 扩展建议

1. **添加数据库迁移工具**：如 Alembic
2. **添加认证系统**：如 JWT
3. **添加缓存系统**：如 Redis
4. **添加 CI/CD 配置**：如 GitHub Actions
5. **添加容器化配置**：如 Dockerfile
6. **添加更多 API 路由和业务逻辑**
7. **扩展前端功能**

## 📄 许可证

本项目采用 MIT 许可证。