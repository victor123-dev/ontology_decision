import { useState, useEffect, useMemo } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Popconfirm, Card, Divider, InputNumber, Switch, Typography, Steps, Tabs, Space, List, Tag, Popover, DatePicker } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, MinusCircleOutlined } from '@ant-design/icons'
import { actionApi } from '../../services/api'
import { modelEventBus } from '../../utils/modelEventBus'
import { toPascalCase } from '../../utils/stringUtils';

const { Option } = Select
const { TextArea } = Input
const { Title, Text } = Typography
const { Step } = Steps
const { TabPane } = Tabs

function ActionManager({ businessModels, modelLinks }) {
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [executeModalVisible, setExecuteModalVisible] = useState(false)
  const [editingAction, setEditingAction] = useState(null)
  const [selectedAction, setSelectedAction] = useState(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [form] = Form.useForm()
  const [executeForm] = Form.useForm()
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState(null)

  useEffect(() => {
    fetchActions()
    
    // 订阅行动事件（用于双向同步）
    const handleActionCreated = ({ action }) => {
      setActions(prev => [...prev, action]);
    };
    
    const handleActionUpdated = ({ actionId, updatedFields }) => {
      setActions(prev => 
        prev.map(action => 
          action.id === actionId 
            ? { ...action, ...updatedFields }
            : action
        )
      );
    };
    
    const handleActionDeleted = ({ actionId }) => {
      setActions(prev => prev.filter(action => action.id !== actionId));
    };
    
    modelEventBus.on('action_created', handleActionCreated);
    modelEventBus.on('action_updated', handleActionUpdated);
    modelEventBus.on('action_deleted', handleActionDeleted);
    
    return () => {
      modelEventBus.off('action_created', handleActionCreated);
      modelEventBus.off('action_updated', handleActionUpdated);
      modelEventBus.off('action_deleted', handleActionDeleted);
    };
  }, [])

  const handleEdit = (record) => {
    setEditingAction(record)
    form.setFieldsValue({
      id: record.id,
      api_name: record.api_name,
      name: record.name,
      description: record.description,
      action_type: record.action_type,
      operation: record.operation,
      target_model_id: record.target_model_id,
      target_link_id: record.target_link_id,
      function_code: record.function_code,
      parameters: record.parameters || [],
      submission_criteria: record.submission_criteria || []
    })
    setCurrentStep(0)
    setModalVisible(true)
  }

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
          description: field.description || field.name + (isPrimaryKey ? ' (主键，必填)' : ''),
          is_enum: field.is_enum || false,
          enum_values: field.enum_values || null
        };
      });
    } else {
      // 创建操作包含所有字段，根据字段本身的required属性设置必填状态
      return model.fields.map(field => ({
        name: field.field_id,
        type: mapDataTypeToParamType(field.data_type),
        required: field.required || false, // 使用字段本身的required属性
        default_value: '',
        description: field.description || field.name,
        is_enum: field.is_enum || false,
        enum_values: field.enum_values || null
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
            required: field.required || false, // 使用字段本身的required属性
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
      form.setFieldsValue({ 
        operation: undefined, 
        target_model_id: undefined, 
        target_link_id: undefined,
        function_code: undefined,
        parameters: []
      })
    } else if (value === 'link') {
      form.setFieldsValue({ 
        operation: undefined, 
        target_model_id: undefined, 
        target_link_id: undefined,
        function_code: undefined,
        parameters: []
      })
    } else if (value === 'function') {
      form.setFieldsValue({ 
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
        await form.validateFields(['name'])
      } else if (currentStep === 1) {
        // 验证行动类型配置
        const actionType = form.getFieldValue('action_type')
        if (!actionType) {
          message.error('请选择行动类型')
          return
        }
        if (actionType === 'object') {
          await form.validateFields(['operation', 'target_model_id'])
        } else if (actionType === 'link') {
          await form.validateFields(['operation', 'target_link_id'])
        } else if (actionType === 'function') {
          await form.validateFields(['function_code'])
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

  const fetchActions = async () => {
    setLoading(true)
    try {
      const response = await actionApi.getAll()
      setActions(response.data)
    } catch (_error) {
      message.error('获取行动列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingAction(null)
    form.resetFields()
    setCurrentStep(0)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await actionApi.delete(id)
      message.success('删除成功')
      // 发布行动删除事件
      modelEventBus.emitActionDeleted(id)
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      // 处理参数的枚举值：确保逻辑一致性
      if (values.parameters && Array.isArray(values.parameters)) {
        values.parameters = values.parameters.map(param => {
          if (param.is_enum) {
            // 开启枚举时，枚举值必填
            if (!param.enum_values || param.enum_values.length === 0) {
              message.error(`参数 "${param.name || '未命名'}" 开启枚举时，必须至少输入一个枚举值`);
              throw new Error('枚举值必填');
            }
            return {
              ...param,
              enum_values: Array.isArray(param.enum_values) ? param.enum_values : []
            };
          } else {
            // 关闭枚举时，清空枚举值
            return {
              ...param,
              is_enum: false,
              enum_values: []
            };
          }
        });
      }
      
      if (editingAction) {
        await actionApi.update(editingAction.id, values)
        message.success('更新成功')
        // 发布行动更新事件
        modelEventBus.emitActionUpdated(editingAction.id, values)
      } else {
        const response = await actionApi.create(values)
        message.success('创建成功')
        // 发布行动创建事件
        modelEventBus.emitActionCreated(response.data)
      }
      setModalVisible(false)
    } catch (error) {
      if (error.message !== '枚举值必填') {
        console.error('Action submission error:', error)
        message.error('操作失败')
      }
    }
  }

  const handleExecute = (action) => {
    setSelectedAction(action)
    executeForm.resetFields()
    setExecutionResult(null)
    setExecuting(false)
    setExecuteModalVisible(true)
  }

  const handleExecuteSubmit = async (values) => {
    setExecuting(true)
    setExecutionResult(null)
    try {
      // 解析 array 和 object 类型的参数
      const parsedParameters = { ...values }
      if (selectedAction?.parameters) {
        selectedAction.parameters.forEach(param => {
          const value = parsedParameters[param.name]
          if (value && typeof value === 'string') {
            if (param.type === 'array' || param.type === 'object') {
              try {
                parsedParameters[param.name] = JSON.parse(value)
              } catch (e) {
                message.error(`参数 ${param.name} 的 JSON 格式不正确: ${e.message}`)
                setExecuting(false)
                return
              }
            }
          }
        })
      }

      const response = await actionApi.execute({
        action_id: selectedAction.id,
        parameters: parsedParameters
      })
      setExecutionResult(response.data)
      message.success('执行成功')
      console.log('Action execution result:', response.data)
    } catch (error) {
      setExecutionResult({ error: error.response?.data?.detail || error.message })
      message.error('执行失败')
    } finally {
      setExecuting(false)
    }
  }

  const getActionTypeLabel = (type) => {
    const labels = {
      'object': '对象行动',
      'link': '关系行动',
      'function': '函数行动'
    }
    return labels[type] || type
  }

  const getOperationLabel = (operation) => {
    const labels = {
      'create_object': '创建对象',
      'update_object': '更新对象',
      'delete_object': '删除对象',
      'create_link': '创建关系',
      'delete_link': '删除关系'
    }
    return labels[operation] || operation
  }

  const columns = [
    {
      title: '行动ID',
      dataIndex: 'id',
      key: 'id',
      width: 180,
    },
    {
      title: 'API名称',
      dataIndex: 'api_name',
      key: 'api_name',
      width: 150,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      width: 250,
    },
    {
      title: '类型',
      dataIndex: 'action_type',
      key: 'action_type',
      width: 100,
      render: getActionTypeLabel
    },
    {
      title: '操作',
      dataIndex: 'operation',
      key: 'operation',
      width: 100,
      render: (operation, record) => {
        if (record.action_type === 'function') {
          return '自定义函数'
        }
        return getOperationLabel(operation)
      }
    },
    {
      title: '目标',
      key: 'target',
      width: 150,
      render: (_, record) => {
        if (record.action_type === 'object' && record.target_model_id) {
          const model = businessModels.find(m => m.id === record.target_model_id)
          return model?.name || record.target_model_id
        }
        if (record.action_type === 'link' && record.target_link_id) {
          const link = modelLinks.find(l => l.id === record.target_link_id)
          return link?.name || record.target_link_id
        }
        return '-'
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <div>
          <Button 
            type="primary" 
            size="small" 
            icon={<PlayCircleOutlined />} 
            style={{ marginRight: 8 }} 
            onClick={() => handleExecute(record)}
          >
            执行
          </Button>
          <Button 
            type="primary" 
            size="small" 
            icon={<EditOutlined />} 
            style={{ marginRight: 8 }} 
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个行动吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </div>
      ),
      width: 220,
    },
  ]

  return (
    <div>
      <Card style={{ marginTop: 16 }}>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>行动列表</h3>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加行动
          </Button>
        </div>
        <Table 
          columns={columns} 
          dataSource={actions} 
          rowKey="id" 
          loading={loading}
        />
      </Card>

      {/* 创建/编辑行动模态框 */}
      <Modal
        title={editingAction ? '编辑行动' : '添加行动'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        width={900}
        footer={null}
        maskClosable={false}
      >
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title="基础配置" />
          <Step title="行动类型" />
          <Step title="参数配置" />
          <Step title="提交条件" />
        </Steps>
        
        <Form 
          form={form} 
          layout="vertical" 
          onFinish={handleSubmit}
        >
          {/* 所有表单字段都必须在Form内，即使被隐藏 */}
          
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
              <Input placeholder="例如: create_customer_order" disabled={editingAction} />
            </Form.Item>

            <Form.Item 
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.id !== currentValues.id}
            >
              {({ getFieldValue, setFieldsValue }) => {
                const actionId = getFieldValue('id');
                if (actionId && !editingAction) {
                  const apiName = toPascalCase(actionId);
                  setFieldsValue({ api_name: apiName });
                }
                return null;
              }}
            </Form.Item>

            <Form.Item name="api_name" label="API名称">
              <Input disabled />
            </Form.Item>

            <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
              <Input />
            </Form.Item>

            <Form.Item name="description" label="说明">
              <TextArea rows={3} />
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
                        form.setFieldsValue({ target_model_id: undefined });
                        // 清除参数
                        form.setFieldsValue({ parameters: [] });
                      }}>
                        <Option value="create_object">创建对象</Option>
                        <Option value="update_object">更新对象</Option>
                        <Option value="delete_object">删除对象</Option>
                      </Select>
                    </Form.Item>
                    <Form.Item name="target_model_id" label="目标模型" rules={[{ required: true, message: '请选择目标模型' }]}>
                      <Select onChange={(value) => {
                        const selectedModel = businessModels.find(m => m.id === value);
                        const operation = form.getFieldValue('operation');
                        if (selectedModel && operation) {
                          const params = generateObjectParameters(selectedModel, operation);
                          form.setFieldsValue({ parameters: params });
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
                        form.setFieldsValue({ target_link_id: undefined });
                        // 清除参数
                        form.setFieldsValue({ parameters: [] });
                      }}>
                        <Option value="create_link">创建关系</Option>
                        <Option value="delete_link">删除关系</Option>
                      </Select>
                    </Form.Item>
                    <Form.Item name="target_link_id" label="目标关系" rules={[{ required: true, message: '请选择目标关系' }]}>
                      <Select onChange={(value) => {
                        const selectedLink = modelLinks.find(l => l.id === value);
                        const operation = form.getFieldValue('operation');
                        if (selectedLink && operation) {
                          const params = generateLinkParameters(selectedLink, operation);
                          form.setFieldsValue({ parameters: params });
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
                      <TextArea 
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
              <Button type="primary" onClick={() => form.submit()}>
                {editingAction ? '更新' : '创建'}
              </Button>
            )}
          </div>
        </Form>
      </Modal>

      {/* 执行行动模态框 */}
      <Modal
        title={`执行行动: ${selectedAction?.name}`}
        open={executeModalVisible}
        onOk={executeForm.submit}
        onCancel={() => setExecuteModalVisible(false)}
        width={800}
        okText="执行"
        cancelText="关闭"
        okButtonProps={{ loading: executing }}
      >
        <Form form={executeForm} layout="vertical" onFinish={handleExecuteSubmit}>
          {selectedAction?.parameters?.map((param, index) => (
            <Form.Item
              key={index}
              name={param.name}
              label={param.name}
              rules={param.required ? [{ required: true, message: `${param.name} 是必填项` }] : []}
              initialValue={param.default_value}
              tooltip={param.description}
            >
              {param.is_enum && param.enum_values ? (
                <Select 
                  placeholder={`请选择${param.description || param.name}`}
                  allowClear
                  options={param.enum_values.map(val => ({ label: val, value: val }))}
                />
              ) : (
                <>
                  {param.type === 'string' && <Input placeholder={param.description} />}
                  {param.type === 'integer' && <InputNumber style={{ width: '100%' }} placeholder={param.description} />}
                  {param.type === 'float' && <InputNumber style={{ width: '100%' }} step={0.01} placeholder={param.description} />}
                  {param.type === 'boolean' && <Switch />}
                  {param.type === 'object' && <TextArea rows={4} placeholder={param.description} />}
                  {param.type === 'array' && <TextArea rows={4} placeholder={param.description} />}
                  {param.type === 'date' && <DatePicker format="YYYY-MM-DD" placeholder={param.description} />}
                  {param.type === 'datetime' && <DatePicker showTime format="YYYY-MM-DD HH:mm:ss" placeholder={param.description} />}
                </>
              )}
            </Form.Item>
          ))}
          {(!selectedAction?.parameters || selectedAction.parameters.length === 0) && (
            <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>
              此行动无需参数
            </div>
          )}
        </Form>

        {/* 执行结果显示区域 */}
        {executing && (
          <div style={{ marginTop: 24, textAlign: 'center', padding: '40px' }}>
            <div style={{ fontSize: '16px', color: '#1890ff', marginBottom: '16px' }}>
              正在执行中，请稍候...
            </div>
          </div>
        )}

        {executionResult && !executing && (
          <div style={{ marginTop: 24 }}>
            <Divider>执行结果</Divider>
            <Card 
              size="small" 
              style={{ 
                maxHeight: '400px', 
                overflow: 'auto',
                backgroundColor: executionResult.error ? '#fff2f0' : '#f6ffed',
                border: executionResult.error ? '1px solid #ffccc7' : '1px solid #b7eb8f'
              }}
            >
              <pre style={{ 
                margin: 0, 
                fontSize: '12px',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {JSON.stringify(executionResult, null, 2)}
              </pre>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  )
}

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
      description: '',
      is_enum: false,
      enum_values: []
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
              
              <Form.Item 
                label="是否为枚举" 
                valuePropName="checked"
              >
                <Switch
                  checked={param.is_enum || false}
                  onChange={(checked) => handleChange(index, 'is_enum', checked)}
                />
              </Form.Item>
              
              {param.is_enum && (
                <Form.Item label="枚举值">
                  <Select
                    mode="tags"
                    value={param.enum_values || []}
                    onChange={(value) => handleChange(index, 'enum_values', value)}
                    placeholder="输入枚举值后按回车"
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              )}
              
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

export default ActionManager
