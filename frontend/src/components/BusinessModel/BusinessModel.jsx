import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Card, List, Typography } from 'antd'
import { businessModelApi, dataSourceApi } from '../../services/api'

const { Option } = Select
const { Title, Text } = Typography

function BusinessModel() {
  const [businessModels, setBusinessModels] = useState([])
  const [dataSources, setDataSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [importModalVisible, setImportModalVisible] = useState(false)
  const [fieldModalVisible, setFieldModalVisible] = useState(false)
  const [editingModel, setEditingModel] = useState(null)
  const [editingField, setEditingField] = useState(null)
  const [form] = Form.useForm()
  const [importForm] = Form.useForm()
  const [fieldForm] = Form.useForm()
  const [selectedDataSource, setSelectedDataSource] = useState(null)
  const [tables, setTables] = useState([])
  const [importLoading, setImportLoading] = useState(false)

  useEffect(() => {
    fetchBusinessModels()
    fetchDataSources()
  }, [])

  const fetchBusinessModels = async () => {
    setLoading(true)
    try {
      const response = await businessModelApi.getAll()
      // 确保每个模型都有fields属性
      const modelsWithFields = response.data.map(model => ({
        ...model,
        fields: model.fields || []
      }))
      setBusinessModels(modelsWithFields)
    } catch (error) {
      message.error('获取业务模型失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchDataSources = async () => {
    try {
      const response = await dataSourceApi.getAll()
      setDataSources(response.data)
    } catch (error) {
      message.error('获取数据源失败')
    }
  }

  const handleAdd = () => {
    setEditingModel(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingModel(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await businessModelApi.delete(id)
      message.success('删除成功')
      fetchBusinessModels()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      if (editingModel) {
        await businessModelApi.update(editingModel.id, values)
        message.success('更新成功')
      } else {
        await businessModelApi.create(values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchBusinessModels()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleImportModal = () => {
    importForm.resetFields()
    setSelectedDataSource(null)
    setTables([])
    setImportModalVisible(true)
  }

  const handleDataSourceChange = async (value) => {
    setSelectedDataSource(value)
    try {
      const response = await dataSourceApi.getTables(value)
      setTables(response.data.tables)
    } catch (error) {
      message.error('获取表列表失败')
    }
  }

  const handleImport = async (values) => {
    setImportLoading(true)
    try {
      const response = await businessModelApi.import(values)
      message.success('导入成功')
      console.log('导入的模型:', response.data)
      setImportModalVisible(false)
      fetchBusinessModels()
    } catch (error) {
      message.error('导入失败')
      console.error('导入失败:', error)
    } finally {
      setImportLoading(false)
    }
  }

  const handleEditField = (model, field) => {
    setEditingModel(model)
    setEditingField(field)
    if (field) {
      fieldForm.setFieldsValue(field)
    }
    setFieldModalVisible(true)
  }

  const handleSubmitField = async (values) => {
    try {
      if (editingModel && editingField) {
        await businessModelApi.updateField(editingModel.id, editingField.field_id, values)
        message.success('字段更新成功')
        setFieldModalVisible(false)
        fetchBusinessModels()
      }
    } catch (error) {
      message.error('操作失败')
      console.error('字段更新失败:', error)
    }
  }

  const columns = [
    {
      title: '模型ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '中文名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '中文说明',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '主键ID',
      dataIndex: 'primary_key_id',
      key: 'primary_key_id',
    },
    {
      title: '字段数',
      dataIndex: 'fields',
      key: 'fields',
      render: (fields) => fields ? fields.length : 0,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <div>
          <Button type="primary" size="small" style={{ marginRight: 8 }} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button size="small" style={{ marginRight: 8 }} onClick={() => handleEditField(record, null)}>
            编辑字段
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
        <h2>业务模型管理</h2>
        <div>
          <Button type="primary" style={{ marginRight: 8 }} onClick={handleAdd}>
            添加模型
          </Button>
          <Button onClick={handleImportModal}>
            导入模型
          </Button>
        </div>
      </div>
      <Table columns={columns} dataSource={businessModels} rowKey="id" loading={loading} />

      {/* 编辑/添加模型模态框 */}
      <Modal
        title={editingModel ? '编辑业务模型' : '添加业务模型'}
        open={modalVisible}
        onOk={form.submit}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="id" label="模型ID" rules={[{ required: true, message: '请输入模型ID' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="中文名称" rules={[{ required: true, message: '请输入中文名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="中文说明">
            <Input.TextArea />
          </Form.Item>
          <Form.Item name="primary_key_id" label="主键ID">
            <Input />
          </Form.Item>
          <Form.Item name="data_source_id" label="数据源" rules={[{ required: true, message: '请选择数据源' }]}>
            <Select>
              {dataSources.map((ds) => (
                <Option key={ds.id} value={ds.id}>{ds.name}</Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 导入模型模态框 */}
      <Modal
        title="导入模型"
        open={importModalVisible}
        onOk={importForm.submit}
        onCancel={() => setImportModalVisible(false)}
        width={600}
        okButtonProps={{ loading: importLoading }}
        cancelButtonProps={{ disabled: importLoading }}
      >
        <Form form={importForm} layout="vertical" onFinish={handleImport}>
          <Form.Item name="data_source_id" label="数据源" rules={[{ required: true, message: '请选择数据源' }]}>
            <Select onChange={handleDataSourceChange}>
              {dataSources.map((ds) => (
                <Option key={ds.id} value={ds.id}>{ds.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="table_name" label="表名" rules={[{ required: true, message: '请选择表名' }]}>
            <Select>
              {tables.map((table) => (
                <Option key={table} value={table}>{table}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="model_id" label="模型ID (可选)">
            <Input placeholder="不填写则使用表名作为模型ID" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 字段编辑模态框 */}
      <Modal
        title={editingField ? '编辑字段' : '编辑模型字段'}
        open={fieldModalVisible}
        onOk={fieldForm.submit}
        onCancel={() => setFieldModalVisible(false)}
        width={600}
      >
        {editingModel && (
          <div>
            <h3>{editingModel.name} - 字段列表</h3>
            <List
              dataSource={editingModel.fields || []}
              renderItem={(field) => (
                <List.Item
                  actions={[
                    <Button key="edit" size="small" onClick={() => handleEditField(editingModel, field)}>
                      编辑
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={field.name}
                    description={`字段ID: ${field.field_id} | 数据类型: ${field.data_type}`}
                  />
                  <div>{field.description}</div>
                </List.Item>
              )}
            />

            {editingField && (
              <div style={{ marginTop: 24 }}>
                <h4>编辑字段</h4>
                <Form form={fieldForm} layout="vertical" onFinish={handleSubmitField}>
                  <Form.Item name="field_id" label="字段ID">
                    <Input disabled />
                  </Form.Item>
                  <Form.Item name="name" label="中文名称" rules={[{ required: true, message: '请输入中文名称' }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="data_type" label="数据类型">
                    <Input disabled />
                  </Form.Item>
                  <Form.Item name="description" label="中文说明">
                    <Input.TextArea />
                  </Form.Item>
                </Form>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default BusinessModel
