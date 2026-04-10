import React, { useState, useEffect, useMemo } from 'react';
import { Modal, Form, Input, Select, Button, Radio, message, Steps, Tabs, Space, Card, Divider, InputNumber, Switch, Typography, List, Tag, Popover, Spin } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, MinusCircleOutlined, CodeOutlined } from '@ant-design/icons';
import { dataSourceApi, businessModelApi, businessModelLinkApi, actionApi, sdkApi } from '../../../../services/api';
import { modelEventBus } from '../../../../utils/modelEventBus';

const { Option } = Select;

const Toolbar = ({ onAddModel, onAddLink, onAddAction, models, }) => {
  const [modelModalVisible, setModelModalVisible] = useState(false);
  const [linkModalVisible, setLinkModalVisible] = useState(false);
  const [actionModalVisible, setActionModalVisible] = useState(false);
  const [sdkModalVisible, setSdkModalVisible] = useState(false);
  const [isGeneratingSdk, setIsGeneratingSdk] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [initialFormValues, setInitialFormValues] = useState({});
  const [modelForm] = Form.useForm();
  const [linkForm] = Form.useForm();
  const [actionForm] = Form.useForm();
  const [dataSources, setDataSources] = useState([]);
  const [businessModels, setBusinessModels] = useState([]);
  const [modelLinks, setModelLinks] = useState([]);
  const [sdkForm] = Form.useForm();

  useEffect(() => {
    fetchDataSources();
    fetchBusinessModels();
    fetchModelLinks();
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

  const fetchModelLinks = async () => {
    try {
      const response = await businessModelLinkApi.getAll();
      setModelLinks(response.data);
    } catch (error) {
      message.error('获取模型关系失败');
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

  // 行动相关辅助函数
  const generateObjectParameters = (model, operation) => {
    if (!model) return [];
    
    if (operation === 'delete_object') {
      // 删除操作只包含主键
      const primaryKeyField = model.fields.find(field => field.field_id === model.primary_key_id);
      if (primaryKeyField) {
        return [{
          name: primaryKeyField.field_id,
          type: mapDataTypeToParamType(primaryKeyField.data_type),
          required: true,
          default_value: '',
          description: `删除${model.name}的主键`
        }];
      }
      return [];
    } else if (operation === 'update_object') {
      // 更新操作包含所有字段，但主键设为必填
      return model.fields.map(field => {
        const isPrimaryKey = field.field_id === model.primary_key_id;
        return {
          name: field.field_id,
          type: mapDataTypeToParamType(field.data_type),
          required: isPrimaryKey, // 主键必填，其他字段可选
          default_value: '',
          description: field.description || field.name + (isPrimaryKey ? ' (主键，必填)' : '')
        };
      });
    } else {
      // 创建操作包含所有字段（都可选）
      return model.fields.map(field => ({
        name: field.field_id,
        type: mapDataTypeToParamType(field.data_type),
        required: false,
        default_value: '',
        description: field.description || field.name
      }));
    }
  };

  const generateLinkParameters = (link, operation) => {
    if (!link) return [];
    
    if (operation === 'delete_link') {
      // 删除操作只包含主键（中间表的主键）
      if (link.cardinality === 'many-to-many' && link.intermediate_model) {
        // 对于多对多关系，需要找到中间表模型
        const intermediateModel = businessModels.find(m => m.id === link.intermediate_model);
        if (intermediateModel) {
          const primaryKeyField = intermediateModel.fields.find(field => field.field_id === intermediateModel.primary_key_id);
          if (primaryKeyField) {
            return [{
              name: primaryKeyField.field_id,
              type: mapDataTypeToParamType(primaryKeyField.data_type),
              required: true,
              default_value: '',
              description: `删除${link.name}关系的主键`
            }];
          }
        }
      }
      // 其他关系类型，使用源键和目标键
      return [
        {
          name: link.source_key,
          type: 'string',
          required: true,
          default_value: '',
          description: '源模型主键'
        },
        {
          name: link.target_key,
          type: 'string',
          required: true,
          default_value: '',
          description: '目标模型主键'
        }
      ];
    } else {
      // 创建操作包含中间表的所有字段（多对多）或其他必要字段
      if (link.cardinality === 'many-to-many' && link.intermediate_model) {
        const intermediateModel = businessModels.find(m => m.id === link.intermediate_model);
        if (intermediateModel) {
          return intermediateModel.fields.map(field => ({
            name: field.field_id,
            type: mapDataTypeToParamType(field.data_type),
            required: false,
            default_value: '',
            description: field.description || field.name
          }));
        }
      }
      // 其他关系类型
      return [
        {
          name: link.source_key,
          type: 'string',
          required: true,
          default_value: '',
          description: '源模型主键'
        },
        {
          name: link.target_key,
          type: 'string',
          required: true,
          default_value: '',
          description: '目标模型主键'
        }
      ];
    }
  };

  const mapDataTypeToParamType = (dataType) => {
    const typeMap = {
      'string': 'string',
      'text': 'string',
      'integer': 'integer', 
      'float': 'float',
      'boolean': 'boolean',
      'object': 'object',
      'array': 'array',
      'date': 'date',
      'datetime': 'datetime',
    };
    return typeMap[dataType?.toLowerCase()] || 'string';
  };

  const handleActionTypeChange = (value) => {
    // 清除相关字段
    if (value === 'object') {
      actionForm.setFieldsValue({ 
        operation: undefined, 
        target_model_id: undefined, 
        target_link_id: undefined,
        function_code: undefined,
        parameters: []
      })
    } else if (value === 'link') {
      actionForm.setFieldsValue({ 
        operation: undefined, 
        target_model_id: undefined, 
        target_link_id: undefined,
        function_code: undefined,
        parameters: []
      })
    } else if (value === 'function') {
      actionForm.setFieldsValue({ 
        operation: undefined, 
        target_model_id: undefined, 
        target_link_id: undefined,
        parameters: []
      })
    }
  }

  const handleNextStep = async () => {
    try {
      if (currentStep === 0) {
        // 验证基础配置
        await actionForm.validateFields(['name'])
      } else if (currentStep === 1) {
        // 验证行动类型配置
        const actionType = actionForm.getFieldValue('action_type')
        if (!actionType) {
          message.error('请选择行动类型')
          return
        }
        if (actionType === 'object') {
          await actionForm.validateFields(['operation', 'target_model_id'])
        } else if (actionType === 'link') {
          await actionForm.validateFields(['operation', 'target_link_id'])
        } else if (actionType === 'function') {
          await actionForm.validateFields(['function_code'])
        }
      } else if (currentStep === 2) {
        // 验证参数配置（可选，因为参数可以为空）
        // 这里不强制验证，允许空参数列表
      } else if (currentStep === 3) {
        return
      }
      // currentStep === 3 是最后一步，不需要验证，直接提交
      if (currentStep < 3) {
        setCurrentStep(currentStep + 1)
      }
    } catch (error) {
      console.log('Validation failed:', error)
    }
  }

  const handleAddAction = () => {
    setInitialFormValues({});
    setCurrentStep(0);
    actionForm.resetFields();
    setActionModalVisible(true);
  }

  const handleGenerateSdk = async () => {
    try {
      await sdkForm.validateFields();
      const values = sdkForm.getFieldsValue();
      
      // 确保输出路径正确
      if (!values.output_path) {
        values.output_path = `./sdk/${values.package_name}`;
      }
      
      setIsGeneratingSdk(true);
      message.loading('正在生成SDK，请稍候...', 0);
      
      const response = await sdkApi.generate(values);
      
      message.destroy();
      if (response.data.success) {
        message.success('SDK生成成功！');
        setSdkModalVisible(false);
        sdkForm.resetFields();
      } else {
        message.error(`SDK生成失败: ${response.data.message || '未知错误'}`);
      }
    } catch (error) {
      message.destroy();
      console.error('SDK生成错误:', error);
      message.error(`SDK生成失败: ${error.response?.data?.detail || error.message || '未知错误'}`);
    } finally {
      setIsGeneratingSdk(false);
    }
  };

  const handleModelSubmit = () => {
    modelForm.validateFields().then(values => {
      onAddModel(values);
      modelForm.resetFields();
      setModelModalVisible(false);
    });
  };

  const handleLinkSubmit = () => {
    linkForm.validateFields().then(values => {
      onAddLink(values);
      linkForm.resetFields();
      setLinkModalVisible(false);
    });
  };

  const handleActionSubmit = () => {
    actionForm.validateFields().then(values => {
      onAddAction(values);
      actionForm.resetFields();
      setActionModalVisible(false);
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
        <Button type="primary" size="small" onClick={() => setModelModalVisible(true)}>
          + 新增模型
        </Button>
        <Button size="small" onClick={() => setLinkModalVisible(true)} disabled={models.length < 2}>
          + 新增关系
        </Button>
        <Button size="small" onClick={handleAddAction}>
          + 新增行动
        </Button>
        <Button size="small" icon={<CodeOutlined />} onClick={() => setSdkModalVisible(true)}>
          生成SDK
        </Button>
      </div>

      {/* 新增业务模型模态框 */}
      <Modal
        title="添加业务模型"
        open={modelModalVisible}
        onOk={modelForm.submit}
        onCancel={() => setModelModalVisible(false)}
      >
        <Form form={modelForm} layout="vertical" onFinish={handleModelSubmit}>
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

      {/* 新增行动模态框 */}
      <Modal
        title="添加行动"
        open={actionModalVisible}
        onCancel={() => setActionModalVisible(false)}
        width={900}
        footer={null}
        maskClosable={false}
      >
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Steps.Step title="基础配置" />
          <Steps.Step title="行动类型" />
          <Steps.Step title="参数配置" />
          <Steps.Step title="提交条件" />
        </Steps>
        
        <Form form={actionForm} layout="vertical" onFinish={handleActionSubmit} initialValues={initialFormValues}>
          {/* 步骤1: 基础配置 */}
          <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
            <Form.Item 
              name="id" 
              label="行动ID" 
              rules={[
                { required: true, message: '请输入行动ID' },
                { 
                  pattern: /^[a-zA-Z0-9_-]+$/, 
                  message: '行动ID只能包含字母、数字、下划线和连字符'
                }
              ]}
            >
              <Input placeholder="例如: create_customer_order" />
            </Form.Item>

            <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
              <Input />
            </Form.Item>

            <Form.Item name="description" label="说明">
              <Input.TextArea rows={3} />
            </Form.Item>
          </div>

          {/* 步骤2: 行动类型 */}
          <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
            <Form.Item name="action_type" label="行动类型" rules={[{ required: true, message: '请选择行动类型' }]}>
              <Select onChange={handleActionTypeChange}>
                <Option value="object">对象行动</Option>
                <Option value="link">关系行动</Option>
                <Option value="function">函数行动</Option>
              </Select>
            </Form.Item>

            <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => 
              prevValues.action_type !== currentValues.action_type || 
              (prevValues.action_type === currentValues.action_type && prevValues.operation !== currentValues.operation)
            }>
              {({ getFieldValue }) => {
                const actionType = getFieldValue('action_type')
                
                if (actionType === 'object') {
                  return (
                    <>
                      <Form.Item name="operation" label="操作" rules={[{ required: true, message: '请选择操作' }]}>
                        <Select onChange={(value) => {
                          actionForm.setFieldsValue({ target_model_id: undefined });
                          // 清除参数
                          actionForm.setFieldsValue({ parameters: [] });
                        }}>
                          <Option value="create_object">创建对象</Option>
                          <Option value="update_object">更新对象</Option>
                          <Option value="delete_object">删除对象</Option>
                        </Select>
                      </Form.Item>
                      <Form.Item name="target_model_id" label="目标模型" rules={[{ required: true, message: '请选择目标模型' }]}>
                        <Select onChange={(value) => {
                          const selectedModel = businessModels.find(m => m.id === value);
                          const operation = actionForm.getFieldValue('operation');
                          if (selectedModel && operation) {
                            const params = generateObjectParameters(selectedModel, operation);
                            actionForm.setFieldsValue({ parameters: params });
                          }
                        }}>
                          {businessModels.map(model => (
                            <Option key={model.id} value={model.id}>
                              {model.name} ({model.id})
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </>
                  )
                }
                
                if (actionType === 'link') {
                  // 过滤出多对多关系
                  const manyToManyLinks = modelLinks.filter(link => link.cardinality === 'many-to-many');
                  
                  return (
                    <>
                      <Form.Item name="operation" label="操作" rules={[{ required: true, message: '请选择操作' }]}>
                        <Select onChange={(value) => {
                          actionForm.setFieldsValue({ target_link_id: undefined });
                          // 清除参数
                          actionForm.setFieldsValue({ parameters: [] });
                        }}>
                          <Option value="create_link">创建关系</Option>
                          <Option value="delete_link">删除关系</Option>
                        </Select>
                      </Form.Item>
                      <Form.Item name="target_link_id" label="目标关系" rules={[{ required: true, message: '请选择目标关系' }]}>
                        <Select onChange={(value) => {
                          const selectedLink = modelLinks.find(l => l.id === value);
                          const operation = actionForm.getFieldValue('operation');
                          if (selectedLink && operation) {
                            const params = generateLinkParameters(selectedLink, operation);
                            actionForm.setFieldsValue({ parameters: params });
                          }
                        }}>
                          {manyToManyLinks.map(link => (
                            <Option key={link.id} value={link.id}>
                              {link.name} ({link.id})
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </>
                  )
                }
                
                if (actionType === 'function') {
                  return (
                    <Form.Item name="function_code" label="函数代码" rules={[{ required: true, message: '请输入函数代码' }]}>
                      <Input.TextArea 
                        rows={10} 
                        placeholder={`# 函数行动示例（业务场景优先，SDK 可选增强）
# 可以访问 parameters 变量（用户提交的参数）
# 必须在脚本末尾定义 result 变量（包含执行结果的字典）
# 如需使用 SDK：from my_ontology_sdk import OntologyClient

# 示例1: 简单数据处理（基础功能）
processed_name = parameters.get("name", "").upper()
age_group = "adult" if parameters.get("age", 0) >= 18 else "minor"

result = {
    "success": True,
    "message": "数据处理完成",
    "data": {
        "processed_name": processed_name,
        "age_group": age_group
    }
}

# 示例2: 条件逻辑（业务规则）
email = parameters.get("email", "")
if email and "@" in email:
    result = {"success": True, "message": "邮箱格式正确"}
else:
    result = {"success": False, "message": "邮箱格式错误"}

# 示例3: 数学计算（价格计算）
quantity = parameters.get("quantity", 0)
price = parameters.get("price", 0)
total = quantity * price
discount = total * 0.1 if total > 100 else 0

result = {
    "total": total,
    "discount": discount,
    "final_amount": total - discount,
    "success": True
}

# 示例4: SDK 增强 - 查询关联数据（可选）
# from my_ontology_sdk import OntologyClient
# client = OntologyClient("http://localhost:8080")
# customer = client.models.customer.get(parameters["customer_id"])
# if customer:
#     result = {
#         "success": True,
#         "customer_name": customer.name,
#         "credit_limit": customer.credit_limit
#     }
# else:
#     result = {"success": False, "message": "客户未找到"} `}
                      />
                    </Form.Item>
                  )
                }
                
                return null
              }}
            </Form.Item>
          </div>

          {/* 步骤3: 参数配置 */}
          <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
            <Form.Item
              name="parameters"
              label="参数列表"
              getValueProps={(value) => ({ value: value || [] })}
              getValueFromEvent={(value) => value}
            >
              <ParameterEditor />
            </Form.Item>
          </div>

          {/* 步骤4: 提交条件 */}
          <div style={{ display: currentStep === 3 ? 'block' : 'none' }}>
            <Form.Item
              name="submission_criteria"
              label="条件列表"
              getValueProps={(value) => ({ value: value || [] })}
              getValueFromEvent={(value) => value}
            >
              <CriteriaEditor />
            </Form.Item>
          </div>

          <div style={{ marginTop: 24, textAlign: 'right' }}>
            {currentStep > 0 && (
              <Button style={{ marginRight: 8 }} onClick={() => setCurrentStep(currentStep - 1)}>
                上一步
              </Button>
            )}
            {currentStep < 3 ? (
              <Button type="primary" onClick={() => handleNextStep()}>
                下一步
              </Button>
            ) : (
              <Button type="primary" htmlType="submit">
                创建
              </Button>
            )}
          </div>
        </Form>
      </Modal>
    
      {/* 生成SDK模态框 */}
      <Modal
        title="生成Python Ontology SDK"
        open={sdkModalVisible}
        onOk={handleGenerateSdk}
        onCancel={() => setSdkModalVisible(false)}
        confirmLoading={isGeneratingSdk}
        okText="生成SDK"
        cancelText="取消"
        width={600}
      >
        <Spin spinning={isGeneratingSdk} tip="正在生成SDK...">
          <Form 
            form={sdkForm} 
            layout="vertical"
            onValuesChange={(changedValues) => {
              if (changedValues.package_name !== undefined) {
                // 当包名改变时，自动更新输出路径
                const outputPath = `./sdk/${changedValues.package_name}`;
                sdkForm.setFieldsValue({ output_path: outputPath });
              }
            }}
          >
            <Form.Item 
              name="package_name" 
              label="包名" 
              initialValue="my_ontology_sdk"
              rules={[{ required: true, message: '请输入包名' }]}
            >
              <Input placeholder="例如: my_ontology_sdk" />
            </Form.Item>
            
            <Form.Item 
              name="version" 
              label="版本号" 
              initialValue="1.0.0"
              rules={[{ required: true, message: '请输入版本号' }]}
            >
              <Input placeholder="例如: 1.0.0" />
            </Form.Item>
            
            <Form.Item 
              name="output_path" 
              label="输出路径" 
              initialValue="./sdk/my_ontology_sdk"
            >
              <Input disabled />
            </Form.Item>
            
            <div style={{ backgroundColor: '#f5f5f5', padding: '12px', borderRadius: '4px', fontSize: '12px' }}>
              <p><strong>注意：</strong>SDK生成可能需要较长时间，请耐心等待。</p>
              <p>生成的SDK将包含所有业务模型、关系和行动，并支持面向对象的编程接口。</p>
            </div>
          </Form>
        </Spin>
      </Modal>
    </>
  );
};

// 参数编辑器组件
const ParameterEditor = ({ value = [], onChange }) => {
  const [parameters, setParameters] = useState(value)

  useEffect(() => {
    setParameters(value)
  }, [value])

  const handleAddParameter = () => {
    const newParam = {
      name: '',
      type: 'string',
      required: false,
      default_value: '',
      description: ''
    }
    const newParams = [...parameters, newParam]
    setParameters(newParams)
    onChange?.(newParams)
  }

  const handleRemove = (index) => {
    const newParams = parameters.filter((_, i) => i !== index)
    setParameters(newParams)
    onChange?.(newParams)
  }

  const handleChange = (index, field, value) => {
    const newParams = [...parameters]
    newParams[index][field] = value
    setParameters(newParams)
    onChange?.(newParams)
  }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="dashed" onClick={handleAddParameter} block icon={<PlusOutlined />}>
          添加参数
        </Button>
      </div>
      
      {parameters.map((param, index) => (
        <Card key={index} size="small" style={{ marginBottom: 12 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Form.Item
              label="参数名称"
              required
              validateStatus={param.name ? '' : 'error'}
              help={!param.name ? '参数名称不能为空' : ''}
            >
              <Input
                value={param.name}
                onChange={(e) => handleChange(index, 'name', e.target.value)}
              />
            </Form.Item>
            
            <Form.Item label="参数类型" required>
              <Select
                value={param.type}
                onChange={(value) => handleChange(index, 'type', value)}
                style={{ width: '100%' }}
              >
                <Option value="string">字符串</Option>
                <Option value="text">文本</Option>
                <Option value="integer">整数</Option>
                <Option value="float">浮点数</Option>
                <Option value="boolean">布尔值</Option>
                <Option value="object">对象</Option>
                <Option value="array">数组</Option>
                <Option value="date">日期</Option>
                <Option value="datetime">日期时间</Option>
              </Select>
            </Form.Item>
            
            <Form.Item label="参数说明">
              <Input.TextArea
                value={param.description}
                onChange={(e) => handleChange(index, 'description', e.target.value)}
                rows={2}
                placeholder="描述此参数的用途和业务含义"
              />
            </Form.Item>
            
            <Form.Item label="默认值">
              <Input
                value={param.default_value}
                onChange={(e) => handleChange(index, 'default_value', e.target.value)}
              />
            </Form.Item>
            
            <Form.Item label="是否必填">
              <Switch
                checked={param.required}
                onChange={(checked) => handleChange(index, 'required', checked)}
              />
            </Form.Item>
            
            <Button
              type="text"
              danger
              icon={<MinusCircleOutlined />}
              onClick={() => handleRemove(index)}
            >
              删除参数
            </Button>
          </Space>
        </Card>
      ))}
    </div>
  )
}

// 提交条件编辑器组件
const CriteriaEditor = ({ value = [], onChange }) => {
  const [criteria, setCriteria] = useState(value)

  useEffect(() => {
    setCriteria(value)
  }, [value])

  const handleAddCriterion = () => {
    const newCriterion = {
      type: 'field_validation',
      field_name: '',
      rule: 'not_empty',
      description: ''
    }
    const newCriteria = [...criteria, newCriterion]
    setCriteria(newCriteria)
    onChange?.(newCriteria)
  }

  const handleRemove = (index) => {
    const newCriteria = criteria.filter((_, i) => i !== index)
    setCriteria(newCriteria)
    onChange?.(newCriteria)
  }

  const handleChange = (index, field, value) => {
    const newCriteria = [...criteria]
    newCriteria[index][field] = value
    setCriteria(newCriteria)
    onChange?.(newCriteria)
  }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="dashed" onClick={handleAddCriterion} block icon={<PlusOutlined />}>
          添加条件
        </Button>
      </div>
      
      {criteria.map((criterion, index) => (
        <Card key={index} size="small" style={{ marginBottom: 12 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Form.Item label="条件类型" required>
              <Select
                value={criterion.type}
                onChange={(value) => handleChange(index, 'type', value)}
                style={{ width: '100%' }}
              >
                <Option value="field_validation">字段验证</Option>
                <Option value="custom_condition">自定义条件</Option>
              </Select>
            </Form.Item>
            
            {criterion.type === 'field_validation' && (
              <>
                <Form.Item
                  label="字段名称"
                  required
                  validateStatus={criterion.field_name ? '' : 'error'}
                  help={!criterion.field_name ? '字段名称不能为空' : ''}
                >
                  <Input
                    value={criterion.field_name}
                    onChange={(e) => handleChange(index, 'field_name', e.target.value)}
                  />
                </Form.Item>
                
                <Form.Item label="验证规则" required>
                  <Select
                    value={criterion.rule}
                    onChange={(value) => handleChange(index, 'rule', value)}
                    style={{ width: '100%' }}
                  >
                    <Option value="not_empty">非空</Option>
                    <Option value="email">邮箱格式</Option>
                    <Option value="phone">手机号格式</Option>
                    <Option value="min_length">最小长度</Option>
                    <Option value="max_length">最大长度</Option>
                    <Option value="positive">正数</Option>
                  </Select>
                </Form.Item>
                
                {criterion.rule === 'min_length' && (
                  <Form.Item label="最小长度" required>
                    <InputNumber
                      value={criterion.min_length}
                      onChange={(value) => handleChange(index, 'min_length', value)}
                      min={0}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                )}
                
                {criterion.rule === 'max_length' && (
                  <Form.Item label="最大长度" required>
                    <InputNumber
                      value={criterion.max_length}
                      onChange={(value) => handleChange(index, 'max_length', value)}
                      min={1}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                )}
              </>
            )}
            
            {criterion.type === 'custom_condition' && (
              <>
                <Form.Item label="自定义表达式" required>
                  <Input.TextArea
                    value={criterion.expression}
                    onChange={(e) => handleChange(index, 'expression', e.target.value)}
                    rows={3}
                    placeholder={`# 自定义条件示例（返回布尔值）
# 可以访问所有参数作为变量

# 示例1: 年龄和姓名验证
age >= 18 and len(name) > 0

# 示例2: 邮箱和手机号格式
"@" in email and phone.startswith("1") and len(phone) == 11

# 示例3: 数量和价格验证  
quantity > 0 and price > 0 and quantity * price <= 10000

# 示例4: 复杂条件组合
(age >= 18 or parent_consent) and (email.endswith("@company.com") or is_vip)`}
                  />
                </Form.Item>
                <div style={{ color: '#999', fontSize: '12px', marginBottom: '8px' }}>
                  支持的变量：参数名称（如 name, age）
                  <br />
                  支持的函数：len(), str(), int(), float(), bool(), max(), min(), abs(), sum(), all(), any()
                </div>
              </>
            )}
            
            <Form.Item label="条件说明">
              <Input.TextArea
                value={criterion.description}
                onChange={(e) => handleChange(index, 'description', e.target.value)}
                rows={2}
                placeholder="描述此条件的用途和验证规则"
              />
            </Form.Item>
            
            <Button
              type="text"
              danger
              icon={<MinusCircleOutlined />}
              onClick={() => handleRemove(index)}
            >
              删除条件
            </Button>
          </Space>
        </Card>
      ))}
    </div>
  )
}

export default Toolbar;
