import { useState, useEffect, useMemo } from 'react'
import { Table, Button, Modal, Form, Input, Select, Radio, message, List, Popconfirm, Card, Divider, Tabs } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, ImportOutlined, LinkOutlined } from '@ant-design/icons'
import { businessModelApi, businessModelLinkApi, dataSourceApi } from '../../services/api'
import OntologyView from './OntologyView/OntologyView'

const { Option } = Select

function BusinessModel() {
  const [businessModels, setBusinessModels] = useState([])
  const [modelLinks, setModelLinks] = useState([])
  const [dataSources, setDataSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [linksLoading, setLinksLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [importModalVisible, setImportModalVisible] = useState(false)
  const [fieldModalVisible, setFieldModalVisible] = useState(false)
  const [linkModalVisible, setLinkModalVisible] = useState(false)
  const [editingModel, setEditingModel] = useState(null)
  const [editingField, setEditingField] = useState(null)
  const [editingLink, setEditingLink] = useState(null)
  const [form] = Form.useForm()
  const [importForm] = Form.useForm()
  const [fieldForm] = Form.useForm()
  const [linkForm] = Form.useForm()
  const [selectedDataSource, setSelectedDataSource] = useState(null)
  const [tables, setTables] = useState([])
  const [importLoading, setImportLoading] = useState(false)

  useEffect(() => {
    fetchBusinessModels()
    fetchModelLinks()
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
    } catch (_error) {
      message.error('获取业务模型失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchModelLinks = async () => {
    setLinksLoading(true)
    try {
      const response = await businessModelLinkApi.getAll()
      setModelLinks(response.data)
    } catch (error) {
      message.error('获取模型关系失败')
      setModelLinks([])
    } finally {
      setLinksLoading(false)
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
      setImportModalVisible(false)
      fetchBusinessModels()
      // 导入后重新获取关系（可能有新创建的关系）
      fetchModelLinks()
    } catch (error) {
      message.error('导入失败')
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
    }
  }

  // 关系管理相关函数
  const handleAddLink = () => {
    setEditingLink(null)
    linkForm.resetFields()
    // 设置默认基数关系值
    setTimeout(() => {
      linkForm.setFieldsValue({
        cardinality: 'one-to-many'
      });
    }, 0);
    setLinkModalVisible(true)
  }

  const handleEditLink = (link) => {
    setEditingLink(link)
    
    // 设置基数类型
    const formValues = { ...link };
    linkForm.setFieldsValue(formValues);
    setLinkModalVisible(true)
  }

  const handleDeleteLink = async (id) => {
    try {
      await businessModelLinkApi.delete(id)
      message.success('关系删除成功')
      fetchModelLinks()
    } catch (error) {
      message.error('删除关系失败')
    }
  }

  const handleSubmitLink = async (values) => {
    try {
      if (editingLink) {
        await businessModelLinkApi.update(editingLink.id, values)
        message.success('关系更新成功')
      } else {
        await businessModelLinkApi.create(values)
        message.success('关系创建成功')
      }
      setLinkModalVisible(false)
      fetchModelLinks()
    } catch (error) {
      message.error('操作失败')
    }
  }

  // 获取模型选项
  const getModelOptions = () => {
    return businessModels.map(model => (
      <Option key={model.id} value={model.id}>
        {model.name} ({model.id})
      </Option>
    ))
  }

  // 根据选择的模型获取字段选项
  const getFieldOptions = (modelId) => {
    
    const model = businessModels.find(m => m.id === modelId)
    if (!model) {
      return []
    }
    
    const fields = model.fields || [];
    
    return fields.map(field => (
      <Option key={field.field_id} value={field.field_id}>
        {field.name} ({field.field_id})
        {field.field_id === model.primary_key_id && ' [主键]'}
      </Option>
    ));
  }

  const columns = [
    {
      title: '模型ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
    },
    {
      title: '中文名称',
      dataIndex: 'name',
      key: 'name',
      width: 100,
    },
    {
      title: '中文说明',
      dataIndex: 'description',
      key: 'description',
      width: 250,
    },
    {
      title: '主键ID',
      dataIndex: 'primary_key_id',
      key: 'primary_key_id',
      width: 100,
    },
    {
      title: '字段数',
      dataIndex: 'fields',
      key: 'fields',
      render: (fields) => fields ? fields.length : 0,
      width: 40,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <div>
          <Button type="primary" size="small" icon={<EditOutlined />} style={{ marginRight: 8 }} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button size="small" style={{ marginRight: 8 }} onClick={() => handleEditField(record, null)}>
            编辑字段
          </Button>
          <Popconfirm
            title="确定要删除这个业务模型吗？"
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
      width: 180,
    },
  ];

  // 业务模型展开行的详细内容（显示字段信息）
  const expandedBusinessModelRowRender = (record) => {
    const fields = record.fields || [];
    
    if (fields.length === 0) {
      return <div style={{ padding: '16px', color: '#8c8c8c' }}>暂无字段信息</div>;
    }
    
    return (
      <div style={{ padding: '16px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
        <h4>字段列表 ({fields.length} 个字段)</h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
          {fields.map((field) => (
            <div key={field.field_id} style={{ 
              border: '1px solid #e8e8e8', 
              borderRadius: '4px', 
              padding: '12px',
              backgroundColor: 'white'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                {field.name}
                {field.field_id === record.primary_key_id && (
                  <span style={{ 
                    marginLeft: '8px', 
                    backgroundColor: '#ffe58f', 
                    color: '#595959', 
                    padding: '2px 6px', 
                    borderRadius: '4px', 
                    fontSize: '12px'
                  }}>
                    主键
                  </span>
                )}
              </div>
              <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>
                <strong>字段ID:</strong> {field.field_id}
              </div>
              <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>
                <strong>数据类型:</strong> {field.data_type}
              </div>
              {field.description && (
                <div style={{ fontSize: '12px', color: '#595959', whiteSpace: 'pre-wrap', lineHeight: 1.4 }}>
                  {field.description}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const linkColumns = [
    {
      title: '关系ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
    },
    {
      title: '关系名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: '关系',
      key: 'relationship',
      render: (_, record) => {
        const sourceModel = businessModels.find(m => m.id === record.source_model);
        const targetModel = businessModels.find(m => m.id === record.target_model);
        
        return (
          <span>
            {sourceModel?.name || record.source_model} → {targetModel?.name || record.target_model}
          </span>
        );
      },
      width: 200,
    },
    {
      title: '基数',
      dataIndex: 'cardinality',
      key: 'cardinality',
      render: (cardinality) => {
        const mapping = {
          'one-to-one': '一对一',
          'one-to-many': '一对多',
          'many-to-one': '多对一',
          'many-to-many': '多对多'
        };
        // 使用更直观的emoji图标
        const icons = {
          'one-to-one': '🔗',        // 链接图标，表示一对一连接
          'one-to-many': '➡️',       // 右箭头，表示一对多
          'many-to-one': '⬅️',       // 左箭头，表示多对一
          'many-to-many': '🔄'       // 循环图标，表示多对多关系
        };
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {icons[cardinality] && <span style={{ fontSize: '16px' }}>{icons[cardinality]}</span>}
            <span>{mapping[cardinality] || cardinality}</span>
          </span>
        );
      },
      width: 120,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <div>
          <Button type="primary" size="small" icon={<EditOutlined />} style={{ marginRight: 8 }} onClick={() => handleEditLink(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个关系吗？"
            onConfirm={() => handleDeleteLink(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </div>
      ),
      width: 120,
    },
  ];

  // 展开行的详细内容
  const expandedRowRender = (record) => {
    const sourceModel = businessModels.find(m => m.id === record.source_model);
    const targetModel = businessModels.find(m => m.id === record.target_model);
    const sourceField = sourceModel?.fields?.find(f => f.field_id === record.source_key);
    const targetField = targetModel?.fields?.find(f => f.field_id === record.target_key);
    const intermediateModel = businessModels.find(m => m.id === record.intermediate_model);
    const intermediateSourceField = intermediateModel?.fields?.find(f => f.field_id === record.intermediate_source_key);
    const intermediateTargetField = intermediateModel?.fields?.find(f => f.field_id === record.intermediate_target_key);
    
    // 判断是否为 many-to-many 关系
    const isManyToMany = record.cardinality === 'many-to-many';
    
    return (
      <div style={{ padding: '16px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
        {/* 关系详细信息 */}
        {record.description && (
          <div style={{ marginBottom: '16px' }}>
            <h4>关系说明</h4>
            <div style={{ 
              border: '1px solid #e8e8e8', 
              borderRadius: '4px', 
              padding: '12px',
              backgroundColor: 'white',
              fontSize: '13px', 
              color: '#595959', 
              whiteSpace: 'pre-wrap', 
              lineHeight: 1.5
            }}>
              {record.description}
            </div>
          </div>
        )}
        
        {/* 模型详情 - 动态布局 */}
        {isManyToMany ? (
          /* many-to-many 三栏布局 */
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {/* 源模型卡片 */}
            <div style={{ 
              border: '1px solid #e8e8e8', 
              borderRadius: '4px', 
              padding: '12px',
              backgroundColor: 'white'
            }}>
              <h4 style={{ marginBottom: '12px', color: '#1890ff' }}>源模型</h4>
              <div style={{ fontSize: '13px', lineHeight: 1.6 }}>
                <div><strong>模型名称:</strong> {sourceModel?.name || record.source_model}</div>
                <div><strong>模型ID:</strong> {record.source_model}</div>
                <div><strong>主键字段:</strong> {sourceField ? `${sourceField.name} (${record.source_key})` : record.source_key}</div>
                {sourceModel?.primary_key_id && (
                  <div><strong>主键:</strong> {sourceModel.primary_key_id}</div>
                )}
              </div>
            </div>
            
            {/* 中间模型卡片 */}
            <div style={{ 
              border: '1px solid #e8e8e8', 
              borderRadius: '4px', 
              padding: '12px',
              backgroundColor: 'white'
            }}>
              <h4 style={{ marginBottom: '12px', color: '#722ed1' }}>中间模型</h4>
              <div style={{ fontSize: '13px', lineHeight: 1.6 }}>
                <div><strong>模型名称:</strong> {intermediateModel?.name || record.intermediate_model}</div>
                <div><strong>模型ID:</strong> {record.intermediate_model}</div>
                <div><strong>→ 源模型字段:</strong> {intermediateSourceField ? `${intermediateSourceField.name} (${record.intermediate_source_key})` : record.intermediate_source_key}</div>
                <div><strong>→ 目标模型字段:</strong> {intermediateTargetField ? `${intermediateTargetField.name} (${record.intermediate_target_key})` : record.intermediate_target_key}</div>
              </div>
            </div>
            
            {/* 目标模型卡片 */}
            <div style={{ 
              border: '1px solid #e8e8e8', 
              borderRadius: '4px', 
              padding: '12px',
              backgroundColor: 'white'
            }}>
              <h4 style={{ marginBottom: '12px', color: '#1890ff' }}>目标模型</h4>
              <div style={{ fontSize: '13px', lineHeight: 1.6 }}>
                <div><strong>模型名称:</strong> {targetModel?.name || record.target_model}</div>
                <div><strong>模型ID:</strong> {record.target_model}</div>
                <div><strong>主键字段:</strong> {targetField ? `${targetField.name} (${record.target_key})` : record.target_key}</div>
                {targetModel?.primary_key_id && (
                  <div><strong>主键:</strong> {targetModel.primary_key_id}</div>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* 直接关系两栏布局 */
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
            {/* 源模型卡片 */}
            <div style={{ 
              border: '1px solid #e8e8e8', 
              borderRadius: '4px', 
              padding: '12px',
              backgroundColor: 'white'
            }}>
              <h4 style={{ marginBottom: '12px', color: '#1890ff' }}>源模型</h4>
              <div style={{ fontSize: '13px', lineHeight: 1.6 }}>
                <div><strong>模型名称:</strong> {sourceModel?.name || record.source_model}</div>
                <div><strong>模型ID:</strong> {record.source_model}</div>
                <div><strong>关联字段:</strong> {sourceField ? `${sourceField.name} (${record.source_key})` : record.source_key}</div>
                {sourceModel?.primary_key_id && (
                  <div><strong>主键:</strong> {sourceModel.primary_key_id}</div>
                )}
              </div>
            </div>
            
            {/* 目标模型卡片 */}
            <div style={{ 
              border: '1px solid #e8e8e8', 
              borderRadius: '4px', 
              padding: '12px',
              backgroundColor: 'white'
            }}>
              <h4 style={{ marginBottom: '12px', color: '#1890ff' }}>目标模型</h4>
              <div style={{ fontSize: '13px', lineHeight: 1.6 }}>
                <div><strong>模型名称:</strong> {targetModel?.name || record.target_model}</div>
                <div><strong>模型ID:</strong> {record.target_model}</div>
                <div><strong>关联字段:</strong> {targetField ? `${targetField.name} (${record.target_key})` : record.target_key}</div>
                {targetModel?.primary_key_id && (
                  <div><strong>主键:</strong> {targetModel.primary_key_id}</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Tabs
        defaultActiveKey="1"
        items={[
          {
            key: '1',
            label: '📋 业务模型',
            children: (
              <Card style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3>业务模型列表</h3>
                  <div>
                    <Button type="primary" icon={<PlusOutlined />} style={{ marginRight: 8 }} onClick={handleAdd}>
                      添加模型
                    </Button>
                    <Button icon={<ImportOutlined />} onClick={handleImportModal}>
                      导入模型
                    </Button>
                  </div>
                </div>
                <Table 
                  columns={columns} 
                  dataSource={businessModels} 
                  rowKey="id" 
                  loading={loading}
                  expandable={{
                    expandedRowRender: expandedBusinessModelRowRender,
                    rowExpandable: (record) => (record.fields && record.fields.length > 0),
                  }}
                />
              </Card>
            ),
          },
          {
            key: '2',
            label: '🔗 模型关系',
            children: (
              <Card style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3>模型关系列表</h3>
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleAddLink}>
                    添加关系
                  </Button>
                </div>
                <Table 
                  columns={linkColumns} 
                  dataSource={modelLinks} 
                  rowKey="id" 
                  loading={linksLoading}
                  expandable={{
                    expandedRowRender: expandedRowRender,
                    rowExpandable: (record) => true,
                  }}
                />
              </Card>
            ),
          },
          {
            key: '3',
            label: '🚀 行动管理',
            disabled: true,
            children: (
              <Card style={{ marginTop: 16 }}>
                <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                  行动管理功能正在开发中...
                </div>
              </Card>
            ),
          },
          {
            key: '4',
            label: '🧠 本体视图',
            children: (
              <div style={{ height: 'calc(100vh - 80px)' }}>
                <OntologyView />
              </div>
            ),
          },
        ]}
      />

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
                    description={
                      <div style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>
                        <div>字段ID: {field.field_id} | 数据类型: {field.data_type}</div>
                        <div>{field.description}</div>
                      </div>
                    }
                  />
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

      {/* 关系编辑模态框 */}
      <Modal
        title={editingLink ? '编辑模型关系' : '添加模型关系'}
        open={linkModalVisible}
        onOk={linkForm.submit}
        onCancel={() => setLinkModalVisible(false)}
        width={800}
        afterOpenChange={(open) => {
          if (open && !editingLink) {
            // 新建关系时设置默认值
            linkForm.setFieldsValue({
              cardinality: 'one-to-many'
            });
          }
        }}
      >
        <Form 
          form={linkForm} 
          layout="vertical" 
          onFinish={handleSubmitLink}
        >
          <Form.Item name="id" label="关系ID" rules={[{ required: true, message: '请输入关系ID' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="关系中文名称" rules={[{ required: true, message: '请输入关系中文名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="关系中文说明">
            <Input.TextArea />
          </Form.Item>
          
          {/* 基数关系选择 */}
          <Form.Item label="基数关系">
            <Form.Item name="cardinality" noStyle>
              <Radio.Group>
                <Radio value="one-to-one">一对一 (One-to-One)</Radio>
                <Radio value="one-to-many">一对多 (One-to-Many)</Radio>
                <Radio value="many-to-one">多对一 (Many-to-One)</Radio>
                <Radio value="many-to-many">多对多 (Many-to-Many)</Radio>
              </Radio.Group>
            </Form.Item>
          </Form.Item>
          
          {/* 模型选择 - 动态布局 */}
          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.cardinality !== currentValues.cardinality}>
            {({ getFieldValue }) => {
              const cardinality = getFieldValue('cardinality');
              const isManyToMany = cardinality === 'many-to-many';
              
              if (isManyToMany) {
                // 三栏布局：源模型 ←→ 中间表 ←→ 目标模型
                return (
                  <div style={{ display: 'flex', gap: '20px' }}>
                    {/* 源模型 */}
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="source_model" 
                        label="源模型" 
                        rules={[{ required: true, message: '请选择源模型' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.source_model !== currentValues.source_model
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue, setFieldsValue }) => {
                          const sourceModelId = innerGetFieldValue('source_model');
                          const sourceModel = businessModels.find(m => m.id === sourceModelId);
                          const primaryKey = sourceModel?.primary_key_id;
                          
                          // 多对多关系中，源字段必须使用主键
                          if (primaryKey) {
                            const currentSourceKey = innerGetFieldValue('source_key');
                            if (currentSourceKey !== primaryKey) {
                              setFieldsValue({ source_key: primaryKey });
                            }
                          }
                          
                          return (
                            <Form.Item 
                              name="source_key" 
                              label="源字段" 
                              rules={[{ required: true, message: '请选择源字段' }]}
                            >
                              <Select disabled>
                                {getFieldOptions(sourceModelId)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                    </div>
                    
                    {/* 中间表 */}
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="intermediate_model" 
                        label="中间表" 
                        rules={[{ required: true, message: '请选择中间表' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.intermediate_model !== currentValues.intermediate_model
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue }) => {
                          const intermediateModelId = innerGetFieldValue('intermediate_model');
                          return (
                            <>
                              <Form.Item 
                                name="intermediate_source_key" 
                                label="中间表→源模型字段" 
                                rules={[{ required: true, message: '请选择中间表到源模型的字段' }]}
                              >
                                <Select>
                                  {getFieldOptions(intermediateModelId)}
                                </Select>
                              </Form.Item>
                              
                              <Form.Item 
                                name="intermediate_target_key" 
                                label="中间表→目标模型字段" 
                                rules={[{ required: true, message: '请选择中间表到目标模型的字段' }]}
                              >
                                <Select>
                                  {getFieldOptions(intermediateModelId)}
                                </Select>
                              </Form.Item>
                            </>
                          );
                        }}
                      </Form.Item>
                    </div>
                    
                    {/* 目标模型 */}
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="target_model" 
                        label="目标模型" 
                        rules={[{ required: true, message: '请选择目标模型' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.target_model !== currentValues.target_model
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue, setFieldsValue }) => {
                          const targetModelId = innerGetFieldValue('target_model');
                          const targetModel = businessModels.find(m => m.id === targetModelId);
                          const primaryKey = targetModel?.primary_key_id;
                          
                          // 多对多关系中，目标字段必须使用主键
                          if (primaryKey) {
                            const currentTargetKey = innerGetFieldValue('target_key');
                            if (currentTargetKey !== primaryKey) {
                              setFieldsValue({ target_key: primaryKey });
                            }
                          }
                          
                          return (
                            <Form.Item 
                              name="target_key" 
                              label="目标字段" 
                              rules={[{ required: true, message: '请选择目标字段' }]}
                            >
                              <Select disabled>
                                {getFieldOptions(targetModelId)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                    </div>
                  </div>
                );
              } else {
                // 两栏布局：源模型 ←→ 目标模型
                return (
                  <div style={{ display: 'flex', gap: '20px' }}>
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="source_model" 
                        label="源模型" 
                        rules={[{ required: true, message: '请选择源模型' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.source_model !== currentValues.source_model ||
                          prevValues.cardinality !== currentValues.cardinality
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue, setFieldsValue }) => {
                          const sourceModelId = innerGetFieldValue('source_model');
                          const cardinality = innerGetFieldValue('cardinality');
                          
                          // 获取模型信息
                          const sourceModel = businessModels.find(m => m.id === sourceModelId);
                          const primaryKey = sourceModel?.primary_key_id;
                          
                          // 判断是否需要自动选择主键
                          let shouldAutoSelectPrimaryKey = false;
                          let shouldDisableField = false;

                          if (cardinality === 'one-to-many') {
                            // 一对多：源模型是"one"侧，必须使用主键
                            shouldAutoSelectPrimaryKey = true;
                            shouldDisableField = true;
                          } else if (cardinality === 'many-to-one') {
                            // 多对一：源模型是"many"侧，可以自由选择
                            shouldAutoSelectPrimaryKey = false;
                            shouldDisableField = false;
                          } else if (cardinality === 'one-to-one') {
                            // 一对一：可以自动选择主键但不禁用
                            shouldAutoSelectPrimaryKey = true;
                            shouldDisableField = false;
                          }
                          
                          // 自动选择主键
                          if (shouldAutoSelectPrimaryKey && primaryKey) {
                            const currentSourceKey = innerGetFieldValue('source_key');
                            if (currentSourceKey !== primaryKey) {
                              setFieldsValue({ source_key: primaryKey });
                            }
                          }
                          
                          return (
                            <Form.Item 
                              name="source_key" 
                              label="源字段" 
                              rules={[{ required: true, message: '请选择源字段' }]}
                            >
                              <Select disabled={shouldDisableField}>
                                {getFieldOptions(sourceModelId)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                    </div>
                    
                    <div style={{ flex: 1 }}>
                      <Form.Item 
                        name="target_model" 
                        label="目标模型" 
                        rules={[{ required: true, message: '请选择目标模型' }]}
                      >
                        <Select>
                          {getModelOptions()}
                        </Select>
                      </Form.Item>
                      
                      <Form.Item 
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => 
                          prevValues.target_model !== currentValues.target_model ||
                          prevValues.cardinality !== currentValues.cardinality
                        }
                      >
                        {({ getFieldValue: innerGetFieldValue, setFieldsValue }) => {
                          const targetModelId = innerGetFieldValue('target_model');
                          const cardinality = innerGetFieldValue('cardinality');
                          
                          // 获取模型信息
                          const targetModel = businessModels.find(m => m.id === targetModelId);
                          const primaryKey = targetModel?.primary_key_id;
                          
                          // 判断是否需要自动选择主键
                          let shouldAutoSelectPrimaryKey = false;
                          let shouldDisableField = false;
                          
                          if (cardinality === 'one-to-many') {
                            // 一对多：目标模型是"many"侧，可以自由选择
                            shouldAutoSelectPrimaryKey = false;
                            shouldDisableField = false;
                          } else if (cardinality === 'many-to-one') {
                            // 多对一：目标模型是"one"侧，必须使用主键
                            shouldAutoSelectPrimaryKey = true;
                            shouldDisableField = true;
                          } else if (cardinality === 'one-to-one') {
                            // 一对一：可以自动选择主键但不禁用
                            shouldAutoSelectPrimaryKey = true;
                            shouldDisableField = false;
                          }
                          
                          // 自动选择主键
                          if (shouldAutoSelectPrimaryKey && primaryKey) {
                            const currentTargetKey = innerGetFieldValue('target_key');
                            if (currentTargetKey !== primaryKey) {
                              setFieldsValue({ target_key: primaryKey });
                            }
                          }
                          
                          return (
                            <Form.Item 
                              name="target_key" 
                              label="目标字段" 
                              rules={[{ required: true, message: '请选择目标字段' }]}
                            >
                              <Select disabled={shouldDisableField}>
                                {getFieldOptions(targetModelId)}
                              </Select>
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                    </div>
                  </div>
                );
              }
            }}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default BusinessModel