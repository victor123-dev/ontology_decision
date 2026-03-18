import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Tag } from 'antd'
import { agentApi } from '../../services/api'

const { Option } = Select

function Agent() {
  const [agents, setAgents] = useState([])
  const [capabilities, setCapabilities] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [capabilityModalVisible, setCapabilityModalVisible] = useState(false)
  const [editingAgent, setEditingAgent] = useState(null)
  const [editingCapability, setEditingCapability] = useState(null)
  const [form] = Form.useForm()
  const [capabilityForm] = Form.useForm()

  useEffect(() => {
    fetchAgents()
    fetchCapabilities()
  }, [])

  const fetchAgents = async () => {
    setLoading(true)
    try {
      const response = await agentApi.getAll()
      setAgents(response.data)
    } catch (error) {
      message.error('获取Agent失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchCapabilities = async () => {
    try {
      const response = await agentApi.getAllCapabilities()
      setCapabilities(response.data)
    } catch (error) {
      message.error('获取能力清单失败')
    }
  }

  const handleAdd = () => {
    setEditingAgent(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingAgent(record)
    const formValues = { ...record }
    // 将capabilities对象数组转换为ID数组
    if (record.capabilities && record.capabilities.length > 0) {
      formValues.capabilities = record.capabilities.map(cap => cap.id)
    }
    form.setFieldsValue(formValues)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await agentApi.delete(id)
      message.success('删除成功')
      fetchAgents()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      // 准备提交数据
      const agentData = { ...values }
      // 将capabilities ID数组重命名为capability_ids
      if (values.capabilities) {
        agentData.capability_ids = values.capabilities
        delete agentData.capabilities
      }
      
      if (editingAgent) {
        await agentApi.update(editingAgent.id, agentData)
        message.success('更新成功')
      } else {
        await agentApi.create(agentData)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchAgents()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleAddCapability = () => {
    setEditingCapability(null)
    capabilityForm.resetFields()
    setCapabilityModalVisible(true)
  }

  const handleEditCapability = (record) => {
    setEditingCapability(record)
    capabilityForm.setFieldsValue(record)
    setCapabilityModalVisible(true)
  }

  const handleDeleteCapability = async (id) => {
    try {
      await agentApi.deleteCapability(id)
      message.success('能力删除成功')
      fetchCapabilities()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmitCapability = async (values) => {
    try {
      if (editingCapability) {
        await agentApi.updateCapability(editingCapability.id, values)
        message.success('能力更新成功')
      } else {
        await agentApi.createCapability(values)
        message.success('能力创建成功')
      }
      setCapabilityModalVisible(false)
      fetchCapabilities()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const agentColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'green' : 'red'}>{status}</Tag>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '能力',
      dataIndex: 'capabilities',
      key: 'capabilities',
      render: (caps) => (
        <div>
          {caps && caps.map((cap) => (
            <Tag key={cap.id}>{cap.name}</Tag>
          ))}
        </div>
      )
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

  const capabilityColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
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
          <Button type="primary" size="small" style={{ marginRight: 8 }} onClick={() => handleEditCapability(record)}>
            编辑
          </Button>
          <Button danger size="small" onClick={() => handleDeleteCapability(record.id)}>
            删除
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Agent管理</h2>
        <Button type="primary" onClick={handleAdd}>
          添加Agent
        </Button>
      </div>

      <h3>Agent列表</h3>
      <Table columns={agentColumns} dataSource={agents} rowKey="id" loading={loading} style={{ marginBottom: 24 }} />

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>能力清单</h3>
        <Button type="primary" onClick={handleAddCapability}>
          添加能力
        </Button>
      </div>
      <Table columns={capabilityColumns} dataSource={capabilities} rowKey="id" loading={loading} />

      {/* Agent模态框 */}
      <Modal
        title={editingAgent ? '编辑Agent' : '添加Agent'}
        open={modalVisible}
        onOk={form.submit}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true, message: '请选择状态' }]}>
            <Select>
              <Option value="active">活跃</Option>
              <Option value="inactive">非活跃</Option>
            </Select>
          </Form.Item>
          <Form.Item name="capabilities" label="能力" rules={[{ required: true, message: '请选择能力' }]}>
            <Select mode="multiple" placeholder="选择Agent的能力">
              {capabilities.map((cap) => (
                <Option key={cap.id} value={cap.id}>{cap.name}</Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 能力模态框 */}
      <Modal
        title={editingCapability ? '编辑能力' : '添加能力'}
        open={capabilityModalVisible}
        onOk={capabilityForm.submit}
        onCancel={() => setCapabilityModalVisible(false)}
      >
        <Form form={capabilityForm} layout="vertical" onFinish={handleSubmitCapability}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>


    </div>
  )
}

export default Agent
