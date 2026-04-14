# 数据驱动项目系统设计文档

## 一、系统架构

### 1. 技术栈

- **后端**: Python 3.12, FastAPI, SQLAlchemy, SQLite
- **前端**: React 18, Ant Design, React Router, Axios
- **依赖**: SQLAlchemy (ORM), FastAPI (Web框架), Ant Design (UI组件库)

### 2. 系统架构图

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    前端应用     │────▶│    后端API      │────▶│  数据感知引擎   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         ▲                        │                        │
         │                        ▼                        ▼
         │                 ┌─────────────────┐     ┌─────────────────┐
         └─────────────────│    数据库      │◀────│  数据驱动引擎   │
                           └─────────────────┘     └─────────────────┘
```

## 二、核心功能模块

### 1. 数据源绑定及业务模型配置

- **功能**: 支持SQLite数据源绑定，自动识别表结构，生成业务模型
- **API**: `/api/v1/data-sources`, `/api/v1/business-models`
- **实现**: 使用SQLAlchemy的inspect功能自动识别表结构，集成Azure LLM生成中文名称和说明

### 2. 数据感知配置

- **功能**: 支持数据变化感知和阈值触发感知
- **API**: `/api/v1/data-sensing-configs`
- **实现**: 基于配置的事件触发机制，支持实时监控

### 3. 驱动逻辑配置

- **功能**: 支持一阶函数和脚本函数，实现多对多关系
- **API**: `/api/v1/drive-logics`, `/api/v1/tasks`
- **实现**: 基于事件的驱动逻辑执行，支持复杂的业务规则

### 4. Agent注册

- **功能**: Agent管理和能力清单定义
- **API**: `/api/v1/agents`, `/api/v1/capabilities`
- **实现**: 基于能力匹配的任务分发机制

### 5. 数据感知引擎

- **功能**: 实时数据监听和事件触发
- **实现**: 基于线程的异步监控，支持多种感知类型

### 6. 数据驱动引擎

- **功能**: 事件处理和任务分发
- **实现**: 基于事件队列的处理机制，支持任务优先级

## 三、数据库设计

### 1. 核心表结构

- **data_sources**: 数据源信息
- **business_models**: 业务模型
- **business_model_fields**: 业务模型字段
- **data_sensing_configs**: 数据感知配置
- **drive_logics**: 驱动逻辑
- **tasks**: 任务
- **agents**: Agent信息
- **capabilities**: 能力清单
- **drive_logs**: 驱动日志

### 2. 关系图

- 数据源与业务模型：一对多
- 业务模型与字段：一对多
- 数据感知配置与驱动逻辑：多对多
- 驱动逻辑与任务：多对多
- Agent与能力：多对多

## 四、API接口

### 1. 数据源管理

- `POST /api/v1/data-sources` - 创建数据源
- `GET /api/v1/data-sources` - 获取所有数据源
- `GET /api/v1/data-sources/{id}` - 获取单个数据源
- `PUT /api/v1/data-sources/{id}` - 更新数据源
- `DELETE /api/v1/data-sources/{id}` - 删除数据源
- `POST /api/v1/data-sources/{id}/test-connection` - 测试连接
- `GET /api/v1/data-sources/{id}/tables` - 获取表列表

### 2. 业务模型管理

- `POST /api/v1/business-models` - 创建业务模型
- `GET /api/v1/business-models` - 获取所有业务模型
- `GET /api/v1/business-models/{id}` - 获取单个业务模型
- `PUT /api/v1/business-models/{id}` - 更新业务模型
- `DELETE /api/v1/business-models/{id}` - 删除业务模型
- `POST /api/v1/business-models/import` - 导入业务模型

### 3. 数据感知配置

- `POST /api/v1/data-sensing-configs` - 创建数据感知配置
- `GET /api/v1/data-sensing-configs` - 获取所有数据感知配置
- `GET /api/v1/data-sensing-configs/{id}` - 获取单个数据感知配置
- `PUT /api/v1/data-sensing-configs/{id}` - 更新数据感知配置
- `DELETE /api/v1/data-sensing-configs/{id}` - 删除数据感知配置

### 4. 驱动逻辑配置

- `POST /api/v1/drive-logics` - 创建驱动逻辑
- `GET /api/v1/drive-logics` - 获取所有驱动逻辑
- `GET /api/v1/drive-logics/{id}` - 获取单个驱动逻辑
- `PUT /api/v1/drive-logics/{id}` - 更新驱动逻辑
- `DELETE /api/v1/drive-logics/{id}` - 删除驱动逻辑
- `POST /api/v1/tasks` - 创建任务
- `GET /api/v1/tasks` - 获取所有任务

### 5. Agent管理

- `POST /api/v1/agents` - 创建Agent
- `GET /api/v1/agents` - 获取所有Agent
- `GET /api/v1/agents/{id}` - 获取单个Agent
- `PUT /api/v1/agents/{id}` - 更新Agent
- `DELETE /api/v1/agents/{id}` - 删除Agent
- `POST /api/v1/capabilities` - 创建能力
- `GET /api/v1/capabilities` - 获取所有能力
- `POST /api/v1/agents/{id}/capabilities/{capability_id}` - 分配能力

### 6. 测试数据管理

- `GET /api/v1/test-data/{data_source_id}/{table_name}` - 获取测试数据
- `POST /api/v1/test-data/{data_source_id}/{table_name}` - 添加测试数据

### 7. 驱动日志管理

- `POST /api/v1/drive-logs` - 创建驱动日志
- `GET /api/v1/drive-logs` - 获取驱动日志
- `GET /api/v1/drive-logs/{id}` - 获取单个驱动日志

### 8. 测试执行

- `POST /api/v1/test-execution/simulate-event` - 模拟事件

## 五、系统流程

### 1. 数据源绑定流程

1. 用户添加数据源配置
2. 系统测试连接
3. 用户选择表进行模型导入
4. 系统自动识别表结构并生成业务模型
5. LLM生成中文名称和说明

### 2. 数据感知流程

1. 用户配置数据感知规则
2. 数据感知引擎实时监控数据变化
3. 当触发条件满足时，生成事件
4. 事件传递给数据驱动引擎

### 3. 驱动逻辑执行流程

1. 数据驱动引擎接收事件
2. 匹配关联的驱动逻辑
3. 执行驱动逻辑判断
4. 生成并分发任务
5. Agent执行任务

## 六、系统配置

### 1. 后端配置

- 端口: 8080
- 数据库: SQLite (data.db)
- 日志: 控制台输出

### 2. 前端配置

- 端口: 3030
- API基础URL: http://localhost:8080/api/v1
- 路由: React Router

## 七、部署说明

### 1. 后端部署

1. 安装依赖: 
```bash
pip install -r requirements.txt
```
2. 启动服务: 
```bash
# 开发模式启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 生产模式启动（建议使用gunicorn）
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8080
```

### 2. 前端部署

1. 安装依赖: 
```bash
cd frontend
npm install
```
2. 启动开发服务: 
```bash
npm run dev
```
3. 构建生产版本: `npm run build`

## 八、扩展说明

### 1. 数据源扩展

- 支持添加MySQL、PostgreSQL等其他数据库类型
- 需要在DBClient类中实现对应数据库的连接和操作方法

### 2. 感知类型扩展

- 支持添加时间触发、复杂事件处理等感知类型
- 需要在数据感知引擎中添加相应的监控逻辑

### 3. 驱动逻辑扩展

- 支持添加更复杂的逻辑类型
- 需要在驱动逻辑执行器中添加相应的执行逻辑

### 4. Agent能力扩展

- 支持添加更多Agent类型和能力
- 需要在Agent管理模块中添加相应的能力定义
