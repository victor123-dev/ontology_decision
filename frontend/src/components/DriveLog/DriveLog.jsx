import { useState, useEffect } from 'react'
import { Table, Button, Select, message, Input, Card, Collapse, Tag } from 'antd'
import { driveLogApi } from '../../services/api'

const { Option } = Select
const { Search } = Input
const { Panel } = Collapse

function DriveLog() {
  const [logs, setLogs] = useState([])
  const [groupedLogs, setGroupedLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    level: null,
    search: ''
  })

  useEffect(() => {
    fetchLogs()
  }, [filters])

  useEffect(() => {
    // 按trace_id分组日志
    if (logs.length > 0) {
      const groups = {}
      logs.forEach(log => {
        if (!groups[log.trace_id]) {
          groups[log.trace_id] = []
        }
        groups[log.trace_id].push(log)
      })
      
      // 将分组转换为数组并按时间排序
      const sortedGroups = Object.values(groups).map(group => {
        // 按时间排序日志
        const sortedLogs = group.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
        // 获取最新的日志作为分组的代表
        const latestLog = sortedLogs[sortedLogs.length - 1]
        return {
          trace_id: group[0].trace_id,
          latest_time: latestLog.created_at,
          latest_message: latestLog.message,
          level: latestLog.level,
          logs: sortedLogs
        }
      }).sort((a, b) => new Date(b.latest_time) - new Date(a.latest_time))
      
      setGroupedLogs(sortedGroups)
    } else {
      setGroupedLogs([])
    }
  }, [logs])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.level) params.level = filters.level
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

  const handleSearch = (value) => {
    setFilters({ ...filters, search: value })
  }

  const getLevelColor = (level) => {
    switch (level) {
      case 'info': return 'green'
      case 'warning': return 'orange'
      case 'error': return 'red'
      default: return 'blue'
    }
  }

  const getCategoryText = (category) => {
    switch (category) {
      case 'data_sensing': return '数据感知'
      case 'drive_logic': return '驱动逻辑'
      case 'agent_task': return 'Agent任务'
      default: return category
    }
  }

  const formatDateTime = (dateTimeString) => {
    if (!dateTimeString) return ''
    const date = new Date(dateTimeString)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  }

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
        <div style={{ flex: 1 }}>
          <Search
            placeholder="搜索消息"
            onSearch={handleSearch}
            style={{ width: 300 }}
          />
        </div>
      </div>

      <Collapse
        items={groupedLogs.map((group) => ({
          key: group.trace_id,
          label: (
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <Tag color={getLevelColor(group.level)}>{group.level.toUpperCase()}</Tag>
              <span style={{ flex: 1, fontWeight: 'bold' }}>{group.latest_message}</span>
              <span>{formatDateTime(group.latest_time)}</span>
            </div>
          ),
          children: (
            <Card>
              {group.logs.map((log) => (
                <div key={log.id} style={{ marginBottom: 12, paddingBottom: 12, borderBottom: '1px solid #f0f0f0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                    <Tag color={getCategoryText(log.category)}>{getCategoryText(log.category)}</Tag>
                    <span style={{ fontSize: '12px', color: '#666' }}>{formatDateTime(log.created_at)}</span>
                  </div>
                  <div style={{ marginLeft: 12, marginBottom: 8 }}>
                    <strong>{log.message}</strong>
                  </div>
                  {log.data && (
                    <div style={{ marginLeft: 12, fontSize: '12px', backgroundColor: '#f9f9f9', padding: 8, borderRadius: 4, overflow: 'auto' }}>
                      <pre>{JSON.stringify(log.data, null, 2)}</pre>
                    </div>
                  )}
                </div>
              ))}
            </Card>
          ),
        }))}
      />

      {groupedLogs.length === 0 && !loading && (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          暂无日志记录
        </div>
      )}
    </div>
  )
}

export default DriveLog
