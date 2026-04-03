import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Popconfirm, message, Select, Radio } from 'antd';
import { dataSourceApi, businessModelApi } from '../../../../services/api';

const { Option } = Select;

const PropertyPanel = ({ element, onUpdate, onDelete }) => {
  const [form] = Form.useForm();
  const [isEdit, setIsEdit] = useState(false);
  const [dataSources, setDataSources] = useState([]);
  const [businessModels, setBusinessModels] = useState([]);

  // 选中元素变化时重置
  useEffect(() => {
    if (element && form) {
      // 使用完整的 data 字段进行初始化
      const initialValues = element.data.data;
      form.setFieldsValue(initialValues);
    }
    setIsEdit(false);
  }, [element, form]);

  // 获取数据源和业务模型列表
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

  const handleSave = () => {
    form.validateFields().then(values => {
      onUpdate(element.data.id, values);
      setIsEdit(false);
      message.success('属性修改成功');
    });
  };

  const handleDeleteConfirm = () => {
    onDelete();
    message.success('删除成功');
  };

  const isNode = element.type === 'node';

  return (
    <div style={{ 
      width: '400px', 
      borderLeft: '1px solid #E2E8F0', 
      background: '#FFFFFF', 
      display: 'flex',
      flexDirection: 'column',
      height: '100vh'
    }}>
      <div style={{ 
        padding: '16px 20px', 
        borderBottom: '1px solid #E2E8F0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
          {isNode ? '业务模型属性' : '模型关系属性'}
        </h3>
        <Button type="link" onClick={() => setIsEdit(!isEdit)}>
          {isEdit ? '取消编辑' : '编辑'}
        </Button>
      </div>

      <div style={{ padding: '20px', flex: 1, overflowY: 'auto' }}>
        <Form 
          form={form} 
          layout="vertical"
          initialValues={element.data.data}
        >
          {isNode ? (
            // 业务模型属性
            <>
              <Form.Item name="id" label="模型ID">
                <Input disabled />
              </Form.Item>
              <Form.Item
                name="name"
                label="中文名称"
                rules={[{ required: true, message: '请输入中文名称' }]}
              >
                <Input disabled={!isEdit} />
              </Form.Item>
              <Form.Item name="description" label="中文说明">
                <Input.TextArea disabled={!isEdit} />
              </Form.Item>
              <Form.Item name="primary_key_id" label="主键ID">
                <Input disabled={!isEdit} />
              </Form.Item>
              <Form.Item name="data_source_id" label="数据源">
                <Select disabled={!isEdit}>
                  {dataSources.map((ds) => (
                    <Option key={ds.id} value={ds.id}>{ds.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </>
          ) : (
            // 模型关系属性 - 完全复刻 BusinessModel 中的关系编辑功能
            <>
              <Form.Item name="id" label="关系ID">
                <Input disabled />
              </Form.Item>
              <Form.Item
                name="name"
                label="关系中文名称"
                rules={[{ required: true, message: '请输入关系中文名称' }]}
              >
                <Input disabled={!isEdit} />
              </Form.Item>
              <Form.Item name="description" label="关系中文说明">
                <Input.TextArea disabled={!isEdit} />
              </Form.Item>
              
              {/* 基数关系选择 */}
              <Form.Item label="基数关系">
                <Form.Item name="cardinality" noStyle>
                  <Radio.Group  disabled={!isEdit}>
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
                      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                        {/* 源模型 */}
                        <div style={{ flex: 1, minWidth: '200px' }}>
                          <Form.Item 
                            name="source_model"
                            label="源模型"
                            rules={[{ required: true, message: '请选择源模型' }]}
                          >
                            <Select disabled={!isEdit}>
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
                              {getFieldOptions(form.getFieldValue('source_model') || element.data.source)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                        </div>
                        
                        {/* 中间表 */}
                        <div style={{ flex: 1, minWidth: '200px' }}>
                          <Form.Item 
                            name="intermediate_model" 
                            label="中间表" 
                            rules={[{ required: true, message: '请选择中间表' }]}
                          >
                            <Select disabled={!isEdit}>
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
                                    <Select disabled={!isEdit}>
                                  {getFieldOptions(intermediateModelId)}
                                    </Select>
                                  </Form.Item>
                                  
                                  <Form.Item 
                                    name="intermediate_target_key" 
                                    label="中间表→目标模型字段" 
                                    rules={[{ required: true, message: '请选择中间表到目标模型的字段' }]}
                                  >
                                    <Select disabled={!isEdit}>
                                  {getFieldOptions(intermediateModelId)}
                                    </Select>
                                  </Form.Item>
                                </>
                              );
                            }}
                          </Form.Item>
                        </div>
                        
                        {/* 目标模型 */}
                        <div style={{ flex: 1, minWidth: '200px' }}>
                          <Form.Item 
                            name="target_model"
                            label="目标模型"
                            rules={[{ required: true, message: '请选择目标模型' }]}
                          >
                            <Select disabled={!isEdit}>
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
                              {getFieldOptions(form.getFieldValue('target_model') || element.data.target)}
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
                      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                        <div style={{ flex: 1, minWidth: '200px' }}>
                          <Form.Item 
                            name="source_model"
                            label="源模型"
                            rules={[{ required: true, message: '请选择源模型' }]}
                          >
                            <Select disabled={!isEdit}>
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
                              const sourceModelId = getFieldValue('source_model') || element.data.source;
                              const cardinality = getFieldValue('cardinality');
                              
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
                              if (shouldAutoSelectPrimaryKey && primaryKey && isEdit) {
                                const currentSourceKey = getFieldValue('source_key');
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
                                  <Select disabled={!isEdit || shouldDisableField}>
                                    {getFieldOptions(sourceModelId)}
                                  </Select>
                                </Form.Item>
                              );
                            }}
                          </Form.Item>
                        </div>
                        
                        <div style={{ flex: 1, minWidth: '200px' }}>
                          <Form.Item 
                            name="target_model"
                            label="目标模型"
                            rules={[{ required: true, message: '请选择目标模型' }]}
                          >
                            <Select disabled={!isEdit}>
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
                              const targetModelId = getFieldValue('target_model') || element.data.target;
                              const cardinality = getFieldValue('cardinality');
                              
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
                              if (shouldAutoSelectPrimaryKey && primaryKey && isEdit) {
                                const currentTargetKey = getFieldValue('target_key');
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
                                  <Select disabled={!isEdit || shouldDisableField}>
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
            </>
          )}
        </Form>
      </div>

      <div style={{ 
        padding: '16px 20px', 
        borderTop: '1px solid #E2E8F0',
        display: 'flex',
        gap: '12px'
      }}>
        {isEdit && (
          <Button type="primary" onClick={handleSave} style={{ flex: 1 }}>
            保存修改
          </Button>
        )}
        <Popconfirm
          title={`确定要删除该${isNode ? '业务模型' : '模型关系'}吗？`}
          onConfirm={handleDeleteConfirm}
          okText="确认"
          cancelText="取消"
        >
          <Button danger>
            删除
          </Button>
        </Popconfirm>
      </div>
    </div>
  );
};

export default PropertyPanel;
