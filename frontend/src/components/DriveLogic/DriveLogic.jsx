import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Popconfirm, Tooltip, Tag, Card } from 'antd'
import { ThunderboltOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { driveLogicApi, dataSensingApi, actionApi } from '../../services/api'

const { Option } = Select

function DriveLogic() {
  const [logics, setLogics] = useState([])
  const [actions, setActions] = useState([])
  const [sensingConfigs, setSensingConfigs] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)

  const [editingLogic, setEditingLogic] = useState(null)
  const [selectedType, setSelectedType] = useState('first_order')
  const [form] = Form.useForm()
  const [showAILogicModal, setShowAILogicModal] = useState(false)
  const [aiInput, setAiInput] = useState('')

  useEffect(() => {
    fetchLogics()
    fetchActions()
    fetchSensingConfigs()
  }, [])

  const fetchLogics = async () => {
    setLoading(true)
    try {
      const response = await driveLogicApi.getAll()
      setLogics(response.data)
    } catch (error) {
      console.error('获取驱动逻辑失败:', error);
      message.error('获取驱动逻辑失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchActions = async () => {
    try {
      const response = await actionApi.getAll()
      setActions(response.data)
    } catch (error) {
      console.error('获取行动失败:', error);
      message.error('获取行动失败')
    }
  }

  const fetchSensingConfigs = async () => {
    try {
      const response = await dataSensingApi.getAll()
      setSensingConfigs(response.data)
    } catch (error) {
      console.error('获取数据感知配置失败:', error);
      message.error('获取数据感知配置失败')
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
    
    if (record.action_ids && record.action_ids.length > 0) {
      formValues.action_ids = record.action_ids
    }
    
    form.setFieldsValue(formValues)
    setModalVisible(true)
  }

  const handleTypeChange = (value) => {
    setSelectedType(value)
    // 类型切换时清空关联行动的已选值
    form.setFieldsValue({ action_ids: undefined })
  }

  // 添加配置验证函数
  const isValidDriveLogic = (logic) => {
    if (!logic.name || !logic.type || !logic.config || !logic.event_ids || !logic.action_ids) {
      return false;
    }
    
    if (logic.type === 'first_order') {
      // first_order类型可以没有pre_condition
      return Array.isArray(logic.event_ids) && Array.isArray(logic.action_ids);
    } else if (logic.type === 'script') {
      return logic.config.script_content && Array.isArray(logic.event_ids) && Array.isArray(logic.action_ids);
    }
    
    return true;
  };

  // AI智能生成处理函数
  const handleGenerateWithAI = async () => {
    if (!aiInput.trim()) {
      message.warning('请输入自然语言描述');
      return;
    }
    
    setLoading(true);
    try {
      const response = await driveLogicApi.parseDriveLogic(aiInput);
      if (response.data.success && response.data.logic) {
        const parsedLogic = response.data.logic;
        
        // 验证配置是否完整
        if (!isValidDriveLogic(parsedLogic)) {
          message.error('解析结果不完整，请尝试更明确的描述');
          return;
        }
        
        // 设置表单字段
        const formValues = {
          name: parsedLogic.name || '',
          type: parsedLogic.type || 'first_order',
          description: parsedLogic.description || '',
          event_ids: parsedLogic.event_ids || [],
          action_ids: parsedLogic.action_ids || []
        };
        
        // 根据类型设置配置字段
        if (parsedLogic.type === 'first_order') {
          formValues.pre_condition = parsedLogic.config?.pre_condition || '';
        } else if (parsedLogic.type === 'script') {
          formValues.script_content = parsedLogic.config?.script_content || '';
        }
        
        form.setFieldsValue(formValues);
        setSelectedType(parsedLogic.type || 'first_order');
        
        message.success('AI智能生成配置成功');
        setShowAILogicModal(false);
        setAiInput('');
      } else {
        message.error('生成失败，请参考以下示例：\n• 如果订单金额大于10000，则需要经理审批\n• 当温度异常时发送邮件通知\n• 计算风险评分并根据结果分配不同处理流程');
      }
    } catch (error) {
      console.error('生成失败:', error);
      message.error('生成失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await driveLogicApi.delete(id)
      message.success('删除成功')
      fetchLogics()
    } catch (error) {
      console.error('删除失败:', error);
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
      
      // 处理 action_ids
      let actionIds = values.action_ids || []
      if (!Array.isArray(actionIds)) {
        actionIds = actionIds ? [actionIds] : []
      }
      
      const logicData = {
        name: values.name,
        type: values.type,
        config: configObj,
        description: values.description,
        event_ids: values.event_ids || [],
        action_ids: actionIds
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
      console.error('操作失败:', error);
      message.error('操作失败')
    }
  }

  const logicColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => {
        const description = record.natural_language_description || '暂无自然语言描述';
        return (
          <Tooltip title={description} placement="top">
            <span style={{ cursor: 'help' }}>{name}</span>
          </Tooltip>
        );
      }
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        if (type === 'first_order') return <Tag color="blue">一阶函数</Tag>
        if (type === 'script') return <Tag color="green">脚本函数</Tag>
        return <Tag>{type}</Tag>
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
      title: '关联行动',
      dataIndex: 'action_ids',
      key: 'action_ids',
      render: (actionIds) => {
        if (!actionIds || actionIds.length === 0) return '-'
        return actionIds.map((actionId, idx) => {
          const action = actions.find(a => a.id === actionId);
          return <Tag key={idx} color="cyan">{action ? action.name : actionId}</Tag>;
        })
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
          <Button type="primary" size="small" icon={<EditOutlined />} style={{ marginRight: 8 }} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个驱动逻辑吗？"
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
    },
  ]

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>驱动逻辑配置</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加逻辑
        </Button>
      </div>

      <h3>驱动逻辑列表</h3>
      <Table columns={logicColumns} dataSource={logics} rowKey="id" loading={loading} />

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
            <Input 
              placeholder="例如：温度告警驱动逻辑"
              suffix={
                <Button 
                  type="text" 
                  icon={<ThunderboltOutlined style={{ color: '#faad14' }} />} 
                  onClick={() => setShowAILogicModal(true)}
                  title="AI智能生成配置"
                />
              }
            />
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
          
          <Form.Item name="action_ids" label="关联行动">
            <Select mode="multiple" placeholder="选择触发后要执行的行动">
              {actions.map(action => (
                <Option key={action.id} value={action.id}>
                  {action.name}
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

      {/* AI智能生成模态框 */}
      <Modal
        title="AI智能配置生成"
        open={showAILogicModal}
        onOk={handleGenerateWithAI}
        onCancel={() => setShowAILogicModal(false)}
        confirmLoading={loading}
      >
        <Input.TextArea 
          value={aiInput}
          onChange={(e) => setAiInput(e.target.value)}
          placeholder="例如：如果订单金额大于10000，则需要经理审批"
          rows={4}
        />
        <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
          支持的场景：
          <br/>• 一阶函数：&quot;如果订单金额大于10000，则需要经理审批&quot;
          <br/>• 脚本函数：&quot;计算风险评分并根据结果分配不同处理流程&quot;
        </div>
      </Modal>

    </div>
  )
}

export default DriveLogic