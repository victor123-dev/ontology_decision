import { useState, useEffect } from 'react'
import { Table, Button, Tag, message, Popconfirm, Card, Space, Select, Spin } from 'antd'
import { EyeOutlined, DeleteOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { orchestrationLogApi, orchestrationApi } from '../../services/api'

const { Option } = Select

function OrchestrationLog() {
  const { id: routeOrchestrationId } = useParams()
  const navigate = useNavigate()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })
  const [statusFilter, setStatusFilter] = useState(undefined)
  const [orchestrations, setOrchestrations] = useState([])
  const [selectedOrchestrationId, setSelectedOrchestrationId] = useState(routeOrchestrationId || undefined)

  useEffect(() => {
    fetchOrchestrations()
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [pagination.current, pagination.pageSize, statusFilter, selectedOrchestrationId])

  const fetchOrchestrations = async () => {
    try {
      const response = await orchestrationApi.getAll()
      setOrchestrations(response.data || [])
    } catch (error) {
      console.error('获取编排列表失败:', error)
    }
  }

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = {
        page: pagination.current,
        page_size: pagination.pageSize,
      }
      if (statusFilter) params.status = statusFilter
      if (selectedOrchestrationId) params.orchestration_id = selectedOrchestrationId
      const response = await orchestrationLogApi.getAll(params)
      const data = response.data
      setLogs(data.items || [])
      setPagination(prev => ({ ...prev, total: data.total || 0 }))
    } catch (error) {
      console.error('获取日志失败:', error)
      message.error('获取日志失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (logId) => {
    try {
      await orchestrationLogApi.delete(logId)
      message.success('删除成功')
      fetchLogs()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const formatDateTime = (str) => {
    if (!str) return '-'
    const d = new Date(str)
    if (isNaN(d.getTime())) return str
    return d.toLocaleString('zh-CN', { hour12: false })
  }

  const getDuration = (startedAt, finishedAt) => {
    if (!startedAt || !finishedAt) return '-'
    const start = new Date(startedAt)
    const end = new Date(finishedAt)
    const ms = end - start
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const statusTagMap = {
    success: <Tag color="green" icon={<CheckCircleOutlined />}>成功</Tag>,
    failed: <Tag color="red" icon={<CloseCircleOutlined />}>失败</Tag>,
    running: <Tag color="blue" icon={<Spin size="small" />}>运行中</Tag>,
  }

  const columns = [
    {
      title: '编排名称',
      dataIndex: 'orchestration_name',
      key: 'orchestration_name',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => statusTagMap[status] || <Tag>{status}</Tag>,
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 170,
      render: (t) => formatDateTime(t),
    },
    {
      title: '耗时',
      key: 'duration',
      width: 80,
      render: (_, record) => getDuration(record.started_at, record.finished_at),
    },
    {
      title: '入参',
      dataIndex: 'input_data',
      key: 'input_data',
      width: 200,
      ellipsis: true,
      render: (data) => {
        const str = JSON.stringify(data)
        return str.length > 50 ? str.substring(0, 50) + '...' : str
      },
    },
    {
      title: '错误信息',
      dataIndex: 'error',
      key: 'error',
      width: 200,
      ellipsis: true,
      render: (err) => err || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space size={4}>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/orchestration-log/${record.id}`)}>
            详情
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)} okText="确定" cancelText="取消">
            <Button type="link" danger size="small" icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto' }}>
      <Card
        title={<span style={{ fontSize: 16, fontWeight: 600 }}>逻辑编排执行日志</span>}
        extra={
          <Space>
            <Select
              placeholder="筛选编排"
              allowClear
              style={{ width: 200 }}
              value={selectedOrchestrationId}
              onChange={(val) => {
                setSelectedOrchestrationId(val)
                setPagination(prev => ({ ...prev, current: 1 }))
              }}
            >
              {orchestrations.map(o => (
                <Option key={o.id} value={o.id} title={o.description || ''}>{o.name}</Option>
              ))}
            </Select>
            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 120 }}
              value={statusFilter}
              onChange={(val) => {
                setStatusFilter(val)
                setPagination(prev => ({ ...prev, current: 1 }))
              }}
            >
              <Option value="success">成功</Option>
              <Option value="failed">失败</Option>
              <Option value="running">运行中</Option>
            </Select>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => setPagination({ current: page, pageSize, total: pagination.total }),
          }}
        />
      </Card>
    </div>
  )
}

export default OrchestrationLog
