import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message } from 'antd'
import { dataSensingApi, businessModelApi } from '../../services/api'

const { Option } = Select

function DataSensing() {
  const [configs, setConfigs] = useState([])
  const [businessModels, setBusinessModels] = useState([])
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
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingConfig(record)
    form.setFieldsValue(record)
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

  const handleSubmit = async (values) => {
    try {
      // 处理配置数据
      const configData = {
        ...values,
        config: JSON.parse(values.config || '{}')
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
            <Select>
              <Option value="data_change">数据变化感知</Option>
              <Option value="threshold">阈值触发感知</Option>
            </Select>
          </Form.Item>
          <Form.Item name="model_id" label="业务模型" rules={[{ required: true, message: '请选择业务模型' }]}>
            <Select>
              {businessModels.map((model) => (
                <Option key={model.id} value={model.id}>{model.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="config" label="配置参数 (JSON格式)" rules={[{ required: true, message: '请输入配置参数' }]}>
            <Input.TextArea rows={4} placeholder='例如: {"trigger_conditions": ["create", "update", "delete"]}' />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DataSensing
