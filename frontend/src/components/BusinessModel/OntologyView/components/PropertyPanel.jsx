import React, { useState, useEffect, useMemo } from 'react';
import { Form, Input, Button, Popconfirm, message, Select, Switch, Radio, Collapse, Steps, Divider, Space, List, Tag, Card, Typography } from 'antd';
import { dataSourceApi, businessModelApi, businessModelLinkApi } from '../../../../services/api';
import { modelEventBus } from '../../../../utils/modelEventBus';
import { toPascalCase } from '../../../../utils/stringUtils';
import { PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';

const { Panel } = Collapse;

const { Option } = Select;

const PropertyPanel = ({ element, onUpdate, onDelete, onAddField, onEditField, onDeleteField }) => {
  const [form] = Form.useForm();
  const [isEdit, setIsEdit] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [dataSources, setDataSources] = useState([]);
  const [businessModels, setBusinessModels] = useState([]);
  const [modelLinks, setModelLinks] = useState([]);
  const [fields, setFields] = useState([]);
  const [primaryKeyId, setPrimaryKeyId] = useState(null);

  // 选中元素变化时重置
  useEffect(() => {
    if (element && form) {
      // 使用完整的 data 字段进行初始化
      const initialValues = element.data.data;
      form.setFieldsValue(initialValues);
      
      // 提取字段信息和主键ID
      if (element.type === 'business_model' && element.data.data?.fields) {
        setFields(element.data.data.fields || []);
        setPrimaryKeyId(element.data.data.primary_key_id || null);
      } else {
        setFields([]);
        setPrimaryKeyId(null);
      }
    }
    setIsEdit(false);
  }, [element, form]);

  // 获取数据源、业务模型和模型关系列表
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
          required: isPrimaryKey || field.required, // 主键或字段本身标记为必填则必填
          default_value: '',
          description: field.description || field.name + (isPrimaryKey ? ' (主键，必填)' : '')
        };
      });
    } else {
      // 创建操作包含所有字段，根据字段本身的required属性设置必填状态
      return model.fields.map(field => ({
        name: field.field_id,
        type: mapDataTypeToParamType(field.data_type),
        required: field.required || false, // 使用字段本身的required属性
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
      'int': 'integer',
      'bigint': 'integer',
      'float': 'float',
      'double': 'float',
      'decimal': 'float',
      'boolean': 'boolean',
      'bool': 'boolean',
      'bit': 'boolean',
      'date': 'date',
      'datetime': 'datetime',
      'timestamp': 'datetime',
      'time': 'string',
      'json': 'object',
      'jsonb': 'object',
      'array': 'array'
    };
    return typeMap[dataType?.toLowerCase()] || 'string';
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

  const isModel = element.type === 'business_model';
  const isAction = element.type === 'action';

  return (
    <div style={{ 
      width: '400px', 
      borderLeft: '1px solid #E2E8F0', 
      background: '#FFFFFF', 
      display: 'flex',
      flexDirection: 'column',
      height: '100%'
    }}>
      <div style={{ 
        padding: '16px 20px', 
        borderBottom: '1px solid #E2E8F0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
          {isAction ? '行动属性' : isModel ? '业务模型属性' : '模型关系属性'}
        </h3>
        <Button type="link" onClick={() => {
          setIsEdit(!isEdit);
          if (!isEdit) {
            setCurrentStep(0);
          }
        }}>
          {isEdit ? '取消编辑' : '编辑'}
        </Button>
      </div>

      <div style={{ padding: '20px', flex: 1, overflowY: 'auto' }}>
        <Form 
          form={form} 
          layout="vertical"
          initialValues={element.data.data}
        >
          {isAction ? (
            // 行动属性 - 垂直滚动布局
            <>
              <Divider>基础配置</Divider>
              <Form.Item name="id" label="行动ID">
                <Input disabled />
              </Form.Item>
              <Form.Item name="api_name" label="API名称">
                <Input disabled />
              </Form.Item>
              <Form.Item
                name="name"
                label="名称"
                rules={[{ required: true, message: '请输入名称' }]}
              >
                <Input disabled={!isEdit} />
              </Form.Item>
              <Form.Item name="description" label="说明">
                <Input.TextArea disabled={!isEdit} />
              </Form.Item>
              
              <Divider>行动类型</Divider>
              <Form.Item name="action_type" label="行动类型" rules={[{ required: true, message: '请选择行动类型' }]}>
                <Select disabled={!isEdit} onChange={(value) => {
                  if (isEdit) {
                    // 清除相关字段
                    if (value === 'object') {
                      form.setFieldsValue({ 
                        operation: undefined, 
                        target_model_id: undefined, 
                        target_link_id: undefined,
                        function_code: undefined,
                        parameters: []
                      });
                    } else if (value === 'link') {
                      form.setFieldsValue({ 
                        operation: undefined, 
                        target_model_id: undefined, 
                        target_link_id: undefined,
                        function_code: undefined,
                        parameters: []
                      });
                    } else if (value === 'function') {
                      form.setFieldsValue({ 
                        operation: undefined, 
                        target_model_id: undefined, 
                        target_link_id: undefined,
                        parameters: []
                      });
                    }
                  }
                }}>
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
                  const actionType = getFieldValue('action_type');
                  
                  if (actionType === 'object') {
                    return (
                      <>
                        <Form.Item name="operation" label="操作" rules={[{ required: true, message: '请选择操作' }]}>
                          <Select disabled={!isEdit} onChange={(value) => {
                            if (isEdit) {
                              form.setFieldsValue({ target_model_id: undefined });
                              // 清除参数
                              form.setFieldsValue({ parameters: [] });
                            }
                          }}>
                            <Option value="create_object">创建对象</Option>
                            <Option value="update_object">更新对象</Option>
                            <Option value="delete_object">删除对象</Option>
                          </Select>
                        </Form.Item>
                        <Form.Item name="target_model_id" label="目标模型" rules={[{ required: true, message: '请选择目标模型' }]}>
                          <Select disabled={!isEdit} onChange={(value) => {
                            if (isEdit) {
                              const selectedModel = businessModels.find(m => m.id === value);
                              const operation = getFieldValue('operation');
                              if (selectedModel && operation) {
                                const params = generateObjectParameters(selectedModel, operation);
                                form.setFieldsValue({ parameters: params });
                              }
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
                    );
                  }
                  
                  if (actionType === 'link') {
                    // 过滤出多对多关系
                    const manyToManyLinks = modelLinks.filter(link => link.cardinality === 'many-to-many');
                    
                    return (
                      <>
                        <Form.Item name="operation" label="操作" rules={[{ required: true, message: '请选择操作' }]}>
                          <Select disabled={!isEdit} onChange={(value) => {
                            if (isEdit) {
                              form.setFieldsValue({ target_link_id: undefined });
                              // 清除参数
                              form.setFieldsValue({ parameters: [] });
                            }
                          }}>
                            <Option value="create_link">创建关系</Option>
                            <Option value="delete_link">删除关系</Option>
                          </Select>
                        </Form.Item>
                        <Form.Item name="target_link_id" label="目标关系" rules={[{ required: true, message: '请选择目标关系' }]}>
                          <Select disabled={!isEdit} onChange={(value) => {
                            if (isEdit) {
                              const selectedLink = modelLinks.find(l => l.id === value);
                              const operation = getFieldValue('operation');
                              if (selectedLink && operation) {
                                const params = generateLinkParameters(selectedLink, operation);
                                form.setFieldsValue({ parameters: params });
                              }
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
                    );
                  }
                  
                  if (actionType === 'function') {
                    return (
                      <Form.Item name="function_code" label="函数代码" rules={[{ required: true, message: '请输入函数代码' }]}>
                        <Input.TextArea 
                          disabled={!isEdit} 
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
                    );
                  }
                  
                  return null;
                }}
              </Form.Item>
              
              <Divider>参数配置</Divider>
              <Form.Item name="parameters" label="参数列表">
                {isEdit ? (
                  <ParameterEditorForPropertyPanel 
                    value={form.getFieldValue('parameters') || []}
                    onChange={(value) => form.setFieldsValue({ parameters: value })}
                  />
                ) : (
                  <List
                    dataSource={form.getFieldValue('parameters') || []}
                    renderItem={(param, index) => (
                      <List.Item>
                        <Card size="small" style={{ width: '100%' }}>
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <Typography.Text strong>参数 {index + 1}</Typography.Text>
                            <Typography.Text type="secondary">名称: {param.name}</Typography.Text>
                            <Typography.Text type="secondary">类型: {param.type}</Typography.Text>
                            <Typography.Text type="secondary">必填: {param.required ? '是' : '否'}</Typography.Text>
                            {param.description && (
                              <Typography.Text type="secondary">说明: {param.description}</Typography.Text>
                            )}
                          </Space>
                        </Card>
                      </List.Item>
                    )}
                  />
                )}
              </Form.Item>
              
              <Divider>提交条件</Divider>
              <Form.Item name="submission_criteria" label="条件列表">
                {isEdit ? (
                  <CriteriaEditorForPropertyPanel 
                    value={form.getFieldValue('submission_criteria') || []}
                    onChange={(value) => form.setFieldsValue({ submission_criteria: value })}
                  />
                ) : (
                  <List
                    dataSource={form.getFieldValue('submission_criteria') || []}
                    renderItem={(criterion, index) => (
                      <List.Item>
                        <Card size="small" style={{ width: '100%' }}>
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <Typography.Text strong>条件 {index + 1}</Typography.Text>
                            <Typography.Text type="secondary">类型: {criterion.type}</Typography.Text>
                            {criterion.field_name && (
                              <Typography.Text type="secondary">字段: {criterion.field_name}</Typography.Text>
                            )}
                            {criterion.rule && (
                              <Typography.Text type="secondary">规则: {criterion.rule}</Typography.Text>
                            )}
                            {criterion.expression && (
                              <Typography.Text type="secondary">表达式: {criterion.expression}</Typography.Text>
                            )}
                            {criterion.description && (
                              <Typography.Text type="secondary">说明: {criterion.description}</Typography.Text>
                            )}
                          </Space>
                        </Card>
                      </List.Item>
                    )}
                  />
                )}
              </Form.Item>
            </>
          ) : isModel ? (
            // 业务模型属性
            <>
              <Form.Item name="id" label="模型ID">
                <Input disabled />
              </Form.Item>
              <Form.Item name="api_name" label="API名称">
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
              
              {/* 字段列表 */}
              {isModel && (
                <div style={{ marginTop: '16px', border: '1px solid #d9d9d9', borderRadius: '4px' }}>
                  <div 
                    style={{ 
                      padding: '8px 12px', 
                      backgroundColor: '#f5f5f5', 
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <span>字段列表 ({fields.length} 个字段)</span>
                    <Button 
                      type="link" 
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddField && onAddField(element.data.id);
                      }}
                      disabled={!isEdit}
                    >
                      + 添加字段
                    </Button>
                  </div>
                  
                  <div style={{ padding: '12px', maxHeight: '300px', overflowY: 'auto' }}>
                    {fields.map((field) => (
                      <div 
                        key={field.field_id}
                        style={{ 
                          padding: '8px', 
                          marginBottom: '8px', 
                          border: '1px solid #e8e8e8', 
                          borderRadius: '4px',
                          backgroundColor: field.field_id === primaryKeyId ? '#fffbe6' : 'white'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <strong>
                              {field.required && <span style={{ color: 'red', marginRight: '4px' }}>*</span>}
                              {field.name}
                            </strong>
                            {field.field_id === primaryKeyId && (
                              <span style={{ 
                                marginLeft: '8px', 
                                backgroundColor: '#ffe58f', 
                                color: '#595959', 
                                padding: '2px 6px', 
                                borderRadius: '4px', 
                                fontSize: '12px'
                              }}>
                                主键
                              </span>
                            )}
                            <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
                              ID: {field.field_id} | 类型: {field.data_type}
                            </div>
                            {field.description && (
                              <div style={{ fontSize: '12px', color: '#595959', marginTop: '4px' }}>
                                {field.description}
                              </div>
                            )}
                          </div>
                          <div>
                            <Button 
                              type="link" 
                              size="small"
                              onClick={() => onEditField && onEditField(element.data.id, field)}
                              disabled={!isEdit}
                            >
                              编辑
                            </Button>
                            <Popconfirm
                              title="确定要删除这个字段吗？"
                              onConfirm={() => onDeleteField && onDeleteField(element.data.id, field.field_id)}
                              okText="确定"
                              cancelText="取消"
                              disabled={!isEdit}
                            >
                              <Button type="link" size="small" danger disabled={!isEdit}>
                                删除
                              </Button>
                            </Popconfirm>
                          </div>
                        </div>
                      </div>
                    ))}
                    {fields.length === 0 && (
                      <div style={{ textAlign: 'center', color: '#8c8c8c', padding: '16px' }}>
                        暂无字段
                      </div>
                    )}
                  </div>
                </div>
              )}
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
                          <Form.Item name="source_api_name" label="源API名称">
                            <Input disabled />
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
                          // 自动更新API名称字段
                          if (isEdit && sourceModelId) {
                            const newTargetApiName = `get${toPascalCase(sourceModelId)}`;
                            setFieldsValue({
                              target_api_name: newTargetApiName
                            });
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
                          <Form.Item name="target_api_name" label="目标API名称">
                            <Input disabled />
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
                          // 自动更新API名称字段
                          if (isEdit && targetModelId) {
                            const newSourceApiName = `get${toPascalCase(targetModelId)}`;
                            setFieldsValue({
                              source_api_name: newSourceApiName
                            });
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
                          <Form.Item name="source_api_name" label="源API名称">
                            <Input disabled />
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
                              
                              // 自动更新API名称字段
                              if (isEdit && sourceModelId) {
                                const newTargetApiName = `get${toPascalCase(sourceModelId)}`;
                                setFieldsValue({ 
                                  target_api_name: newTargetApiName
                                });
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
                          <Form.Item name="target_api_name" label="目标API名称">
                            <Input disabled />
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
                              
                              // 自动更新API名称字段
                              if (isEdit && targetModelId) {
                                const newSourceApiName = `get${toPascalCase(targetModelId)}`;
                                setFieldsValue({ 
                                  source_api_name: newSourceApiName
                                });
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
        {(
          <Popconfirm
            title={`确定要删除该${isAction ? '行动' : isModel ? '业务模型' : '模型关系'}吗？`}
            onConfirm={handleDeleteConfirm}
            okText="确认"
            cancelText="取消"
          >
            <Button danger>
              删除
            </Button>
          </Popconfirm>
        )}
      </div>
    </div>
  );
};

// 参数编辑器组件（用于属性面板）
const ParameterEditorForPropertyPanel = ({ value = [], onChange }) => {
  // 确保 value 始终是数组
  const safeValue = Array.isArray(value) ? value : [];
  const [parameters, setParameters] = useState(safeValue)

  useEffect(() => {
    const safeValue = Array.isArray(value) ? value : [];
    setParameters(safeValue)
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

// 提交条件编辑器组件（用于属性面板）
const CriteriaEditorForPropertyPanel = ({ value = [], onChange }) => {
  // 确保 value 始终是数组
  const safeValue = Array.isArray(value) ? value : [];
  const [criteria, setCriteria] = useState(safeValue)

  useEffect(() => {
    const safeValue = Array.isArray(value) ? value : [];
    setCriteria(safeValue)
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

export default PropertyPanel;
