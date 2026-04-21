// import { useState, useEffect } from 'react'
// import { Table, Button, Modal, Form, Input, Select, message } from 'antd'
// import { dataSourceApi } from '../../services/api'

// const { Option } = Select

function DataSource() {
  // const [dataSources, setDataSources] = useState([])
  // const [loading, setLoading] = useState(false)
  // const [modalVisible, setModalVisible] = useState(false)
  // const [editingDataSource, setEditingDataSource] = useState(null)
  // const [form] = Form.useForm()

  // useEffect(() => {
  //   fetchDataSources()
  // }, [])

  // const fetchDataSources = async () => {
  //   setLoading(true)
  //   try {
  //     const response = await dataSourceApi.getAll()
  //     setDataSources(response.data)
  //   } catch (_error) {
  //     message.error('获取数据源失败')
  //   } finally {
  //     setLoading(false)
  //   }
  // }

  // const handleAdd = () => {
  //   setEditingDataSource(null)
  //   form.resetFields()
  //   setModalVisible(true)
  // }

  // const handleEdit = (record) => {
  //   setEditingDataSource(record)
  //   form.setFieldsValue(record)
  //   setModalVisible(true)
  // }

  // const handleDelete = async (id) => {
  //   try {
  //     await dataSourceApi.delete(id)
  //     message.success('删除成功')
  //     fetchDataSources()
  //   } catch (_error) {
  //     message.error('删除失败')
  //   }
  // }

  // const handleTestConnection = async (id) => {
  //   try {
  //     await dataSourceApi.testConnection(id)
  //     message.success('连接成功')
  //   } catch (_error) {
  //     message.error('连接失败')
  //   }
  // }

  // const handleSubmit = async (values) => {
  //   try {
  //     if (editingDataSource) {
  //       await dataSourceApi.update(editingDataSource.id, values)
  //       message.success('更新成功')
  //     } else {
  //       await dataSourceApi.create(values)
  //       message.success('创建成功')
  //     }
  //     setModalVisible(false)
  //     fetchDataSources()
  //   } catch (_error) {
  //     message.error('操作失败')
  //   }
  // }

  // const columns = [
  //   {
  //     title: '名称',
  //     dataIndex: 'name',
  //     key: 'name',
  //   },
  //   {
  //     title: '类型',
  //     dataIndex: 'type',
  //     key: 'type',
  //   },
  //   {
  //     title: '连接字符串',
  //     dataIndex: 'connection_string',
  //     key: 'connection_string',
  //   },
  //   {
  //     title: '描述',
  //     dataIndex: 'description',
  //     key: 'description',
  //   },
  //   {
  //     title: '操作',
  //     key: 'action',
  //     render: (_, record) => (
  //       <div>
  //         <Button type="primary" size="small" style={{ marginRight: 8 }} onClick={() => handleEdit(record)}>
  //           编辑
  //         </Button>
  //         <Button danger size="small" style={{ marginRight: 8 }} onClick={() => handleDelete(record.id)}>
  //           删除
  //         </Button>
  //         <Button size="small" onClick={() => handleTestConnection(record.id)}>
  //           测试连接
  //         </Button>
  //       </div>
  //     ),
  //   },
  // ]
  const token = import.meta.env.VITE_SSO_TOKEN || '';
  // 免密登录至采集设计页面
  const iframeUrl = `https://es-dcp-pre.digiwincloud.com.cn/#/login/sso?token=${token}&eid=DWDSE2026POC&projectId=121&sourceAppCode=DMP&routerLink=/collect-process-manage/collect-process-design/collection-design&pageMode=add&&accId=&&adcdId=&sourceEnv=dmp_dev`;
  // 免密登录至首页(无菜单)
  // const iframeUrl = `https://es-dcp-pre.digiwincloud.com.cn/#/login/sso?token=${token}&eid=DWDSE2026POC&projectId=121&sourceAppCode=DMP`;
  // 跳转至登录页(有菜单)
  // const iframeUrl = `https://es-dcp-pre.digiwincloud.com.cn/#/home`;
  return (
    <div style={{ width: '100%', height: '100%' }}>
      {/* 
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>数据采集</h2>
        <Button type="primary" onClick={handleAdd}>
          添加数据源
        </Button>
      </div>
      <Table columns={columns} dataSource={dataSources} rowKey="id" loading={loading} />

      <Modal
        title={editingDataSource ? '编辑数据源' : '添加数据源'}
        open={modalVisible}
        onOk={form.submit}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select>
              <Option value="sqlite">SQLite</Option>
              <Option value="mysql">MySQL</Option>
            </Select>
          </Form.Item>
          <Form.Item name="connection_string" label="连接字符串" rules={[{ required: true, message: '请输入连接字符串' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>
      */}
      
      {/* 嵌入外部数据管理页面 */}
      <iframe 
        id="dcdpIframe"
        src={iframeUrl} 
        style={{ 
          width: '100%', 
          height: 'calc(100vh - 64px)', // 减去顶部导航栏高度
          border: 'none',
          minHeight: '600px'
        }}
      />
    </div>
  )
}

export default DataSource
