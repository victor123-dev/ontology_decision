import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Button, Radio, message } from 'antd';
import { dataSourceApi, businessModelApi } from '../../../../services/api';

const { Option } = Select;

const Toolbar = ({ onAddNode, onAddLink, nodes }) => {
  const [nodeModalVisible, setNodeModalVisible] = useState(false);
  const [linkModalVisible, setLinkModalVisible] = useState(false);
  const [nodeForm] = Form.useForm();
  const [linkForm] = Form.useForm();
  const [dataSources, setDataSources] = useState([]);
  const [businessModels, setBusinessModels] = useState([]);

  useEffect(() => {
    fetchDataSources();
    fetchBusinessModels();
  }, []);

  const fetchDataSources = async () => {
    try {
      const response = await dataSourceApi.getAll();
      setDataSources(response.data);
    } catch (error) {
      message.error('获取数据源失败');
    }
  };

  const fetchBusinessModels = async () => {
    try {
      const response = await businessModelApi.getAll();
      setBusinessModels(response.data);
    } catch (error) {
      message.error('获取业务模型失败');
    }
  };

  const getModelOptions = () => {
    return businessModels.map(model => (
      <Option key={model.id} value={model.id}>
        {model.name} ({model.id})
      </Option>
    ));
  };

  const getFieldOptions = (modelId) => {
    const model = businessModels.find(m => m.id === modelId);
    if (!model) return [];
    const fields = model.fields || [];
    return fields.map(field => (
      <Option key={field.field_id} value={field.field_id}>
        {field.name} ({field.field_id})
        {field.field_id === model.primary_key_id && ' [主键]'}
      </Option>
    ));
  };

  const handleNodeSubmit = () => {
    nodeForm.validateFields().then(values => {
      onAddNode(values);
      nodeForm.resetFields();
      setNodeModalVisible(false);
    });
  };

  const handleLinkSubmit = () => {
    linkForm.validateFields().then(values => {
      onAddLink(values);
      linkForm.resetFields();
      setLinkModalVisible(false);
    });
  };

  return (
    <>
      <div style={{ 
        position: 'absolute', top: 16, left: 16, 
        background: '#FFFFFF', padding: '8px 12px', borderRadius: '8px', 
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)', zIndex: 10,
        display: 'flex', gap: '12px', alignItems: 'center'
      }}>
        <Button type="primary" size="small" onClick={() => setNodeModalVisible(true)}>
          + 新增模型
        </Button>
        <Button size="small" onClick={() => setLinkModalVisible(true)} disabled={nodes.length < 2}>
          + 新增关系
        </Button>
      </div>

      {/* 新增业务模型模态框 */}
      <Modal
        title="添加业务模型"
        open={nodeModalVisible}
        onOk={nodeForm.submit}
        onCancel={() => setNodeModalVisible(false)}
      >
        <Form form={nodeForm} layout="vertical" onFinish={handleNodeSubmit}>
          <Form.Item name="id" label="模型ID" rules={[{ required: true, message: '请输入模型ID' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="中文名称" rules={[{ required: true, message: '请输入中文名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="中文说明">
            <Input.TextArea />
          </Form.Item>
          <Form.Item name="primary_key_id" label="主键ID">
            <Input />
          </Form.Item>
          <Form.Item name="data_source_id" label="数据源" rules={[{ required: true, message: '请选择数据源' }]}>
            <Select>
              {dataSources.map((ds) => (
                <Option key={ds.id} value={ds.id}>{ds.name}</Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 新增模型关系模态框 */}
      <Modal
        title="添加模型关系"
        open={linkModalVisible}
        onOk={linkForm.submit}
        onCancel={() => setLinkModalVisible(false)}
        width={800}
        afterOpenChange={(open) => {
          if (open) {
            // 新建关系时设置默认值
            linkForm.setFieldsValue({
              cardinality: 'one-to-many'
            });
          }
        }}
      >
        <Form 
          form={linkForm} 
          layout="vertical" 
          onFinish={handleLinkSubmit}
        >
          <Form.Item name="id" label="关系ID" rules={[{ required: true, message: '请输入关系ID' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="关系中文名称" rules={[{ required: true, message: '请输入关系中文名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="关系中文说明">
            <Input.TextArea />
          </Form.Item>
          
          {/* 基数关系选择 */}
          <Form.Item label="基数关系">
            <Form.Item name="cardinality" noStyle>
              <Radio.Group>
                <Radio value="one-to-one">一对一 (One-to-One)</Radio>
                <Radio value="one-to-many">一对多 (One-to-Many)</Radio>
                <Radio value="many-to-one">多对一 (Many-to-One)</Radio>
                <Radio value="many-to-many">多对多 (Many-to-Many)</Radio>
              </Radio.Group>
            </Form.Item>
          </Form.Item>
          
          {/* 模型选择 - 动态布局 */}
          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.cardinality !== currentValues.cardinality}>
            {({ getFieldValue }) => {
              const cardinality = getFieldValue('cardinality');
              const isManyToMany = cardinality === 'many-to-many';
              
              if (isManyToMany) {
                // 三栏布局：源模型 ←→ 中间表 ←→ 目标模型
                return (
                  <div style={{ display: 'flex', gap: '20px' }}>
                    {/* 源模型 */}
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="source_model" 
                        label="源模型" 
                        rules={[{ required: true, message: '请选择源模型' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.source_model !== currentValues.source_model
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue, setFieldsValue }) => {
                          const sourceModelId = innerGetFieldValue('source_model');
                          const sourceModel = businessModels.find(m => m.id === sourceModelId);
                          const primaryKey = sourceModel?.primary_key_id;
                          
                          // 多对多关系中，源字段必须使用主键
                          if (primaryKey) {
                            const currentSourceKey = innerGetFieldValue('source_key');
                            if (currentSourceKey !== primaryKey) {
                              setFieldsValue({ source_key: primaryKey });
                            }
                          }
                          
                          return (
                            <Form.Item 
                              name="source_key" 
                              label="源字段" 
                              rules={[{ required: true, message: '请选择源字段' }]}
                            >
                              <Select disabled>
                                {getFieldOptions(sourceModelId)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                    </div>
                    
                    {/* 中间表 */}
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="intermediate_model" 
                        label="中间表" 
                        rules={[{ required: true, message: '请选择中间表' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.intermediate_model !== currentValues.intermediate_model
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue }) => {
                          const intermediateModelId = innerGetFieldValue('intermediate_model');
                          return (
                            <>
                              <Form.Item 
                                name="intermediate_source_key" 
                                label="中间表→源模型字段" 
                                rules={[{ required: true, message: '请选择中间表到源模型的字段' }]}
                              >
                                <Select>
                                  {getFieldOptions(intermediateModelId)}
                                </Select>
                              </Form.Item>
                              
                              <Form.Item 
                                name="intermediate_target_key" 
                                label="中间表→目标模型字段" 
                                rules={[{ required: true, message: '请选择中间表到目标模型的字段' }]}
                              >
                                <Select>
                                  {getFieldOptions(intermediateModelId)}
                                </Select>
                              </Form.Item>
                            </>
                          );
                        }}
                      </Form.Item>
                    </div>
                    
                    {/* 目标模型 */}
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="target_model" 
                        label="目标模型" 
                        rules={[{ required: true, message: '请选择目标模型' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.target_model !== currentValues.target_model
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue, setFieldsValue }) => {
                          const targetModelId = innerGetFieldValue('target_model');
                          const targetModel = businessModels.find(m => m.id === targetModelId);
                          const primaryKey = targetModel?.primary_key_id;
                          
                          // 多对多关系中，目标字段必须使用主键
                          if (primaryKey) {
                            const currentTargetKey = innerGetFieldValue('target_key');
                            if (currentTargetKey !== primaryKey) {
                              setFieldsValue({ target_key: primaryKey });
                            }
                          }
                          
                          return (
                            <Form.Item 
                              name="target_key" 
                              label="目标字段" 
                              rules={[{ required: true, message: '请选择目标字段' }]}
                            >
                              <Select disabled>
                                {getFieldOptions(targetModelId)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                    </div>
                  </div>
                );
              } else {
                // 两栏布局：源模型 ←→ 目标模型
                return (
                  <div style={{ display: 'flex', gap: '20px' }}>
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="source_model" 
                        label="源模型" 
                        rules={[{ required: true, message: '请选择源模型' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.source_model !== currentValues.source_model ||
                          prevValues.cardinality !== currentValues.cardinality
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue, setFieldsValue }) => {
                          const sourceModelId = innerGetFieldValue('source_model');
                          const cardinality = innerGetFieldValue('cardinality');
                          
                          // 获取模型信息
                          const sourceModel = businessModels.find(m => m.id === sourceModelId);
                          const primaryKey = sourceModel?.primary_key_id;
                          
                          // 判断是否需要自动选择主键
                          let shouldAutoSelectPrimaryKey = false;
                          let shouldDisableField = false;
                          
                          if (cardinality === 'one-to-many') {
                            // 一对多：源模型是"one"侧，必须使用主键
                            shouldAutoSelectPrimaryKey = true;
                            shouldDisableField = true;
                          } else if (cardinality === 'many-to-one') {
                            // 多对一：源模型是"many"侧，可以自由选择
                            shouldAutoSelectPrimaryKey = false;
                            shouldDisableField = false;
                          } else if (cardinality === 'one-to-one') {
                            // 一对一：可以自动选择主键但不禁用
                            shouldAutoSelectPrimaryKey = true;
                            shouldDisableField = false;
                          }
                          
                          // 自动选择主键
                          if (shouldAutoSelectPrimaryKey && primaryKey) {
                            const currentSourceKey = innerGetFieldValue('source_key');
                            if (currentSourceKey !== primaryKey) {
                              setFieldsValue({ source_key: primaryKey });
                            }
                          }
                          
                          return (
                            <Form.Item 
                              name="source_key" 
                              label="源字段" 
                              rules={[{ required: true, message: '请选择源字段' }]}
                            >
                              <Select disabled={shouldDisableField}>
                                {getFieldOptions(sourceModelId)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                    </div>
                    
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="target_model" 
                        label="目标模型" 
                        rules={[{ required: true, message: '请选择目标模型' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.target_model !== currentValues.target_model ||
                          prevValues.cardinality !== currentValues.cardinality
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue, setFieldsValue }) => {
                          const targetModelId = innerGetFieldValue('target_model');
                          const cardinality = innerGetFieldValue('cardinality');
                          
                          // 获取模型信息
                          const targetModel = businessModels.find(m => m.id === targetModelId);
                          const primaryKey = targetModel?.primary_key_id;
                          
                          // 判断是否需要自动选择主键
                          let shouldAutoSelectPrimaryKey = false;
                          let shouldDisableField = false;
                          
                          if (cardinality === 'one-to-many') {
                            // 一对多：目标模型是"many"侧，可以自由选择
                            shouldAutoSelectPrimaryKey = false;
                            shouldDisableField = false;
                          } else if (cardinality === 'many-to-one') {
                            // 多对一：目标模型是"one"侧，必须使用主键
                            shouldAutoSelectPrimaryKey = true;
                            shouldDisableField = true;
                          } else if (cardinality === 'one-to-one') {
                            // 一对一：可以自动选择主键但不禁用
                            shouldAutoSelectPrimaryKey = true;
                            shouldDisableField = false;
                          }
                          
                          // 自动选择主键
                          if (shouldAutoSelectPrimaryKey && primaryKey) {
                            const currentTargetKey = innerGetFieldValue('target_key');
                            if (currentTargetKey !== primaryKey) {
                              setFieldsValue({ target_key: primaryKey });
                            }
                          }
                          
                          return (
                            <Form.Item 
                              name="target_key" 
                              label="目标字段" 
                              rules={[{ required: true, message: '请选择目标字段' }]}
                            >
                              <Select disabled={shouldDisableField}>
                                {getFieldOptions(targetModelId)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                    </div>
                  </div>
                );
              }
            }}
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default Toolbar;
