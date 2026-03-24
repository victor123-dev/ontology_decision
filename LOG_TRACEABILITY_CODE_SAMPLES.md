# 日志链路追踪功能代码样例

## 一、数据模型扩展

### 1. DriveLog 模型扩展 (app/models/drive_log.py)

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.utils.db_client import Base

class DriveLog(Base):
    __tablename__ = "drive_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)  # data_sensing, drive_logic, agent_task
    message = Column(Text, nullable=False)
    data = Column(JSON)
    trace_id = Column(String(100), index=True)  # 全局链路标识符
    parent_id = Column(Integer, ForeignKey("drive_logs.id"), nullable=True)  # 父日志ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 自引用关系
    parent = relationship("DriveLog", remote_side=[id])
```

### 2. 数据库迁移脚本 (migrations/versions/add_parent_id_to_drive_logs.py)

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 添加parent_id字段
    op.add_column('drive_logs', sa.Column('parent_id', sa.Integer(), nullable=True))
    # 添加外键约束
    op.create_foreign_key('fk_drive_logs_parent_id', 'drive_logs', 'drive_logs', ['parent_id'], ['id'])

def downgrade():
    op.drop_constraint('fk_drive_logs_parent_id', 'drive_logs', type_='foreignkey')
    op.drop_column('drive_logs', 'parent_id')
```

## 二、核心逻辑实现

### 1. 增强的日志记录函数 (app/engines/shared_utils.py)

```python
def log_event_with_parent(level: str, category: str, message: str, data: Dict[str, Any] = None, trace_id: str = None, parent_id: int = None):
    """记录带父子关系的驱动日志"""
    try:
        import uuid
        from app.models.drive_log import DriveLog
        
        db = get_db_session()
        try:
            log = DriveLog(
                level=level,
                category=category,
                message=message,
                data=data,
                trace_id=trace_id or str(uuid.uuid4()),
                parent_id=parent_id
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log.id
        finally:
            db.close()
    except Exception as e:
        logger.error(f"记录驱动日志失败: {str(e)}")
        return None

def get_trace_chain(trace_id: str, db: Session):
    """获取完整的链路追踪信息"""
    logs = db.query(DriveLog).filter(DriveLog.trace_id == trace_id).order_by(DriveLog.created_at).all()
    
    # 构建树形结构
    log_dict = {log.id: log for log in logs}
    root_logs = []
    
    for log in logs:
        if log.parent_id is None:
            root_logs.append(log)
        else:
            parent = log_dict.get(log.parent_id)
            if parent:
                if not hasattr(parent, 'children'):
                    parent.children = []
                parent.children.append(log)
    
    return root_logs
```

### 2. 数据感知引擎增强 (app/engines/data_sensing_engine.py)

```python
def trigger_event(self, event_type: str, model_id: int, data: Dict[str, Any], parent_log_id: int = None):
    """触发事件（增强版）"""
    import uuid
    trace_id = str(uuid.uuid4())
    event = {
        "type": event_type,
        "model_id": model_id,
        "data": data,
        "timestamp": time.time(),
        "trace_id": trace_id,
        "parent_log_id": parent_log_id
    }
    
    # 记录数据感知日志，并获取日志ID
    log_id = self._log_sensing_event(event_type, model_id, data, trace_id)
    event["log_id"] = log_id
    
    self.stats['events_triggered'] += 1
    
    for callback in self.event_callbacks:
        try:
            callback(event)
        except Exception as e:
            logger.error(f"事件回调出错: {str(e)}")
    
    return log_id  # 返回日志ID供后续使用

def _log_sensing_event(self, event_type: str, model_id: int, data: Dict[str, Any], trace_id: str):
    """记录数据感知事件日志"""
    log_id = log_event_with_parent(
        'info', 'data_sensing', 
        f"触发事件: {event_type}, 模型: {model_id}", 
        {
            "event_type": event_type,
            "model_id": model_id,
            "data": data
        }, 
        trace_id, 
        None  # 数据感知是根节点，parent_id为None
    )
    return log_id
```

### 3. 驱动引擎增强 (app/engines/drive_engine.py)

```python
def _process_event(self, event: Dict[str, Any]):
    """处理单个事件（增强版）"""
    try:
        event_type = event.get('type')
        event_data = event.get('data', {})
        config_id = event_data.get('config_id')
        parent_log_id = event.get('log_id')  # 获取父日志ID
        
        db = get_db_session()
        try:
            logics = db.query(DriveLogic).all()
            
            matched_logics = []
            for logic in logics:
                event_ids = [e.id for e in logic.events]
                if config_id in event_ids:
                    matched_logics.append(logic)
            
            if not matched_logics:
                for logic in logics:
                    if not logic.events:
                        matched_logics.append(logic)
            
            trace_id = event.get('trace_id')
            logger.info(f"事件 {event['type']} 匹配到 {len(matched_logics)} 条驱动逻辑")
            self.stats['logics_matched'] += len(matched_logics)
            
            # 记录驱动逻辑匹配日志
            drive_log_id = log_event_with_parent(
                'info', 'drive_logic', 
                f"事件 {event['type']} 匹配到 {len(matched_logics)} 条驱动逻辑", 
                {'event_type': event['type'], 'matched_count': len(matched_logics)}, 
                trace_id, parent_log_id
            )
            
            for logic in matched_logics:
                self.logic_executor.execute_logic(logic, event, db, trace_id, drive_log_id)
                
        finally:
            db.close()
            
    except Exception as e:
        self.stats['errors'] += 1
        logger.error(f"处理事件出错: {str(e)}")
        logger.error(traceback.format_exc())
```

### 4. 逻辑执行器增强 (app/engines/logic_executor.py)

```python
def execute_logic(self, logic: DriveLogic, event: Dict[str, Any], db, trace_id: str = None, parent_log_id: int = None):
    """执行驱动逻辑（增强版）"""
    try:
        config = logic.config or {}
        logic_type = logic.type
        
        logger.info(f"执行驱动逻辑: {logic.name} (类型: {logic_type})")
        
        # 记录驱动逻辑执行日志
        logic_log_id = log_event_with_parent(
            'info', 'drive_logic', 
            f"执行驱动逻辑: {logic.name}", 
            {'logic_name': logic.name, 'logic_type': logic_type}, 
            trace_id, parent_log_id
        )
        
        # ... 执行逻辑的原有代码 ...
        
        # 在触发任务时传递日志ID
        if trigger_tasks:
            for task in logic.tasks:
                task_manager.create_task_instance(task, processed_data, trace_id, logic_log_id)
                
    except Exception as e:
        logger.error(f"执行驱动逻辑失败: {logic.name}, 错误: {str(e)}")
        logger.error(traceback.format_exc())
```

## 三、API接口实现

### 1. 后端API增强 (app/api/drive_log.py)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.utils.db_client import get_db
from app.models.drive_log import DriveLog

router = APIRouter()

@router.get("/drive-logs/trace/{trace_id}")
def get_trace_chain(trace_id: str, db: Session = Depends(get_db)):
    """获取完整的链路追踪信息"""
    try:
        logs = db.query(DriveLog).filter(DriveLog.trace_id == trace_id).order_by(DriveLog.created_at).all()
        
        if not logs:
            raise HTTPException(status_code=404, detail="Trace ID not found")
        
        # 构建树形结构
        log_dict = {log.id: {
            "id": log.id,
            "level": log.level,
            "category": log.category,
            "message": log.message,
            "data": log.data,
            "trace_id": log.trace_id,
            "parent_id": log.parent_id,
            "created_at": log.created_at,
            "children": []
        } for log in logs}
        
        root_logs = []
        for log_id, log_data in log_dict.items():
            if log_data["parent_id"] is None:
                root_logs.append(log_data)
            else:
                parent = log_dict.get(log_data["parent_id"])
                if parent:
                    parent["children"].append(log_data)
        
        return {
            "success": True,
            "trace_id": trace_id,
            "chain": root_logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取链路信息失败: {str(e)}")

@router.get("/drive-logs/traces")
def get_all_traces(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取所有链路摘要信息"""
    try:
        # 获取所有唯一的trace_id
        trace_ids = db.query(DriveLog.trace_id).distinct().order_by(DriveLog.created_at.desc()).limit(limit).offset(offset).all()
        
        traces = []
        for trace_id_tuple in trace_ids:
            trace_id = trace_id_tuple[0]
            # 获取该trace的最新日志作为摘要
            latest_log = db.query(DriveLog).filter(DriveLog.trace_id == trace_id).order_by(DriveLog.created_at.desc()).first()
            if latest_log:
                traces.append({
                    "trace_id": trace_id,
                    "latest_message": latest_log.message,
                    "latest_level": latest_log.level,
                    "latest_category": latest_log.category,
                    "latest_time": latest_log.created_at,
                    "log_count": db.query(DriveLog).filter(DriveLog.trace_id == trace_id).count()
                })
        
        return {
            "success": True,
            "traces": traces,
            "total": db.query(DriveLog.trace_id).distinct().count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取链路列表失败: {str(e)}")
```

### 2. 前端API服务增强 (frontend/src/services/api.js)

```javascript
// 在现有的driveLogApi中添加新方法
const driveLogApi = {
  // ... 现有方法 ...
  
  getAll: (params = {}) => {
    const queryParams = new URLSearchParams(params).toString();
    return api.get(`/drive-logs${queryParams ? '?' + queryParams : ''}`);
  },
  
  getTraceChain: (traceId) => {
    return api.get(`/drive-logs/trace/${traceId}`);
  },
  
  getAllTraces: (params = {}) => {
    const queryParams = new URLSearchParams(params).toString();
    return api.get(`/drive-logs/traces${queryParams ? '?' + queryParams : ''}`);
  }
};

export default driveLogApi;
```

## 四、前端组件实现

### 1. 增强的驱动日志组件 (frontend/src/components/DriveLog/DriveLog.jsx)

```jsx
import { useState, useEffect } from 'react'
import { Table, Button, Select, message, Input, Card, Tag } from 'antd'
import { driveLogApi } from '../../services/api'

const { Option } = Select
const { Search } = Input

function DriveLog() {
  const [logs, setLogs] = useState([])
  const [traces, setTraces] = useState([])
  const [selectedTrace, setSelectedTrace] = useState(null)
  const [loading, setLoading] = useState(false)
  const [traceView, setTraceView] = useState('list') // 'list' or 'chain'
  const [filters, setFilters] = useState({
    level: null,
    search: ''
  })

  useEffect(() => {
    if (traceView === 'list') {
      fetchTraces()
    }
  }, [traceView, filters])

  const fetchTraces = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.level) params.level = filters.level
      if (filters.search) params.search = filters.search
      
      const response = await driveLogApi.getAllTraces(params)
      setTraces(response.data.traces)
    } catch (error) {
      message.error('获取链路列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchTraceChain = async (traceId) => {
    setLoading(true)
    try {
      const response = await driveLogApi.getTraceChain(traceId)
      setSelectedTrace(response.data.chain)
      setTraceView('chain')
    } catch (error) {
      message.error('获取链路详情失败')
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

  const renderTraceTree = (logs, level = 0) => {
    return logs.map((log) => (
      <div key={log.id} style={{ marginLeft: level * 20, marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', backgroundColor: level === 0 ? '#f0f9ff' : '#fafafa', borderLeft: `3px solid ${getLevelColor(log.level)}` }}>
          <Tag color={getLevelColor(log.level)}>{log.level.toUpperCase()}</Tag>
          <Tag color="blue">{getCategoryText(log.category)}</Tag>
          <span style={{ flex: 1 }}>{log.message}</span>
          <span style={{ fontSize: '12px', color: '#666' }}>{formatDateTime(log.created_at)}</span>
        </div>
        {log.data && (
          <div style={{ marginLeft: 12, fontSize: '12px', backgroundColor: '#f9f9f9', padding: 8, borderRadius: 4, overflow: 'auto' }}>
            <pre>{JSON.stringify(log.data, null, 2)}</pre>
          </div>
        )}
        {log.children && log.children.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {renderTraceTree(log.children, level + 1)}
          </div>
        )}
      </div>
    ))
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>驱动日志</h2>
        {traceView === 'chain' && (
          <Button onClick={() => setTraceView('list')}>返回列表</Button>
        )}
      </div>

      {traceView === 'list' ? (
        <div>
          {/* 过滤器 */}
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
          
          {/* 链路列表 */}
          <Table 
            dataSource={traces}
            columns={[
              {
                title: 'Trace ID',
                dataIndex: 'trace_id',
                key: 'trace_id',
                render: (traceId) => (
                  <Button type="link" onClick={() => fetchTraceChain(traceId)}>
                    {traceId.substring(0, 8)}...
                  </Button>
                )
              },
              {
                title: '最新消息',
                dataIndex: 'latest_message',
                key: 'latest_message'
              },
              {
                title: '级别',
                dataIndex: 'latest_level',
                key: 'latest_level',
                render: (level) => <Tag color={getLevelColor(level)}>{level.toUpperCase()}</Tag>
              },
              {
                title: '类别',
                dataIndex: 'latest_category',
                key: 'latest_category',
                render: (category) => <Tag color="blue">{getCategoryText(category)}</Tag>
              },
              {
                title: '日志数量',
                dataIndex: 'log_count',
                key: 'log_count'
              },
              {
                title: '时间',
                dataIndex: 'latest_time',
                key: 'latest_time',
                render: (time) => formatDateTime(time)
              }
            ]}
            loading={loading}
            rowKey="trace_id"
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条链路`
            }}
          />
        </div>
      ) : (
        // 链路详情视图
        <Card>
          <h3>链路详情 - {selectedTrace?.[0]?.trace_id}</h3>
          {selectedTrace && renderTraceTree(selectedTrace)}
        </Card>
      )}
    </div>
  )
}

export default DriveLog
```

## 五、使用说明

### 1. 数据库迁移
```bash
# 生成迁移脚本
alembic revision --autogenerate -m "add parent_id to drive_logs"

# 应用迁移
alembic upgrade head
```

### 2. 功能测试
- **链路列表**: 访问 `/drive-logs` 查看所有链路摘要
- **链路详情**: 点击任意 Trace ID 查看完整的树形链路结构
- **层级展示**: 支持多级嵌套，清晰展示数据感知 → 驱动逻辑 → Agent任务的完整执行流程

### 3. 兼容性说明
- 现有日志数据的 `parent_id` 字段将自动设为 `null`
- 现有的 `/drive-logs` API 接口保持不变
- 新增的链路追踪功能对现有功能无任何影响

### 4. 性能优化建议
- 为 `(trace_id, parent_id)` 字段添加复合索引
- 实现日志数据的自动清理机制
- 对于大数据量场景，考虑分页加载和懒加载策略