import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message } from 'antd'
import { dataSensingApi, businessModelApi } from '../../services/api'

const { Option } = Select

function DataSensing() {
  const [configs, setConfigs] = useState([])
  const [businessModels, setBusinessModels] = useState([])
  const [modelFields, setModelFields] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingConfig, setEditingConfig] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchConfigs()
    fetchBusinessModels()
  }, [])

  const fetchConfigs = async () => {
    setLoading(true)
    try {
      const response = await dataSensingApi.getAll()
      setConfigs(response.data)
    } catch (error) {
      message.error('获取数据感知配置失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchBusinessModels = async () => {
    try {
      const response = await businessModelApi.getAll()
      setBusinessModels(response.data)
    } catch (error) {
      message.error('获取业务模型失败')
    }
  }

  const handleAdd = () => {
    setEditingConfig(null)
    form.resetFields()
    setModelFields([])
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingConfig(record)
    setSelectedType(record.type)
    
    // 处理配置数据，将 JSON 转换为表单字段
    const formValues = {
      ...record
    }
    
    // 根据类型设置相应的表单字段
    if (record.type === 'data_change') {
      formValues.trigger_conditions = record.config.trigger_conditions || []
      formValues.monitored_fields = record.config.monitored_fields || []
      formValues.check_interval = record.config.check_interval || 5
    } else if (record.type === 'threshold') {
      formValues.monitored_field = record.config.monitored_field || ''
      formValues.threshold_type = record.config.threshold_type || 'static'
      formValues.threshold_value = record.config.threshold_value
      formValues.threshold_field = record.config.threshold_field
      formValues.operator = record.config.operator || 'gt'
      formValues.check_interval = record.config.check_interval || 5
    }
    
    form.setFieldsValue(formValues)
    
    // 获取模型字段
    if (record.model_id) {
      const model = businessModels.find(m => m.id === record.model_id)
      if (model && model.fields) {
        setModelFields(model.fields)
      }
    }
    
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await dataSensingApi.delete(id)
      message.success('删除成功')
      fetchConfigs()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const [selectedType, setSelectedType] = useState('data_change')
  const thresholdType = Form.useWatch('threshold_type', form)

  const handleTypeChange = (value) => {
    setSelectedType(value)
  }

  const handleModelChange = (modelId) => {
    // 获取所选模型的字段
    const model = businessModels.find(m => m.id === modelId)
    if (model && model.fields) {
      setModelFields(model.fields)
    } else {
      setModelFields([])
    }
    // 重置字段相关的表单
    form.setFieldsValue({ 
      monitored_fields: [],
      monitored_field: '' 
    })
  }

  const handleSubmit = async (values) => {
    try {
      // 处理配置数据
      let configObj = {}
      
      if (values.type === 'data_change') {
        configObj = {
          trigger_conditions: values.trigger_conditions || [],
          monitored_fields: values.monitored_fields || [],
          check_interval: values.check_interval || 5
        }
      } else if (values.type === 'threshold') {
        configObj = {
          monitored_field: values.monitored_field || '',
          threshold_field: values.threshold_field,
          threshold_value: values.threshold_value,
          operator: values.operator || 'gt',
          check_interval: values.check_interval || 5,
          threshold_type: values.threshold_type || 'static'
        }
      }
      
      const configData = {
        ...values,
        config: configObj
      }
      
      if (editingConfig) {
        await dataSensingApi.update(editingConfig.id, configData)
        message.success('更新成功')
      } else {
        await dataSensingApi.create(configData)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchConfigs()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        return type === 'data_change' ? '数据变化感知' : '阈值触发感知'
      }
    },
    {
      title: '业务模型',
      dataIndex: 'model_id',
      key: 'model_id',
      render: (modelId) => {
        const model = businessModels.find(m => m.id === modelId)
        return model ? model.name : modelId
      }
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <div>
          <Button type="primary" size="small" style={{ marginRight: 8 }} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button danger size="small" onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>数据感知配置</h2>
        <Button type="primary" onClick={handleAdd}>
          添加配置
        </Button>
      </div>
      <Table columns={columns} dataSource={configs} rowKey="id" loading={loading} />

      <Modal
        title={editingConfig ? '编辑数据感知配置' : '添加数据感知配置'}
        open={modalVisible}
        onOk={form.submit}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select onChange={handleTypeChange}>
              <Option value="data_change">数据变化感知</Option>
              <Option value="threshold">阈值触发感知</Option>
            </Select>
          </Form.Item>
          <Form.Item name="model_id" label="业务模型" rules={[{ required: true, message: '请选择业务模型' }]}>
            <Select onChange={handleModelChange}>
              {businessModels.map((model) => (
                <Option key={model.id} value={model.id}>{model.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          {/* 数据变化感知配置 */}
          {selectedType === 'data_change' && (
            <div>
              <Form.Item name="trigger_conditions" label="触发条件" rules={[{ required: true, message: '请选择触发条件' }]}>
                <Select mode="multiple" placeholder="选择触发条件">
                  <Option value="create">新增</Option>
                  <Option value="update">更新</Option>
                  <Option value="delete">删除</Option>
                </Select>
              </Form.Item>
              <Form.Item name="monitored_fields" label="监控字段" rules={[{ required: true, message: '请选择监控字段' }]}>
                <Select mode="multiple" placeholder="选择监控字段">
                  {modelFields.map((field) => (
                    <Option key={field.field_id} value={field.field_id}>{field.name}</Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="check_interval" label="检查间隔 (秒)" initialValue={5}>
                <Input type="number" min={1} max={60} />
              </Form.Item>
            </div>
          )}
          
          {/* 阈值触发感知配置 */}
          {selectedType === 'threshold' && (
            <div>
              <Form.Item name="monitored_field" label="监控字段" rules={[{ required: true, message: '请选择监控字段' }]}>
                <Select placeholder="选择监控字段">
                  {modelFields.map((field) => (
                    <Option key={field.field_id} value={field.field_id}>{field.name}</Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="threshold_type" label="阈值类型" initialValue="static">
                <Select>
                  <Option value="static">固定阈值</Option>
                  <Option value="dynamic">动态阈值</Option>
                </Select>
              </Form.Item>
              {thresholdType === 'static' && (
                <Form.Item name="threshold_value" label="固定阈值" rules={[{ required: true, message: '请输入固定阈值' }]}>
                  <Input type="number" placeholder="例如: 100" />
                </Form.Item>
              )}
              {thresholdType === 'dynamic' && (
                <Form.Item name="threshold_field" label="阈值字段" rules={[{ required: true, message: '请选择阈值字段' }]}>
                  <Select placeholder="选择阈值字段">
                    {modelFields.map((field) => (
                      <Option key={field.field_id} value={field.field_id}>{field.name}</Option>
                    ))}
                  </Select>
                </Form.Item>
              )}
              <Form.Item name="operator" label="操作符" initialValue="gt">
                <Select>
                  <Option value="gt">大于</Option>
                  <Option value="lt">小于</Option>
                  <Option value="eq">等于</Option>
                  <Option value="ne">不等于</Option>
                  <Option value="gte">大于等于</Option>
                  <Option value="lte">小于等于</Option>
                </Select>
              </Form.Item>
              <Form.Item name="check_interval" label="检查间隔 (秒)" initialValue={5}>
                <Input type="number" min={1} max={60} />
              </Form.Item>
            </div>
          )}
          
          <Form.Item name="description" label="描述">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DataSensing
