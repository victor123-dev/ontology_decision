import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message } from 'antd'
import { driveLogicApi } from '../../services/api'

const { Option } = Select

function DriveLogic() {
  const [logics, setLogics] = useState([])
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [taskModalVisible, setTaskModalVisible] = useState(false)
  const [editingLogic, setEditingLogic] = useState(null)
  const [editingTask, setEditingTask] = useState(null)
  const [form] = Form.useForm()
  const [taskForm] = Form.useForm()

  useEffect(() => {
    fetchLogics()
    fetchTasks()
  }, [])

  const fetchLogics = async () => {
    setLoading(true)
    try {
      const response = await driveLogicApi.getAll()
      setLogics(response.data)
    } catch (error) {
      message.error('获取驱动逻辑失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchTasks = async () => {
    try {
      const response = await driveLogicApi.getAllTasks()
      setTasks(response.data)
    } catch (error) {
      message.error('获取任务失败')
    }
  }

  const handleAdd = () => {
    setEditingLogic(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingLogic(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await driveLogicApi.delete(id)
      message.success('删除成功')
      fetchLogics()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      // 处理配置数据
      const logicData = {
        ...values,
        config: JSON.parse(values.config || '{}')
      }
      
      if (editingLogic) {
        await driveLogicApi.update(editingLogic.id, logicData)
        message.success('更新成功')
      } else {
        await driveLogicApi.create(logicData)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchLogics()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleAddTask = () => {
    setEditingTask(null)
    taskForm.resetFields()
    setTaskModalVisible(true)
  }

  const handleSubmitTask = async (values) => {
    try {
      // 处理配置数据
      const taskData = {
        ...values,
        config: values.config ? JSON.parse(values.config) : null
      }
      
      await driveLogicApi.createTask(taskData)
      message.success('任务创建成功')
      setTaskModalVisible(false)
      fetchTasks()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const logicColumns = [
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
        return type === 'first_order' ? '一阶函数' : '脚本函数'
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

  const taskColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>驱动逻辑配置</h2>
        <div>
          <Button type="primary" style={{ marginRight: 8 }} onClick={handleAdd}>
            添加驱动逻辑
          </Button>
          <Button onClick={handleAddTask}>
            添加任务
          </Button>
        </div>
      </div>

      <h3>驱动逻辑列表</h3>
      <Table columns={logicColumns} dataSource={logics} rowKey="id" loading={loading} style={{ marginBottom: 24 }} />

      <h3>任务列表</h3>
      <Table columns={taskColumns} dataSource={tasks} rowKey="id" loading={loading} />

      {/* 驱动逻辑模态框 */}
      <Modal
        title={editingLogic ? '编辑驱动逻辑' : '添加驱动逻辑'}
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
              <Option value="first_order">一阶函数</Option>
              <Option value="script">脚本函数</Option>
            </Select>
          </Form.Item>
          <Form.Item name="config" label="配置参数 (JSON格式)" rules={[{ required: true, message: '请输入配置参数' }]}>
            <Input.TextArea rows={4} placeholder='例如: {"expression": "data.value > 100"}' />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>

      {/* 任务模态框 */}
      <Modal
        title="添加任务"
        open={taskModalVisible}
        onOk={taskForm.submit}
        onCancel={() => setTaskModalVisible(false)}
        width={600}
      >
        <Form form={taskForm} layout="vertical" onFinish={handleSubmitTask}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true, message: '请输入类型' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="config" label="配置参数 (JSON格式)">
            <Input.TextArea rows={4} placeholder='例如: {"target": "email", "recipient": "user@example.com"}' />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DriveLogic
