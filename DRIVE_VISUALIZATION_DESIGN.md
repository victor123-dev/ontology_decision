# 驱动全景可视化功能设计文档

## 1. 需求分析

根据系统架构，驱动全景需要展示完整的数据驱动链路：

```
数据源 → 业务模型 → 数据感知配置 → 驱动逻辑 → 任务 → Agent/能力
```

每个环节的关系：
- **数据源 ↔ 业务模型**: 一对多关系
- **业务模型 ↔ 数据感知配置**: 一对多关系  
- **数据感知配置 ↔ 驱动逻辑**: 多对多关系
- **驱动逻辑 ↔ 任务**: 多对多关系
- **任务 ↔ 能力**: 多对多关系
- **Agent ↔ 能力**: 多对多关系

## 2. 后端API设计

### 2.1 新增API路由文件

创建 `app/api/drive_visualization.py`，提供两个主要接口：

- `GET /drive-visualization/full-graph`: 获取完整的驱动全景图数据
- `GET /drive-visualization/model/{model_id}`: 获取指定业务模型的驱动链路图

### 2.2 数据结构

返回的数据包含两个主要部分：

**Nodes (节点)**:
- id: 唯一标识符 (格式: type_id)
- type: 节点类型 (data_source, business_model, sensing_config, drive_logic, task, capability, agent)
- name: 显示名称
- description: 描述信息
- data: 详细数据对象

**Edges (边)**:
- source: 源节点ID
- target: 目标节点ID  
- type: 关系类型

### 2.3 主路由集成

在 `app/main.py` 中注册新的API路由。

## 3. 前端可视化组件设计

### 3.1 组件结构

- `DriveVisualization.jsx`: 主组件，包含视图控制和数据获取
- `GraphVisualization.jsx`: 图形渲染组件，使用D3.js实现

### 3.2 功能特性

**视图模式**:
- 完整全景图：展示系统中所有驱动链路
- 按模型查看：聚焦特定业务模型的驱动链路

**交互功能**:
- 节点拖拽：手动调整节点位置
- 缩放平移：图形的缩放和平移操作
- 节点点击：跳转到对应的管理页面

**视觉设计**:
- 不同类型节点使用不同颜色区分
- 节点显示名称和关键信息
- 连线清晰展示关系方向

### 3.3 技术选型

- **图形库**: D3.js (力导向布局)
- **UI框架**: Ant Design
- **路由**: React Router

## 4. 文件结构

```
frontend/
└── src/
    └── components/
        └── DriveVisualization/
            ├── DriveVisualization.jsx
            └── GraphVisualization.jsx

app/
└── api/
    └── drive_visualization.py
```

## 5. 实施步骤

### 5.1 后端开发
1. 创建 `app/api/drive_visualization.py`
2. 实现两个API接口
3. 在 `app/main.py` 中注册路由

### 5.2 前端开发
1. 创建 `frontend/src/components/DriveVisualization/` 目录
2. 实现 `DriveVisualization.jsx` 和 `GraphVisualization.jsx`
3. 更新 `App.jsx` 添加路由和菜单项

### 5.3 测试验证
1. 验证API返回数据格式正确
2. 测试图形渲染功能
3. 验证交互功能正常工作

## 6. 扩展考虑

- **性能优化**: 对于大型系统，可考虑分页加载或懒加载
- **导出功能**: 支持将图形导出为图片或PDF
- **搜索过滤**: 支持按名称或类型搜索节点
- **历史版本**: 支持查看不同时间点的驱动配置状态