import React, { useState, useCallback, useEffect } from 'react';
import GraphCanvas from './components/GraphCanvas';
import Toolbar from './components/Toolbar';
import PropertyPanel from './components/PropertyPanel';
import { ontologyViewApi, businessModelApi, businessModelLinkApi } from '../../../services/api';
import { message } from 'antd';

const OntologyView = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [selectedElement, setSelectedElement] = useState(null);
  const [loading, setLoading] = useState(false);

  // 从后端获取本体视图数据
  const fetchOntologyData = async () => {
    setLoading(true);
    try {
      const response = await ontologyViewApi.getGraph();
      // 转换数据格式为图数据
      const nodes = response.data.nodes.map(node => ({
        id: node.id,
        name: node.name,
        type: node.type,
        description: node.description,
        data: node.data
      }));
      
      const graphLinks = response.data.edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        name: edge.name,
        description: edge.description,
        data: edge.data
      }));
      
      setGraphData({ nodes, links: graphLinks });
    } catch (error) {
      message.error('获取本体视图数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOntologyData();
  }, []);

  const handleUpdateNode = useCallback(async (nodeId, newData) => {
    console.log("要更新的节点数据:", newData);
    
    try {
      await businessModelApi.update(nodeId, newData);
      // 更新图数据
      setGraphData(prev => {
        const newNodes = [...prev.nodes];
        const nodeIndex = newNodes.findIndex(n => n.id === nodeId);
        if (nodeIndex !== -1) {
          // 直接修改原对象，而不是创建新对象
          const nodeToUpdate = newNodes[nodeIndex];
          nodeToUpdate.name = newData.name || nodeToUpdate.name;
          nodeToUpdate.description = newData.description || nodeToUpdate.description;
          nodeToUpdate.data = { ...nodeToUpdate.data, ...newData };
        }
        console.log("更新后的图数据:", newNodes);
        return {
          ...prev,
          nodes: newNodes
        };
      });
      
      // 更新选中元素
      setSelectedElement(prev => {
        console.log("更新前的元素:", prev);
        const newSelectedElement = prev?.data.id === nodeId ? { 
          ...prev, 
          data: {
            ...prev.data,
            name: newData.name,
            description: newData.description,
            data: {
              ...prev.data.data,
              ...newData
            }
          }
        } : prev;
        console.log("更新后的选中元素:", newSelectedElement);
        return newSelectedElement;
      });
    } catch (error) {
      message.error('更新模型失败');
    }
  }, []);

  const handleUpdateLink = useCallback(async (linkId, newData) => {
    console.log(newData);
    try {
      await businessModelLinkApi.update(linkId, newData);
      setGraphData(prev => {
        const newLinks = [...prev.links];
        const linkIndex = newLinks.findIndex(l => l.id === linkId);
        if (linkIndex !== -1) {
          // 直接修改原对象，而不是创建新对象
          const linkToUpdate = newLinks[linkIndex];
          linkToUpdate.name = newData.name || linkToUpdate.name;
          linkToUpdate.description = newData.description || linkToUpdate.description;
          linkToUpdate.data = { ...linkToUpdate.data, ...newData };
        }
        
        return {
          ...prev,
          links: newLinks
        };
      });
      setSelectedElement(prev => {
        console.log("更新前的元素:", prev);
        // 如果是当前要更新的关系
        if (prev?.data.id === linkId) {
          const newSelectedElement = {
            ...prev,
            data: {
              ...prev.data,
              // 更新 prev.data 中的 name 和 description
              name: newData.name || prev.data.name,
              description: newData.description || prev.data.description,
              // 更新 prev.data.data 中的内容（用 newData 覆盖）
              data: {
                ...prev.data.data,
                ...newData
              }
            }
          };
          console.log("更新后的选中元素:", newSelectedElement);
          return newSelectedElement;
        }
        // 如果不是当前关系，保持原样
        return prev;
      });
    } catch (error) {
      message.error('更新关系失败');
    }
  }, []);

  const handleDeleteElement = useCallback(async () => {
    if (!selectedElement) return;
    
    try {
      if (selectedElement.type === 'node') {
        await businessModelApi.delete(selectedElement.data.id);
        setGraphData(prev => ({
          nodes: prev.nodes.filter(n => n.id !== selectedElement.data.id),
          links: prev.links.filter(l => 
            String(l.source) !== String(selectedElement.data.id) && 
            String(l.target) !== String(selectedElement.data.id)
          ),
        }));
      } else {
        await businessModelLinkApi.delete(selectedElement.data.id);
        setGraphData(prev => ({
          ...prev,
          links: prev.links.filter(l => l.id !== selectedElement.data.id),
        }));
      }
      setSelectedElement(null);
    } catch (error) {
      message.error('删除失败');
    }
  }, [selectedElement]);

  const handleAddNode = useCallback(async (nodeData) => {
    try {
      const response = await businessModelApi.create(nodeData);
      const newNode = {
        id: response.data.id,
        name: response.data.name,
        type: response.data.type
      };
      setGraphData(prev => ({ ...prev, nodes: [...prev.nodes, newNode] }));
    } catch (error) {
      message.error('创建模型失败');
    }
  }, []);

  const handleAddLink = useCallback(async (linkData) => {
    try {
      const response = await businessModelLinkApi.create(linkData);
      // 转换为图数据格式
      const linkGraphData = {
        id: response.data.id,
        source: response.data.source_model,
        target: response.data.target_model,
        name: response.data.name
      };
      setGraphData(prev => ({ ...prev, links: [...prev.links, linkGraphData] }));
    } catch (error) {
      message.error('创建关系失败');
    }
  }, []);

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%' }}>
      <div style={{ flex: 1, position: 'relative' }}>
        <Toolbar 
          onAddNode={handleAddNode} 
          onAddLink={handleAddLink} 
          nodes={graphData.nodes}
        />
        <GraphCanvas 
          data={graphData} 
          onSelect={setSelectedElement} 
          selectedId={selectedElement?.data.id}
        />
      </div>

      {selectedElement && (
        <PropertyPanel 
          element={selectedElement}
          onUpdate={selectedElement.type === 'node' ? handleUpdateNode : handleUpdateLink}
          onDelete={handleDeleteElement}
        />
      )}
    </div>
  );
};

export default OntologyView;