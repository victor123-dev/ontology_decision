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
      default:
        break;
    }
  };

  return (
    <div style={{ width: '100%' }}>
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
      
      <Card style={{ width: '100%' }}>
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