import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Card, Tag } from 'antd'
import { driveLogicApi, dataSensingApi, agentApi } from '../../services/api'

const { Option } = Select

function DriveLogic() {
  const [logics, setLogics] = useState([])
  const [tasks, setTasks] = useState([])
  const [sensingConfigs, setSensingConfigs] = useState([])
  const [agents, setAgents] = useState([])
  const [capabilities, setCapabilities] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [taskModalVisible, setTaskModalVisible] = useState(false)
  const [editingLogic, setEditingLogic] = useState(null)
  const [editingTask, setEditingTask] = useState(null)
  const [selectedType, setSelectedType] = useState('first_order')
  const [form] = Form.useForm()
  const [taskForm] = Form.useForm()

  useEffect(() => {
    fetchLogics()
    fetchTasks()
    fetchSensingConfigs()
    fetchAgents()
    fetchCapabilities()
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

  const fetchSensingConfigs = async () => {
    try {
      const response = await dataSensingApi.getAll()
      setSensingConfigs(response.data)
    } catch (error) {
      message.error('获取数据感知配置失败')
    }
  }

  const fetchAgents = async () => {
    try {
      const response = await agentApi.getAll()
      setAgents(response.data)
    } catch (error) {
      message.error('获取Agent失败')
    }
  }

  const fetchCapabilities = async () => {
    try {
      const response = await agentApi.getAllCapabilities()
      setCapabilities(response.data)
    } catch (error) {
      message.error('获取能力失败')
    }
  }

  const handleAdd = () => {
    setEditingLogic(null)
    setSelectedType('first_order')
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingLogic(record)
    setSelectedType(record.type)
    
    const formValues = {
      name: record.name,
      type: record.type,
      description: record.description,
    }
    
    if (record.type === 'first_order') {
      formValues.pre_condition = record.config?.pre_condition || ''
    } else if (record.type === 'script') {
      formValues.script_content = record.config?.script_content || ''
    }
    
    if (record.events && record.events.length > 0) {
      formValues.event_ids = record.events.map(e => e.id)
    }
    
    if (record.tasks && record.tasks.length > 0) {
      formValues.task_ids = record.tasks.map(t => t.id)
    }
    
    form.setFieldsValue(formValues)
    setModalVisible(true)
  }

  const handleTypeChange = (value) => {
    setSelectedType(value)
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
      let configObj = {}
      
      if (values.type === 'first_order') {
        configObj = {
          pre_condition: values.pre_condition || ''
        }
      } else if (values.type === 'script') {
        configObj = {
          script_content: values.script_content || ''
        }
      }
      
      const logicData = {
        name: values.name,
        type: values.type,
        config: configObj,
        description: values.description,
        event_ids: values.event_ids || [],
        task_ids: values.task_ids || []
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
      message.error('操作失败: ' + error.message)
    }
  }

  const handleAddTask = () => {
    setEditingTask(null)
    taskForm.resetFields()
    setTaskModalVisible(true)
  }

  const handleEditTask = (record) => {
    setEditingTask(record)
    // 深拷贝record对象
    const formValues = { ...record }
    // 将config对象转换为JSON字符串
    if (record.config) {
      formValues.config = JSON.stringify(record.config, null, 2)
    }
    taskForm.setFieldsValue(formValues)
    setTaskModalVisible(true)
  }

  const handleSubmitTask = async (values) => {
    try {
      const taskData = {
        name: values.name,
        capability_type: values.capability_type,
        config: values.config ? JSON.parse(values.config) : null,
        description: values.description
      }
      
      if (editingTask) {
        await driveLogicApi.updateTask(editingTask.id, taskData)
        message.success('任务更新成功')
      } else {
        await driveLogicApi.createTask(taskData)
        message.success('任务创建成功')
      }
      setTaskModalVisible(false)
      fetchTasks()
    } catch (error) {
      message.error('操作失败: ' + error.message)
    }
  }

  const handleDeleteTask = async (id) => {
    try {
      await driveLogicApi.deleteTask(id)
      message.success('任务删除成功')
      fetchTasks()
    } catch (error) {
      message.error('删除失败')
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
        return type === 'first_order' 
          ? <Tag color="blue">一阶函数</Tag> 
          : <Tag color="green">脚本函数</Tag>
      }
    },
    {
      title: '关联事件',
      dataIndex: 'events',
      key: 'events',
      render: (events) => {
        if (!events || events.length === 0) return '-'
        return events.map((e, idx) => (
          <Tag key={idx} color="purple">{e.name}</Tag>
        ))
      }
    },
    {
      title: '关联任务',
      dataIndex: 'tasks',
      key: 'tasks',
      render: (tasks) => {
        if (!tasks || tasks.length === 0) return '-'
        return tasks.map((t, idx) => (
          <Tag key={idx} color="cyan">{t.name}</Tag>
        ))
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
      title: '能力类型',
      dataIndex: 'capability_type',
      key: 'capability_type',
      render: (type) => <Tag color="blue">{type}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'completed' ? 'green' : status === 'failed' ? 'red' : 'orange'
        return <Tag color={color}>{status}</Tag>
      }
    },
    {
      title: '分配Agent',
      dataIndex: 'assigned_agent',
      key: 'assigned_agent',
      render: (agent) => agent ? agent.name : '-'
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
          <Button type="primary" size="small" style={{ marginRight: 8 }} onClick={() => handleEditTask(record)}>
            编辑
          </Button>
          <Button danger size="small" onClick={() => handleDeleteTask(record.id)}>
            删除
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>驱动逻辑配置</h2>
        <Button type="primary" onClick={handleAdd}>
          添加驱动逻辑
        </Button>
      </div>

      <h3>驱动逻辑列表</h3>
      <Table columns={logicColumns} dataSource={logics} rowKey="id" loading={loading} style={{ marginBottom: 24 }} />

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>任务列表</h3>
        <Button type="primary" onClick={handleAddTask}>
          添加任务
        </Button>
      </div>
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
            <Input placeholder="例如：温度告警驱动逻辑" />
          </Form.Item>
          
          <Form.Item name="type" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select onChange={handleTypeChange} placeholder="选择驱动逻辑类型">
              <Option value="first_order">
                <div>
                  <div><strong>一阶函数</strong></div>
                  <div style={{ fontSize: '12px', color: '#888' }}>简单的条件判断逻辑</div>
                </div>
              </Option>
              <Option value="script">
                <div>
                  <div><strong>脚本函数</strong></div>
                  <div style={{ fontSize: '12px', color: '#888' }}>使用Python脚本处理复杂逻辑</div>
                </div>
              </Option>
            </Select>
          </Form.Item>
          
          <Form.Item name="event_ids" label="关联数据感知事件">
            <Select mode="multiple" placeholder="选择触发此逻辑的数据感知事件">
              {sensingConfigs.map(config => (
                <Option key={config.id} value={config.id}>
                  {config.name} ({config.type === 'data_change' ? '数据变化' : '阈值触发'})
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item name="task_ids" label="关联任务">
            <Select mode="multiple" placeholder="选择触发后要执行的任务">
              {tasks.map(task => (
                <Option key={task.id} value={task.id}>
                  {task.name} (能力类型: {task.capability_type})
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          {/* 一阶函数可选预处理配置 */}
          {selectedType === 'first_order' && (
            <Card size="small" title="预处理配置 (可选)" style={{ marginBottom: 16 }}>
              <Form.Item name="pre_condition" label="前置条件">
                <Input.TextArea 
                  rows={2} 
                  placeholder="可选的前置处理条件表达式" 
                />
              </Form.Item>
            </Card>
          )}
          
          {/* 脚本函数可选预处理配置 */}
          {selectedType === 'script' && (
            <Card size="small" title="预处理脚本 (可选)" style={{ marginBottom: 16 }}>
              <Form.Item name="script_content" label="脚本内容">
                <Input.TextArea 
                  rows={4} 
                  placeholder="可选的预处理脚本，用于对事件数据进行处理" 
                />
              </Form.Item>
            </Card>
          )}
          
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="描述此驱动逻辑的作用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 任务模态框 */}
      <Modal
        title={editingTask ? '编辑任务' : '添加任务'}
        open={taskModalVisible}
        onOk={taskForm.submit}
        onCancel={() => setTaskModalVisible(false)}
        width={600}
      >
        <Form form={taskForm} layout="vertical" onFinish={handleSubmitTask}>
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="例如：发送温度告警通知" />
          </Form.Item>
          
          <Form.Item name="capability_type" label="能力类型" rules={[{ required: true, message: '请输入能力类型' }]}>
            <Select placeholder="选择任务需要的能力类型">
              {capabilities.map(cap => (
                <Option key={cap.id} value={cap.task_type}>
                  {cap.name} ({cap.task_type})
                </Option>
              ))}
              <Option value="notification">通知 (notification)</Option>
              <Option value="email">邮件 (email)</Option>
              <Option value="sms">短信 (sms)</Option>
              <Option value="webhook">Webhook (webhook)</Option>
              <Option value="data_process">数据处理 (data_process)</Option>
              <Option value="analysis">分析 (analysis)</Option>
            </Select>
          </Form.Item>
          
          <Form.Item name="config" label="任务配置 (JSON格式)">
            <Input.TextArea rows={4} placeholder='例如: {"recipient": "admin@example.com", "message": "温度异常"}' />
          </Form.Item>
          
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="描述此任务的作用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DriveLogic
