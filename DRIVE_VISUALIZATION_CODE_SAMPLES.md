# 驱动全景可视化功能代码样例

## 1. 后端API接口 (app/api/drive_visualization.py)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.utils.db_client import Base, create_engine, sessionmaker
from app.config import settings
from app.models.data_source import DataSource
from app.models.business_model import BusinessModel, BusinessModelField
from app.models.data_sensing import DataSensingConfig
from app.models.drive_logic import DriveLogic, Task
from app.models.agent import Agent, Capability

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

@router.get("/drive-visualization/full-graph")
def get_full_drive_graph(db: Session = Depends(get_db)):
    """获取完整的驱动全景图数据"""
    # 获取所有数据源
    data_sources = db.query(DataSource).all()
    
    # 获取所有业务模型（包含字段）
    business_models = db.query(BusinessModel).all()
    for model in business_models:
        db.refresh(model)  # 确保加载字段关系
    
    # 获取所有数据感知配置
    sensing_configs = db.query(DataSensingConfig).all()
    
    # 获取所有驱动逻辑（包含关联的事件和任务）
    drive_logics = db.query(DriveLogic).all()
    for logic in drive_logics:
        db.refresh(logic)  # 确保加载events和tasks关系
    
    # 获取所有任务（包含关联的能力）
    tasks = db.query(Task).all()
    for task in tasks:
        db.refresh(task)  # 确保加载capabilities关系
    
    # 获取所有Agent和能力
    agents = db.query(Agent).all()
    capabilities = db.query(Capability).all()
    
    return {
        "nodes": _build_nodes(
            data_sources, business_models, sensing_configs, 
            drive_logics, tasks, agents, capabilities
        ),
        "edges": _build_edges(
            data_sources, business_models, sensing_configs, 
            drive_logics, tasks, capabilities
        )
    }

@router.get("/drive-visualization/model/{model_id}")
def get_model_driven_graph(model_id: str, db: Session = Depends(get_db)):
    """获取指定业务模型的驱动链路图"""
    # 获取指定业务模型
    business_model = db.query(BusinessModel).filter(
        BusinessModel.id == model_id
    ).first()
    if not business_model:
        raise HTTPException(status_code=404, detail="Business model not found")
    
    # 获取关联的数据感知配置
    sensing_configs = db.query(DataSensingConfig).filter(
        DataSensingConfig.model_id == model_id
    ).all()
    
    # 获取关联的驱动逻辑
    drive_logic_ids = set()
    for config in sensing_configs:
        for logic in config.logics:
            drive_logic_ids.add(logic.id)
    
    drive_logics = db.query(DriveLogic).filter(
        DriveLogic.id.in_(list(drive_logic_ids))
    ).all() if drive_logic_ids else []
    
    # 获取关联的任务
    task_ids = set()
    for logic in drive_logics:
        for task in logic.tasks:
            task_ids.add(task.id)
    
    tasks = db.query(Task).filter(
        Task.id.in_(list(task_ids))
    ).all() if task_ids else []
    
    # 获取关联的能力和Agent
    capability_ids = set()
    for task in tasks:
        for cap in task.capabilities:
            capability_ids.add(cap.id)
    
    capabilities = db.query(Capability).filter(
        Capability.id.in_(list(capability_ids))
    ).all() if capability_ids else []
    
    agent_ids = set()
    for cap in capabilities:
        for agent in cap.agents:
            agent_ids.add(agent.id)
    
    agents = db.query(Agent).filter(
        Agent.id.in_(list(agent_ids))
    ).all() if agent_ids else []
    
    # 获取数据源信息
    data_source = db.query(DataSource).filter(
        DataSource.id == business_model.data_source_id
    ).first()
    
    return {
        "nodes": _build_nodes(
            [data_source] if data_source else [], 
            [business_model], 
            sensing_configs, 
            drive_logics, 
            tasks, 
            agents, 
            capabilities
        ),
        "edges": _build_edges(
            [data_source] if data_source else [], 
            [business_model], 
            sensing_configs, 
            drive_logics, 
            tasks, 
            capabilities
        )
    }

def _build_nodes(data_sources, business_models, sensing_configs, 
                drive_logics, tasks, agents, capabilities):
    """构建节点列表"""
    nodes = []
    
    # 数据源节点
    for ds in data_sources:
        nodes.append({
            "id": f"ds_{ds.id}",
            "type": "data_source",
            "name": ds.name,
            "description": ds.description or "",
            "data": {
                "id": ds.id,
                "type": ds.type,
                "connection_string": ds.connection_string
            }
        })
    
    # 业务模型节点
    for bm in business_models:
        nodes.append({
            "id": f"bm_{bm.id}",
            "type": "business_model",
            "name": bm.name,
            "description": bm.description or "",
            "data": {
                "id": bm.id,
                "primary_key_id": bm.primary_key_id,
                "field_count": len(bm.fields) if bm.fields else 0
            }
        })
    
    # 数据感知配置节点
    for config in sensing_configs:
        nodes.append({
            "id": f"sensing_{config.id}",
            "type": "sensing_config",
            "name": config.name,
            "description": config.description or "",
            "data": {
                "id": config.id,
                "type": config.type,
                "status": config.status,
                "config": config.config
            }
        })
    
    # 驱动逻辑节点
    for logic in drive_logics:
        nodes.append({
            "id": f"logic_{logic.id}",
            "type": "drive_logic",
            "name": logic.name,
            "description": logic.description or "",
            "data": {
                "id": logic.id,
                "type": logic.type,
                "config": logic.config
            }
        })
    
    # 任务节点
    for task in tasks:
        nodes.append({
            "id": f"task_{task.id}",
            "type": "task",
            "name": task.name,
            "description": task.description or "",
            "data": {
                "id": task.id,
                "config": task.config
            }
        })
    
    # 能力节点
    for cap in capabilities:
        nodes.append({
            "id": f"cap_{cap.id}",
            "type": "capability",
            "name": cap.name,
            "description": cap.description or "",
            "data": {
                "id": cap.id
            }
        })
    
    # Agent节点
    for agent in agents:
        nodes.append({
            "id": f"agent_{agent.id}",
            "type": "agent",
            "name": agent.name,
            "description": agent.description or "",
            "data": {
                "id": agent.id,
                "status": agent.status
            }
        })
    
    return nodes

def _build_edges(data_sources, business_models, sensing_configs, 
                drive_logics, tasks, capabilities):
    """构建边列表"""
    edges = []
    
    # 数据源 -> 业务模型
    for bm in business_models:
        if bm.data_source_id:
            edges.append({
                "source": f"ds_{bm.data_source_id}",
                "target": f"bm_{bm.id}",
                "type": "data_source_to_model"
            })
    
    # 业务模型 -> 数据感知配置
    for config in sensing_configs:
        if config.model_id:
            edges.append({
                "source": f"bm_{config.model_id}",
                "target": f"sensing_{config.id}",
                "type": "model_to_sensing"
            })
    
    # 数据感知配置 -> 驱动逻辑 (多对多)
    for config in sensing_configs:
        for logic in config.logics:
            edges.append({
                "source": f"sensing_{config.id}",
                "target": f"logic_{logic.id}",
                "type": "sensing_to_logic"
            })
    
    # 驱动逻辑 -> 任务 (多对多)
    for logic in drive_logics:
        for task in logic.tasks:
            edges.append({
                "source": f"logic_{logic.id}",
                "target": f"task_{task.id}",
                "type": "logic_to_task"
            })
    
    # 任务 -> 能力 (多对多)
    for task in tasks:
        for cap in task.capabilities:
            edges.append({
                "source": f"task_{task.id}",
                "target": f"cap_{cap.id}",
                "type": "task_to_capability"
            })
    
    # 能力 -> Agent (多对多)
    for cap in capabilities:
        for agent in cap.agents:
            edges.append({
                "source": f"cap_{cap.id}",
                "target": f"agent_{agent.id}",
                "type": "capability_to_agent"
            })
    
    return edges
```

## 2. 前端主组件 (frontend/src/components/DriveVisualization/DriveVisualization.jsx)

```jsx
import React, { useState, useEffect } from 'react';
import { Card, Select, Spin, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import GraphVisualization from './GraphVisualization';

const { Option } = Select;

const DriveVisualization = () => {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('full'); // 'full' or 'model'
  const [selectedModel, setSelectedModel] = useState(null);
  const [businessModels, setBusinessModels] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchBusinessModels();
    if (viewMode === 'full') {
      fetchFullGraph();
    }
  }, [viewMode]);

  const fetchBusinessModels = async () => {
    try {
      const response = await api.get('/business-models');
      setBusinessModels(response.data);
    } catch (error) {
      message.error('获取业务模型失败');
    }
  };

  const fetchFullGraph = async () => {
    setLoading(true);
    try {
      const response = await api.get('/drive-visualization/full-graph');
      setGraphData(response.data);
    } catch (error) {
      message.error('获取全景图失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchModelGraph = async (modelId) => {
    setLoading(true);
    try {
      const response = await api.get(`/drive-visualization/model/${modelId}`);
      setGraphData(response.data);
    } catch (error) {
      message.error('获取模型驱动图失败');
    } finally {
      setLoading(false);
    }
  };

  const handleViewModeChange = (value) => {
    setViewMode(value);
    if (value === 'full') {
      fetchFullGraph();
    }
  };

  const handleModelChange = (value) => {
    setSelectedModel(value);
    fetchModelGraph(value);
  };

  const handleNodeClick = (node) => {
    // 根据节点类型跳转到对应的管理页面
    switch (node.type) {
      case 'data_source':
        navigate('/data-source');
        break;
      case 'business_model':
        navigate('/business-model');
        break;
      case 'sensing_config':
        navigate('/data-sensing');
        break;
      case 'drive_logic':
        navigate('/drive-logic');
        break;
      case 'task':
        navigate('/drive-logic');
        break;
      case 'agent':
        navigate('/agent');
        break;
      default:
        break;
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>驱动全景可视化</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <Select 
            value={viewMode} 
            onChange={handleViewModeChange}
            style={{ width: 150 }}
          >
            <Option value="full">完整全景图</Option>
            <Option value="model">按模型查看</Option>
          </Select>
          {viewMode === 'model' && (
            <Select
              placeholder="选择业务模型"
              value={selectedModel}
              onChange={handleModelChange}
              style={{ width: 200 }}
            >
              {businessModels.map(model => (
                <Option key={model.id} value={model.id}>
                  {model.name} ({model.id})
                </Option>
              ))}
            </Select>
          )}
        </div>
      </div>
      
      <Card>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
          </div>
        ) : graphData ? (
          <GraphVisualization 
            data={graphData} 
            onNodeClick={handleNodeClick}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            暂无数据，请先配置驱动逻辑
          </div>
        )}
      </Card>
    </div>
  );
};

export default DriveVisualization;
```

## 3. 图形可视化组件 (frontend/src/components/DriveVisualization/GraphVisualization.jsx)

```jsx
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const GraphVisualization = ({ data, onNodeClick }) => {
  const svgRef = useRef();

  useEffect(() => {
    if (!data || !data.nodes || !data.edges) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 1200;
    const height = 800;

    // 创建缩放行为
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    const g = svg.append('g');

    // 创建力导向布局
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges).id(d => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(60));

    // 创建连线
    const link = g.append('g')
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2);

    // 创建节点组
    const node = g.append('g')
      .selectAll('g')
      .data(data.nodes)
      .enter()
      .append('g')
      .call(drag(simulation));

    // 添加节点圆圈
    node.append('circle')
      .attr('r', 25)
      .attr('fill', d => getNodeColor(d.type))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .on('click', (event, d) => {
        event.stopPropagation();
        onNodeClick(d);
      });

    // 添加节点文本
    node.append('text')
      .attr('dy', 5)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#000')
      .text(d => d.name.length > 8 ? d.name.substring(0, 8) + '...' : d.name);

    // 更新位置
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('transform', d => `translate(${d.x}, ${d.y})`);
    });

    // 拖拽函数
    function drag(simulation) {
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }

      return d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
    }

    // 节点颜色映射
    function getNodeColor(nodeType) {
      const colorMap = {
        'data_source': '#4CAF50',
        'business_model': '#2196F3',
        'sensing_config': '#FF9800',
        'drive_logic': '#9C27B0',
        'task': '#E91E63',
        'capability': '#607D8B',
        'agent': '#795548'
      };
      return colorMap[nodeType] || '#9E9E9E';
    }

    // 清理函数
    return () => {
      simulation.stop();
    };
  }, [data]);

  return (
    <div style={{ overflow: 'hidden', border: '1px solid #e8e8e8', borderRadius: 4 }}>
      <svg ref={svgRef} width="100%" height="800"></svg>
    </div>
  );
};

export default GraphVisualization;
```

## 4. 路由注册 (app/main.py)

在现有的路由导入中添加：

```python
# 导入部分
from app.api import example, data_source, business_model, data_sensing, drive_logic, agent, test_data, drive_log, test_execution, drive_visualization

# 路由注册部分  
app.include_router(drive_visualization.router, prefix="/api/v1", tags=["Drive Visualization"])
```

## 5. 前端路由集成 (frontend/src/App.jsx)

```jsx
// 导入组件
import DriveVisualization from './components/DriveVisualization/DriveVisualization';

// 路由配置
<Route path="/drive-visualization" element={<DriveVisualization />} />

// 菜单配置（需要导入图标）
import { FundProjectionScreenOutlined } from '@ant-design/icons';

// 在菜单项中添加
{
  key: 'drive-visualization',
  label: '驱动可视化',
  icon: <FundProjectionScreenOutlined />
}
```

## 6. 前端依赖安装

确保安装D3.js依赖：

```bash
cd frontend
npm install d3
```

## 7. 文件结构

创建以下目录结构：

```
frontend/
└── src/
    └── components/
        └── DriveVisualization/
            ├── DriveVisualization.jsx
            └── GraphVisualization.jsx
```

## 使用说明

1. **后端开发**: 
   - 创建 `app/api/drive_visualization.py` 文件
   - 在 `app/main.py` 中注册新路由

2. **前端开发**:
   - 创建 `frontend/src/components/DriveVisualization/` 目录
   - 实现两个React组件文件
   - 更新 `App.jsx` 添加路由和菜单项
   - 安装D3.js依赖

3. **测试验证**:
   - 访问 `/drive-visualization` 页面
   - 测试完整全景图和按模型查看两种模式
   - 验证节点点击跳转功能
   - 测试交互功能（拖拽、缩放）

这些代码样例可以直接复制使用，只需要根据实际的项目结构调整导入路径和配置即可。D3.js提供了强大的图形可视化能力，支持复杂的交互操作，能够很好地展示驱动全景的复杂关系。