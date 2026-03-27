import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Card, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { testDataApi, dataSourceApi } from '../../services/api'

const { Option } = Select

function TestData() {
  const [dataSources, setDataSources] = useState([])
  const [tables, setTables] = useState([])
  const [testData, setTestData] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedDataSource, setSelectedDataSource] = useState(null)
  const [selectedTable, setSelectedTable] = useState(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingRecord, setEditingRecord] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchDataSources()
  }, [])

  const fetchDataSources = async () => {
    try {
      const response = await dataSourceApi.getAll()
      setDataSources(response.data)
    } catch (error) {
      message.error('获取数据源失败')
    }
  }

  const handleDataSourceChange = async (value) => {
    setSelectedDataSource(value)
    setSelectedTable(null)
    setTestData([])
    try {
      const response = await dataSourceApi.getTables(value)
      setTables(response.data.tables)
    } catch (error) {
      message.error('获取表列表失败')
    }
  }

  const handleTableChange = async (value) => {
    setSelectedTable(value)
    // 直接传入 value 而不是依赖 selectedTable 状态
    if (selectedDataSource && value) {
      setLoading(true)
      try {
        const response = await testDataApi.get(selectedDataSource, value)
        setTestData(response.data.data)
      } catch (error) {
        message.error('获取测试数据失败')
      } finally {
        setLoading(false)
      }
    }
  }

  const fetchTestData = async () => {
    if (!selectedDataSource || !selectedTable) return
    
    setLoading(true)
    try {
      const response = await testDataApi.get(selectedDataSource, selectedTable)
      setTestData(response.data.data)
    } catch (error) {
      message.error('获取测试数据失败')
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
    if (!selectedDataSource || !selectedTable) {
      message.error('请先选择数据源和表')
      return
    }
    
    try {
      if (editingRecord) {
        // 编辑模式
        await testDataApi.update(selectedDataSource, selectedTable, values)
        message.success('数据更新成功')
      } else {
        // 新增模式
        await testDataApi.insert(selectedDataSource, selectedTable, values)
        message.success('数据添加成功')
      }
      setModalVisible(false)
      fetchTestData()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleDelete = async (record) => {
    if (!selectedDataSource || !selectedTable) {
      message.error('请先选择数据源和表')
      return
    }
    
    try {
      await testDataApi.delete(selectedDataSource, selectedTable, record)
      message.success('数据删除成功')
      fetchTestData()
    } catch (error) {
      message.error('操作失败')
    }
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>测试数据管理</h2>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <label style={{ marginRight: 8 }}>数据源:</label>
            <Select
              style={{ width: 200 }}
              value={selectedDataSource}
              onChange={handleDataSourceChange}
              placeholder="选择数据源"
            >
              {dataSources.map((ds) => (
                <Option key={ds.id} value={ds.id}>{ds.name}</Option>
              ))}
            </Select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ marginRight: 8 }}>表名:</label>
            <Select
              style={{ width: 200 }}
              value={selectedTable}
              onChange={handleTableChange}
              placeholder="选择表名"
              disabled={!selectedDataSource}
            >
              {tables.map((table) => (
                <Option key={table} value={table}>{table}</Option>
              ))}
            </Select>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddData} disabled={!selectedTable}>
            添加数据
          </Button>
        </div>
      </Card>

      {selectedTable && (
        <>
          <h3>{selectedTable} 数据</h3>
          <Table 
            dataSource={testData} 
            rowKey={(record, index) => index} 
            loading={loading}
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
        title={editingRecord ? `编辑 ${selectedTable} 数据` : `添加 ${selectedTable} 数据`}
        open={modalVisible}
        onOk={form.submit}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          {/* 动态生成表单字段 */}
          {testData.length > 0 && Object.keys(testData[0]).map(key => (
            <Form.Item key={key} name={key} label={key}>
              <Input />
            </Form.Item>
          ))}
        </Form>
      </Modal>
    </div>
  )
}

export default TestData
