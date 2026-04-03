import React, { useState, useCallback, useEffect } from 'react';
import GraphCanvas from './components/GraphCanvas';
import Toolbar from './components/Toolbar';
import PropertyPanel from './components/PropertyPanel';
import { ontologyViewApi, businessModelApi, businessModelLinkApi } from '../../../services/api';
import { message, Modal, Form, Input, Select } from 'antd';
import { modelEventBus } from '../../../utils/modelEventBus';

const OntologyView = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [selectedElement, setSelectedElement] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fieldModalVisible, setFieldModalVisible] = useState(false);
  const [editingField, setEditingField] = useState(null);
  const [editingModelId, setEditingModelId] = useState(null);
  const [fieldForm] = Form.useForm();

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

  // 监听模型和关系的变更事件
  useEffect(() => {
    // 模型创建
    const handleModelCreated = ({ model }) => {
      setGraphData(prev => ({
        ...prev,
        nodes: [...prev.nodes, { 
          id: model.id, 
          name: model.name, 
          type: 'business_model', 
          description: model.description, 
          data: model 
        }]
      }));
    };

    // 模型更新
    const handleModelUpdated = ({ modelId, updatedFields }) => {
      setGraphData(prev => {
        const newNodes = [...prev.nodes];
        const nodeIndex = newNodes.findIndex(n => n.id === modelId);
        if (nodeIndex !== -1) {
          // 直接修改原对象，保持 D3 引用
          Object.assign(newNodes[nodeIndex], updatedFields);
          // 更新 data 字段
          if (newNodes[nodeIndex].data) {
            newNodes[nodeIndex].data = { ...newNodes[nodeIndex].data, ...updatedFields };
          }
        }
        return { ...prev, nodes: newNodes };
      });
      // 如果当前选中的元素是这个模型，也需要更新 selectedElement
      setSelectedElement(prev => {
        // 判断是否需要更新
        if (prev?.data.id === modelId) {
          return {
            ...prev,
            data: {
              ...prev.data,
              // 更新模型的基本信息
              name: updatedFields.name || prev.data.name,
              description: updatedFields.description || prev.data.description,
              // 更新模型的完整数据
              data: {
                ...prev.data.data,
                ...updatedFields
              }
            }
          };
        }
        // 不需要更新，返回原状态（保持不变）
        return prev;
      });
    };

    // 模型删除
    const handleModelDeleted = ({ modelId }) => {
      setGraphData(prev => ({
        nodes: prev.nodes.filter(n => n.id !== modelId),
        links: prev.links.filter(l => 
          String(l.source.id) !== String(modelId) && 
          String(l.target.id) !== String(modelId)
        )
      }));
      // 如果删除的是当前选中的模型或相关链接，关闭属性栏
      setSelectedElement(prev => {
        if (!prev) return prev;
        if (prev.type === 'business_model' && prev.data.id === modelId) {
          return null;
        }
        if (prev.type === 'link' && 
            (String(prev.data.source) === String(modelId) || 
             String(prev.data.target) === String(modelId))) {
          return null;
        }
        return prev;
      });
    };

    // 关系创建
    const handleLinkCreated = ({ link }) => {
      setGraphData(prev => ({
        ...prev,
        links: [...prev.links, {
          id: link.id,
          source: link.source_model,
          target: link.target_model,
          name: link.name,
          description: link.description,
          data: link
        }]
      }));
    };

    // 关系更新
    const handleLinkUpdated = ({ linkId, updatedFields }) => {
      setGraphData(prev => {
        const newLinks = [...prev.links];
        const linkIndex = newLinks.findIndex(l => l.id === linkId);
        if (linkIndex !== -1) {
          // 直接修改原对象，保持 D3 引用
          Object.assign(newLinks[linkIndex], updatedFields);
          // 更新 data 字段
          if (newLinks[linkIndex].data) {
            newLinks[linkIndex].data = { ...newLinks[linkIndex].data, ...updatedFields };
          }
        }
        return { ...prev, links: newLinks };
      });
      // 如果当前选中的元素是这个关系，也需要更新 selectedElement
      setSelectedElement(prev => {
        if (prev?.data.id === linkId) {
          return {
            ...prev,
            data: {
              ...prev.data,
              // 更新关系的基本信息
              name: updatedFields.name || prev.data.name,
              description: updatedFields.description || prev.data.description,
              data: {
                ...prev.data.data,
                ...updatedFields
              }
            }
          };
        }
        return prev;
 });
    };

    // 关系删除
    const handleLinkDeleted = ({ linkId }) => {
      setGraphData(prev => ({
        ...prev,
        links: prev.links.filter(l => l.id !== linkId)
      }));
      // 如果删除的是当前选中的关系，关闭属性栏
      setSelectedElement(prev => {
        if (prev?.data.id === linkId) {
          return null;
        }
        return prev;
      });
    };

    // 字段创建
    const handleFieldCreated = ({ modelId, field }) => {
      setGraphData(prev => {
        const newNodes = [...prev.nodes];
        const nodeIndex = newNodes.findIndex(n => n.id === modelId);
        if (nodeIndex !== -1) {
          const node = newNodes[nodeIndex];
          if (node.data && node.data.fields) {
            node.data.fields = [...node.data.fields, field];
          }
        }
        return { ...prev, nodes: newNodes };
      });
      
      // 如果当前选中的元素是这个模型，也需要更新 selectedElement
      setSelectedElement(prev => {
        if (prev?.data.id === modelId) {
          const existingFields = prev?.data?.data?.fields || [];
          return {
            ...prev,
            data: {
              ...prev.data,
              data: {
                ...prev.data.data,
                fields: [...existingFields, field]
              }
            }
          };
        }
        return prev;
      });
    };

    // 字段更新
    const handleFieldUpdated = ({ modelId, fieldId, updatedFields }) => {
      setGraphData(prev => {
        const newNodes = [...prev.nodes];
        const nodeIndex = newNodes.findIndex(n => n.id === modelId);
        if (nodeIndex !== -1) {
          const node = newNodes[nodeIndex];
          if (node.data && node.data.fields) {
            node.data.fields = node.data.fields.map(field => 
              field.field_id === fieldId ? { ...field, ...updatedFields } : field
            );
          }
        }
        return { ...prev, nodes: newNodes };
      });
      
      // 如果当前选中的元素是这个模型，也需要更新 selectedElement
      setSelectedElement(prev => {
        // 判断是否需要更新
        if (prev?.data.id === modelId) {
          // 需要更新，返回新的状态
          if (prev?.data?.data?.fields) {
            return {
              ...prev,
              data: {
                ...prev.data,
                data: {
                  ...prev.data.data,
                  fields: prev.data.data.fields.map(field => 
                    field.field_id === fieldId ? { ...field, ...updatedFields } : field
                  )
                }
              }
            };
          }
        }
        // 不需要更新，返回原状态（保持不变）
        return prev;
      });
    };

    // 字段删除
    const handleFieldDeleted = ({ modelId, fieldId }) => {
      setGraphData(prev => {
        const newNodes = [...prev.nodes];
        const nodeIndex = newNodes.findIndex(n => n.id === modelId);
        if (nodeIndex !== -1) {
          const node = newNodes[nodeIndex];
          if (node.data && node.data.fields) {
            node.data.fields = node.data.fields.filter(field => field.field_id !== fieldId);
            // 如果删除的是主键，需要更新主键ID
            if (node.data.primary_key_id === fieldId) {
              node.data.primary_key_id = null;
            }
          }
        }
        return { ...prev, nodes: newNodes };
      });
      
      // 如果当前选中的元素是这个模型，也需要更新 selectedElement
      setSelectedElement(prev => {
        if (prev?.data.id === modelId) {
          if (prev?.data?.data?.fields) {
            const updatedFields = prev.data.data.fields.filter(field => field.field_id !== fieldId);
            let updatedData = {
              ...prev.data.data,
              fields: updatedFields
            };
            // 如果删除的是主键，需要更新主键ID
            if (prev.data.data.primary_key_id === fieldId) {
              updatedData.primary_key_id = null;
            }
            return {
              ...prev,
              data: {
                ...prev.data,
                data: updatedData
              }
            };
          }
          return prev;
        }
      });
    };

    // 订阅所有事件
    modelEventBus.on('model_created', handleModelCreated);
    modelEventBus.on('model_updated', handleModelUpdated);
    modelEventBus.on('model_deleted', handleModelDeleted);
    modelEventBus.on('link_created', handleLinkCreated);
    modelEventBus.on('link_updated', handleLinkUpdated);
    modelEventBus.on('link_deleted', handleLinkDeleted);
    modelEventBus.on('field_created', handleFieldCreated);
    modelEventBus.on('field_updated', handleFieldUpdated);
    modelEventBus.on('field_deleted', handleFieldDeleted);

    // 清理订阅
    return () => {
      modelEventBus.off('model_created', handleModelCreated);
      modelEventBus.off('model_updated', handleModelUpdated);
      modelEventBus.off('model_deleted', handleModelDeleted);
      modelEventBus.off('link_created', handleLinkCreated);
      modelEventBus.off('link_updated', handleLinkUpdated);
      modelEventBus.off('link_deleted', handleLinkDeleted);
      modelEventBus.off('field_created', handleFieldCreated);
      modelEventBus.off('field_updated', handleFieldUpdated);
      modelEventBus.off('field_deleted', handleFieldDeleted);
    };
  }, []);

  const handleUpdateNode = useCallback(async (nodeId, newData) => {    
    try {
      await businessModelApi.update(nodeId, newData);
      
      // 触发事件通知其他页面
      modelEventBus.emitModelUpdated(nodeId, newData);
      
      // 更新图数据（本体视图内部处理）
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
        return {
          ...prev,
          nodes: newNodes
        };
      });
      
      // 更新选中元素
      setSelectedElement(prev => {
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
        return newSelectedElement;
      });
    } catch (error) {
      message.error('更新模型失败');
    }
  }, []);

  useEffect(() => {
  if (fieldModalVisible) {
    // 延迟设置，确保模态框完全打开后再设置表单值
    const timer = setTimeout(() => {
      fieldForm.setFieldsValue(editingField || {});
    }, 0);
    return () => clearTimeout(timer);
  } else {
    // 模态框关闭时重置表单
    fieldForm.resetFields();
  }
}, [editingField, fieldModalVisible, fieldForm]);

  // 字段操作处理函数
  const handleAddField = useCallback((modelId) => {
    setEditingModelId(modelId);
    setEditingField(null);
    setFieldModalVisible(true);
  }, []);

  const handleEditField = useCallback((modelId, field) => {
    setEditingModelId(modelId);
    setEditingField(field);
    setFieldModalVisible(true);
  }, []);

  const handleDeleteField = useCallback(async (modelId, fieldId) => {
    try {
      await businessModelApi.deleteField(modelId, fieldId);
      message.success('字段删除成功');
      
      // 触发事件通知其他页面
      modelEventBus.emitFieldDeleted(modelId, fieldId);
      
      // 更新本体视图中的字段列表
      setGraphData(prev => {
        const newNodes = [...prev.nodes];
        const nodeIndex = newNodes.findIndex(n => n.id === modelId);
        if (nodeIndex !== -1) {
          const node = newNodes[nodeIndex];
          if (node.data && node.data.fields) {
            node.data.fields = node.data.fields.filter(f => f.field_id !== fieldId);
            // 如果删除的是主键，需要更新主键ID
            if (node.data.primary_key_id === fieldId) {
              node.data.primary_key_id = null;
            }
          }
        }
        return { ...prev, nodes: newNodes };
      });
      
      // 如果当前选中的是这个模型，更新选中元素
      if (selectedElement?.data.id === modelId) {
        setSelectedElement(prev => {
          if (prev?.data?.data?.fields) {
            const updatedFields = prev.data.data.fields.filter(f => f.field_id !== fieldId);
            return {
              ...prev,
              data: {
                ...prev.data,
                data: {
                  ...prev.data.data,
                  fields: updatedFields,
                  primary_key_id: prev.data.data.primary_key_id === fieldId ? null : prev.data.data.primary_key_id
                }
              }
            };
          }
          return prev;
        });
      }
    } catch (error) {
      message.error('删除字段失败');
    }
  }, [selectedElement]);

  const handleSaveField = useCallback(async (values) => {
    try {
      if (editingModelId && editingField) {
        // 更新现有字段
        await businessModelApi.updateField(editingModelId, editingField.field_id, values);
        message.success('字段更新成功');
        
        // 触发事件通知其他页面
        modelEventBus.emitFieldUpdated(editingModelId, editingField.field_id, values);
      } else if (editingModelId) {
        // 创建新字段
        const response = await businessModelApi.createField(editingModelId, values);
        message.success('字段创建成功');
        
        // 触发事件通知其他页面
        modelEventBus.emitFieldCreated(editingModelId, response.data);
      }
      
      setFieldModalVisible(false);
      setEditingField(null);
      setEditingModelId(null);
      fieldForm.resetFields();
    } catch (error) {
      message.error('操作字段失败');
    }
  }, [editingModelId, editingField, fieldForm]);

  const handleUpdateLink = useCallback(async (linkId, newData) => {
    try {
      await businessModelLinkApi.update(linkId, newData);
      
      // 触发事件通知其他页面
      modelEventBus.emitLinkUpdated(linkId, newData);
      
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
      if (selectedElement.type === 'business_model') {
        await businessModelApi.delete(selectedElement.data.id);
        
        // 触发事件通知其他页面
        modelEventBus.emitModelDeleted(selectedElement.data.id);
        
        setGraphData(prev => ({
          nodes: prev.nodes.filter(n => n.id !== selectedElement.data.id),
          links: prev.links.filter(l => 
            String(l.source) !== String(selectedElement.data.id) && 
            String(l.target) !== String(selectedElement.data.id)
          ),
        }));
      } else {
        await businessModelLinkApi.delete(selectedElement.data.id);
        
        // 触发事件通知其他页面
        modelEventBus.emitLinkDeleted(selectedElement.data.id);
        
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
      
      // 触发事件通知其他页面
      modelEventBus.emitModelCreated(response.data);
      
      const newNode = {
        id: response.data.id,
        name: response.data.name,
        type: response.data.type,
        description: response.data.description,
        data: response.data
      };
      setGraphData(prev => ({ ...prev, nodes: [...prev.nodes, newNode] }));
    } catch (error) {
      message.error('创建模型失败');
    }
  }, []);

  const handleAddLink = useCallback(async (linkData) => {
    try {
      const response = await businessModelLinkApi.create(linkData);
      
      // 触发事件通知其他页面
      modelEventBus.emitLinkCreated(response.data);
      
      // 转换为图数据格式
      const linkGraphData = {
        id: response.data.id,
        source: response.data.source_model,
        target: response.data.target_model,
        name: response.data.name,
        description: response.data.description,
        data: response.data
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
      {/* 字段编辑模态框 */}
      <Modal
        title={editingField ? '编辑字段' : '添加字段'}
        open={fieldModalVisible}
        onOk={() => {
          fieldForm.submit();
        }}
        onCancel={() => {
          setFieldModalVisible(false);
          setEditingField(null);
          setEditingModelId(null);
          fieldForm.resetFields();
        }}
        width={600}
      >
        <Form
          form={fieldForm}
          layout="vertical"
          onFinish={handleSaveField}
        >
          <Form.Item
            name="field_id"
            label="字段ID"
            rules={[{ required: true, message: '请输入字段ID' }]}
          >
            <Input disabled={!!editingField} />
          </Form.Item>
          
          <Form.Item
            name="name"
            label="中文名称"
            rules={[{ required: true, message: '请输入中文名称' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="中文说明"
          >
            <Input.TextArea />
          </Form.Item>
          
          <Form.Item
            name="data_type"
            label="数据类型"
            rules={[{ required: true, message: '请选择数据类型' }]}
          >
            <Select>
              <Select.Option value="string">字符串</Select.Option>
              <Select.Option value="integer">整数</Select.Option>
              <Select.Option value="float">浮点数</Select.Option>
              <Select.Option value="boolean">布尔值</Select.Option>
              <Select.Option value="date">日期</Select.Option>
              <Select.Option value="datetime">日期时间</Select.Option>
              <Select.Option value="text">文本</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      </div>

      {selectedElement && (
        <PropertyPanel 
          element={selectedElement}
          onUpdate={selectedElement.type === 'business_model' ? handleUpdateNode : handleUpdateLink}
          onDelete={handleDeleteElement}
          onAddField={handleAddField}
          onEditField={handleEditField}
          onDeleteField={handleDeleteField}
        />
      )}
    </div>
  );
};

export default OntologyView;