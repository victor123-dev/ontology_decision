import React, { useState, useCallback, useEffect } from 'react';
import GraphCanvas from './components/GraphCanvas';
import Toolbar from './components/Toolbar';
import PropertyPanel from './components/PropertyPanel';
import { ontologyViewApi, businessModelApi, businessModelLinkApi, actionApi } from '../../../services/api';
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

  // 监听模型和关系和行动的变更事件
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

    // 行动创建
    const handleActionCreated = ({ action }) => {
      console.log('handleActionCreated', action);
      setGraphData(prev => {
        // 处理行动-模型连线的更新，有目标模型，创建新的连线
        const newLinks = [...prev.links];
        const targetModelId = action.target_model_id;
        if (targetModelId) {
          const newActionLink = {
            id: `action_${action.id}_to_${targetModelId}`,
            source: action.id,
            target: targetModelId,
            name: "作用于",
            description: `${action.name || 'Action'} 作用于 ${targetModelId}`,
            data: {
              type: "action_to_model",
              action_id: action.id,
              model_id: targetModelId
            }
          };
          newLinks.push(newActionLink);
        }
        return { ...prev, links: newLinks, nodes: [...prev.nodes, { 
          id: action.id, 
          name: action.name, 
          type: 'action',
          description: action.description, 
          data: action 
        }] };
      });
    };

    // 行动更新
    const handleActionUpdated = ({ actionId, updatedFields }) => {
      setGraphData(prev => {
        const newNodes = [...prev.nodes];
        const nodeIndex = newNodes.findIndex(n => n.id === actionId);
        if (nodeIndex !== -1) {
          // 直接修改原对象，保持 D3 引用
          Object.assign(newNodes[nodeIndex], updatedFields);
          // 更新 data 字段
          if (newNodes[nodeIndex].data) {
          newNodes[nodeIndex].data = { ...newNodes[nodeIndex].data, ...updatedFields };
          }
        }
        
        const newLinks = [...prev.links];
        // 处理行动-模型连线的更新（当目标模型发生变化时）
        const actionNode = newNodes.find(n => n.id === actionId);
        const newTargetModelId = updatedFields.target_model_id;
        
        if (newTargetModelId) {
          // 找到现有的行动-模型连线
          const existingLinkIndex = newLinks.findIndex(link => 
            (String(link.source) === String(actionId) || String(link.source?.id) === String(actionId)) &&
            link.data?.type === 'action_to_model'
          );
          
          if (existingLinkIndex !== -1) {
            const existingLink = newLinks[existingLinkIndex];
            const existingTargetModelId = existingLink.target || existingLink.target?.id;
            
            // 如果目标模型发生了变化，需要更新连线
            if (String(existingTargetModelId) !== String(newTargetModelId)) {
              // 1. 移除旧的连线
              newLinks.splice(existingLinkIndex, 1);
              
              // 2. 添加新的连线
              const newActionLink = {
                id: `action_${actionId}_to_${newTargetModelId}`,
                source: actionId,
                target: newTargetModelId,
                name: "作用于",
                description: `${actionNode?.name || 'Action'} 作用于 ${newTargetModelId}`,
                data: {
                  type: "action_to_model",
                  action_id: actionId,
                  model_id: newTargetModelId
                }
              };
              newLinks.push(newActionLink);
            }
          } else {
            // 如果没有现有的连线，但有新的目标模型，创建新的连线
            const newActionLink = {
              id: `action_${actionId}_to_${newTargetModelId}`,
              source: actionId,
              target: newTargetModelId,
              name: "作用于",
              description: `${actionNode?.name || 'Action'} 作用于 ${newTargetModelId}`,
              data: {
                type: "action_to_model",
                action_id: actionId,
                model_id: newTargetModelId
              }
            };
            newLinks.push(newActionLink);
          }
        } else {
          // 如果没有目标模型，移除所有相关的行动-模型连线
          const linksToRemove = newLinks.filter(link => 
            (String(link.source) === String(actionId) || String(link.source?.id) === String(actionId)) &&
            link.data?.type === 'action_to_model'
          );
          
          linksToRemove.forEach(linkToRemove => {
            const index = newLinks.findIndex(link => link.id === linkToRemove.id);
            if (index !== -1) {
              newLinks.splice(index, 1);
            }
          });
        }
        
        return { ...prev, links: newLinks, nodes: newNodes };
      });
      // 如果当前选中的元素是这个行动，也需要更新 selectedElement
      setSelectedElement(prev => {
        // 判断是否需要更新
        if (prev?.data.id === actionId) {
          return {
          ...prev,
          data: {
            ...prev.data,
            // 更新行动的基本信息
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

    // 行动删除
    const handleActionDeleted = ({ actionId }) => {
      setGraphData(prev => ({
        nodes: prev.nodes.filter(node => node.id !== actionId),
        links: prev.links.filter(l => 
          String(l.source.id) !== String(actionId) && 
          String(l.target.id) !== String(actionId)
        )
      }));
      // 如果删除的是当前选中的行动，关闭属性栏
      setSelectedElement(prev => {
        if (prev?.data.id === actionId) {
          return null;
        }
        return prev;
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
    modelEventBus.on('action_created', handleActionCreated);
    modelEventBus.on('action_updated', handleActionUpdated);
    modelEventBus.on('action_deleted', handleActionDeleted);

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
      modelEventBus.off('action_created', handleActionCreated);
      modelEventBus.off('action_updated', handleActionUpdated);
      modelEventBus.off('action_deleted', handleActionDeleted);
    };
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

  const handleUpdateModel = useCallback(async (nodeId, newData) => {    
    try {
      await businessModelApi.update(nodeId, newData);
      
      // 触发事件通知其他页面
      modelEventBus.emitModelUpdated(nodeId, newData);
    } catch (error) {
      message.error('更新模型失败');
    }
  }, []);
  
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
    } catch (error) {
      message.error('更新关系失败');
    }
  }, []);

  const handleUpdateAction = useCallback(async (actionId, newData) => {    
    try {
      await actionApi.update(actionId, newData);
      
      // 发布行动更新事件
      modelEventBus.emitActionUpdated(actionId, newData);
    } catch (error) {
      message.error('更新行动失败');
    }
  }, []);

  const handleDeleteElement = useCallback(async () => {
    if (!selectedElement) return;
    
    try {
      if (selectedElement.type === 'business_model') {
        await businessModelApi.delete(selectedElement.data.id);
        
        // 触发事件通知其他页面
        modelEventBus.emitModelDeleted(selectedElement.data.id);
        
      } else if (selectedElement.type === 'link') {
        await businessModelLinkApi.delete(selectedElement.data.id);
        
        // 触发事件通知其他页面
        modelEventBus.emitLinkDeleted(selectedElement.data.id);
        
      } else if (selectedElement.type === 'action') {
        await actionApi.delete(selectedElement.data.id);
        
        // 触发事件通知其他页面
        modelEventBus.emitActionDeleted(selectedElement.data.id);
        
      }
      setSelectedElement(null);
    } catch (error) {
      message.error('删除失败');
    }
  }, [selectedElement]);

  const handleAddModel = useCallback(async (modelData) => {
    try {
      const response = await businessModelApi.create(modelData);
      
      // 触发事件通知其他页面
      modelEventBus.emitModelCreated(response.data);
    } catch (error) {
      message.error('创建模型失败');
    }
  }, []);

  const handleAddLink = useCallback(async (linkData) => {
    try {
      const response = await businessModelLinkApi.create(linkData);
      
      // 触发事件通知其他页面
      modelEventBus.emitLinkCreated(response.data);
    } catch (error) {
      message.error('创建关系失败');
    }
  }, []);

  const handleAddAction = useCallback(async (actionData) => {
    try {
      const response = await actionApi.create(actionData);
      
      // 触发事件通知其他页面
      modelEventBus.emitActionCreated(response.data);
    } catch (error) {
      message.error('创建行动失败');
    }
  }, []);

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%' }}>
      <div style={{ flex: 1, position: 'relative' }}>
        <Toolbar 
          onAddModel={handleAddModel} 
          onAddLink={handleAddLink} 
          onAddAction={handleAddAction} 
          models={graphData.nodes.filter(n => n.type === 'business_model')}
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
          onUpdate={selectedElement.type === 'business_model' ? handleUpdateModel : selectedElement.type === 'link' ? handleUpdateLink : handleUpdateAction}
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