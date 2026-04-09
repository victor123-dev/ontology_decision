import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Card, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { businessModelApi, businessDataApi } from '../../services/api'

const { Option } = Select

function BusinessData() {
  const [businessModels, setBusinessModels] = useState([])
  const [testData, setTestData] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedBusinessModel, setSelectedBusinessModel] = useState(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingRecord, setEditingRecord] = useState(null)
  const [form] = Form.useForm()
  
  // Pagination state
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  })

  useEffect(() => {
    fetchBusinessModels()
  }, [])

  const fetchBusinessModels = async () => {
    try {
      const response = await businessModelApi.getAll()
      setBusinessModels(response.data)
    } catch (_error) {
      message.error('获取业务模型失败')
    }
  }

  const handleBusinessModelChange = async (value) => {
    setSelectedBusinessModel(value)
    setTestData([])
    setPagination({ current: 1, pageSize: 10, total: 0 })
    if (value) {
      fetchTestData(value, 1, 10)
    }
  }

  const fetchTestData = async (modelId, page = 1, pageSize = 10) => {
    if (!modelId) return
    
    setLoading(true)
    try {
      const offset = (page - 1) * pageSize
      
      // 并行调用获取数据和总数
      const [dataResponse, countResponse] = await Promise.all([
        businessDataApi.getAll(modelId, pageSize, offset),
        businessDataApi.getCount(modelId)
      ])
      
      const data = dataResponse.data.data || []
      const totalCount = countResponse.data.count || 0
      
      setTestData(Array.isArray(data) ? data : [])
      setPagination(prev => ({
        ...prev,
        current: page,
        pageSize: pageSize,
        total: totalCount
      }))
    } catch (_error) {
      message.error('获取业务数据失败')
      setTestData([])
      setPagination(prev => ({ ...prev, total: 0 }))
    } finally {
      setLoading(false)
    }
  }

  const handleAddData = () => {
    form.resetFields()
    setEditingRecord(null)
    setModalVisible(true)
  }

  const handleEditData = (record) => {
    form.setFieldsValue(record)
    setEditingRecord(record)
    setModalVisible(true)
  }

  const handleSubmit = async (values) => {
    if (!selectedBusinessModel) {
      message.error('请先选择业务模型')
      return
    }
    
    try {
      if (editingRecord) {
        // 编辑模式 - need to get the primary key value
        // For now, assume the primary key is 'id' or find it from business model
        const primaryKeyValue = editingRecord.id || Object.values(editingRecord)[0]
        await businessDataApi.update(selectedBusinessModel, primaryKeyValue, values)
        message.success('数据更新成功')
      } else {
        // 新增模式
        await businessDataApi.create(selectedBusinessModel, values)
        message.success('数据添加成功')
      }
      setModalVisible(false)
      fetchTestData(selectedBusinessModel, pagination.current, pagination.pageSize)
    } catch (_error) {
      message.error('操作失败')
    }
  }

  const handleDelete = async (record) => {
    if (!selectedBusinessModel) {
      message.error('请先选择业务模型')
      return
    }
    
    try {
      // Need to get the primary key value for deletion
      const primaryKeyValue = record.id || Object.values(record)[0]
      await businessDataApi.delete(selectedBusinessModel, primaryKeyValue)
      message.success('数据删除成功')
      fetchTestData(selectedBusinessModel, pagination.current, pagination.pageSize)
    } catch (_error) {
      message.error('操作失败')
    }
  }

  const handleTableChange = (paginationConfig) => {
    const { current, pageSize } = paginationConfig
    fetchTestData(selectedBusinessModel, current, pageSize)
  }

  // Get selected business model details
  const selectedModel = businessModels.find(model => model.id === selectedBusinessModel)

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>业务数据管理</h2>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <label style={{ marginRight: 8 }}>业务模型:</label>
            <Select
              style={{ width: 300 }}
              value={selectedBusinessModel}
              onChange={handleBusinessModelChange}
              placeholder="选择业务模型"
            >
              {businessModels.map((model) => (
                <Option key={model.id} value={model.id}>{model.name} ({model.id})</Option>
              ))}
            </Select>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddData} disabled={!selectedBusinessModel}>
            添加数据
          </Button>
        </div>
      </Card>

      {selectedBusinessModel && (
        <>
          <h3>{selectedModel?.name || selectedBusinessModel} 数据</h3>
          <Table 
            dataSource={testData} 
            rowKey={(record, index) => record.id || index} 
            loading={loading}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showTotal: (total) => `共 ${total} 条`,
              onChange: (page, pageSize) => {
                handleTableChange({ current: page, pageSize })
              }
            }}
            columns={testData.length > 0 ? [
              ...Object.keys(testData[0]).map(key => ({
                title: key,
                dataIndex: key,
                key: key
              })),
              {
                title: '操作',
                key: 'action',
                render: (_, record) => (
                  <div>
                    <Button type="primary" size="small" icon={<EditOutlined />} style={{ marginRight: 8 }} onClick={() => handleEditData(record)}>
                      编辑
                    </Button>
                    <Popconfirm
                      title="确定要删除这条数据吗？"
                      onConfirm={() => handleDelete(record)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button danger size="small" icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  </div>
                )
              }
            ] : []}
          />
        </>
      )}
      
      <Modal
        title={editingRecord ? "编辑数据" : "添加数据"}
        open={modalVisible}
        onOk={() => form.submit()}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          {selectedBusinessModel && testData.length > 0 && Object.keys(testData[0]).map(key => (
            <Form.Item
              key={key}
              name={key}
              label={key}
              rules={[{ required: false }]}
            >
              <Input />
            </Form.Item>
          ))}
        </Form>
      </Modal>
    </div>
  )
}

export default BusinessData