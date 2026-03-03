import { useState, useEffect } from 'react'
import { Table, Button, Select, message, DatePicker, Input } from 'antd'
import { driveLogApi } from '../../services/api'

const { Option } = Select
const { RangePicker } = DatePicker
const { Search } = Input

function DriveLog() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    level: null,
    category: null,
    search: ''
  })

  useEffect(() => {
    fetchLogs()
  }, [filters])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.level) params.level = filters.level
      if (filters.category) params.category = filters.category
      if (filters.search) params.search = filters.search
      
      const response = await driveLogApi.getAll(params)
      setLogs(response.data)
    } catch (error) {
      message.error('获取驱动日志失败')
    } finally {
      setLoading(false)
    }
  }

  const handleLevelChange = (value) => {
    setFilters({ ...filters, level: value })
  }

  const handleCategoryChange = (value) => {
    setFilters({ ...filters, category: value })
  }

  const handleSearch = (value) => {
    setFilters({ ...filters, search: value })
  }

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
    },
    {
      title: '数据',
      dataIndex: 'data',
      key: 'data',
      render: (data) => {
        if (!data) return '-'
        return typeof data === 'object' ? JSON.stringify(data) : data
      }
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>驱动日志</h2>
      </div>

      <div style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
        <div>
          <label style={{ marginRight: 8 }}>级别:</label>
          <Select
            style={{ width: 120 }}
            value={filters.level}
            onChange={handleLevelChange}
            placeholder="选择级别"
            allowClear
          >
            <Option value="info">Info</Option>
            <Option value="warning">Warning</Option>
            <Option value="error">Error</Option>
          </Select>
        </div>
        <div>
          <label style={{ marginRight: 8 }}>分类:</label>
          <Select
            style={{ width: 150 }}
            value={filters.category}
            onChange={handleCategoryChange}
            placeholder="选择分类"
            allowClear
          >
            <Option value="data_sensing">数据感知</Option>
            <Option value="drive_logic">驱动逻辑</Option>
            <Option value="agent_task">Agent任务</Option>
          </Select>
        </div>
        <div style={{ flex: 1 }}>
          <Search
            placeholder="搜索消息"
            onSearch={handleSearch}
            style={{ width: 300 }}
          />
        </div>
      </div>

      <Table columns={columns} dataSource={logs} rowKey="id" loading={loading} />
    </div>
  )
}

export default DriveLog
