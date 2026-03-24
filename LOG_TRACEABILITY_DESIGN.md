# 日志链路追踪功能设计文档

## 一、需求背景

根据教师反馈，需要将执行的日志以链路形式展开展示，实现完整的执行过程追踪。当前系统已经具备基本的 `trace_id` 功能，但缺乏层级关系和完整的可视化展示。

## 二、设计目标

1. **完整链路追踪**: 从数据感知 → 驱动逻辑 → Agent任务的完整执行链路
2. **层级关系**: 支持父子日志关系，清晰展示调用层次
3. **可视化展示**: 提供直观的树形结构展示界面
4. **高效查询**: 支持大数据量下的快速查询和展示
5. **向后兼容**: 保持现有API接口不变，确保平滑升级

## 三、数据模型设计

### 1. DriveLog 模型扩展

```python
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

### 2. 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 日志唯一ID |
| level | String | 日志级别 (info/warning/error) |
| category | String | 日志类别 (data_sensing/drive_logic/agent_task) |
| message | Text | 日志消息 |
| data | JSON | 详细数据上下文 |
| trace_id | String | 全局链路标识符 |
| parent_id | Integer | 父日志ID，支持层级关系 |
| created_at | DateTime | 创建时间 |

### 3. 链路结构示例

```
trace_id: "abc123"
├── 数据感知日志 (parent_id: null, category: data_sensing)
│   ├── 驱动逻辑日志1 (parent_id: 1, category: drive_logic)
│   │   └── Agent任务日志1 (parent_id: 2, category: agent_task)
│   └── 驱动逻辑日志2 (parent_id: 1, category: drive_logic)
│       └── Agent任务日志2 (parent_id: 3, category: agent_task)
└── 数据感知日志2 (parent_id: null, category: data_sensing)
    └── 驱动逻辑日志3 (parent_id: 4, category: drive_logic)
        └── Agent任务日志3 (parent_id: 5, category: agent_task)
```

## 四、核心逻辑设计

### 1. 数据感知引擎增强

**文件**: `app/engines/data_sensing_engine.py`

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
    
    for callback in self.event_callbacks:
        try:
            callback(event)
        except Exception as e:
            logger.error(f"事件回调出错: {str(e)}")
    
    return log_id
```

### 2. 驱动引擎增强

**文件**: `app/engines/drive_engine.py`

```python
def _process_event(self, event: Dict[str, Any]):
    """处理单个事件（增强版）"""
    try:
        parent_log_id = event.get('log_id')  # 获取父日志ID
        
        # ... 原有逻辑 ...
        
        # 记录驱动逻辑匹配日志
        drive_log_id = log_event_with_parent(
            'info', 'drive_logic', 
            f"事件 {event['type']} 匹配到 {len(matched_logics)} 条驱动逻辑", 
            {'event_type': event['type'], 'matched_count': len(matched_logics)}, 
            trace_id, parent_log_id
        )
        
        for logic in matched_logics:
            self.logic_executor.execute_logic(logic, event, db, trace_id, drive_log_id)
            
    except Exception as e:
        # ... 错误处理 ...
```

### 3. 增强的日志记录函数

**文件**: `app/engines/shared_utils.py`

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
```

### 4. 链路查询优化

**文件**: `app/engines/shared_utils.py`

```python
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

## 五、API接口设计

### 1. 后端API

**文件**: `app/api/drive_log.py`

#### 获取完整链路信息
- **Endpoint**: `GET /api/v1/drive-logs/trace/{trace_id}`
- **描述**: 获取指定trace_id的完整链路追踪信息
- **响应**:
```json
{
  "success": true,
  "trace_id": "abc123",
  "chain": [
    {
      "id": 1,
      "level": "info",
      "category": "data_sensing",
      "message": "触发事件: order_created",
      "data": {...},
      "trace_id": "abc123",
      "parent_id": null,
      "created_at": "2026-03-24T10:00:00Z",
      "children": [
        {
          "id": 2,
          "level": "info",
          "category": "drive_logic",
          "message": "执行驱动逻辑: 大额订单审批",
          "data": {...},
          "trace_id": "abc123",
          "parent_id": 1,
          "created_at": "2026-03-24T10:00:01Z",
          "children": [
            {
              "id": 3,
              "level": "info",
              "category": "agent_task",
              "message": "创建Agent任务: 审批大额订单",
              "data": {...},
              "trace_id": "abc123",
              "parent_id": 2,
              "created_at": "2026-03-24T10:00:02Z",
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

#### 获取所有链路摘要
- **Endpoint**: `GET /api/v1/drive-logs/traces`
- **参数**: 
  - `limit`: 返回数量限制 (默认100)
  - `offset`: 分页偏移量 (默认0)
- **描述**: 获取所有链路的摘要信息列表
- **响应**:
```json
{
  "success": true,
  "traces": [
    {
      "trace_id": "abc123",
      "latest_message": "创建Agent任务: 审批大额订单",
      "latest_level": "info",
      "latest_category": "agent_task",
      "latest_time": "2026-03-24T10:00:02Z",
      "log_count": 3
    }
  ],
  "total": 150
}
```

### 2. 前端API服务

**文件**: `frontend/src/services/api.js`

```javascript
const driveLogApi = {
  // 现有方法...
  
  getTraceChain: (traceId) => {
    return api.get(`/drive-logs/trace/${traceId}`);
  },
  
  getAllTraces: (params = {}) => {
    const queryParams = new URLSearchParams(params).toString();
    return api.get(`/drive-logs/traces${queryParams ? '?' + queryParams : ''}`);
  }
};
```

## 六、前端界面设计

### 1. 组件结构

**文件**: `frontend/src/components/DriveLog/DriveLog.jsx`

#### 视图模式
- **列表视图**: 显示所有链路摘要，支持按trace_id查看详情
- **链路视图**: 显示完整的树形链路结构

#### 主要功能
- 链路列表展示（trace_id、最新消息、日志数量、时间）
- 树形结构展示（支持多级嵌套）
- 级别和类别标签着色
- 时间格式化显示
- 数据上下文折叠/展开

### 2. UI组件示例

```jsx
// 链路列表视图
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
    // ... 其他列
  ]}
/>

// 链路树形视图
const renderTraceTree = (logs, level = 0) => {
  return logs.map((log) => (
    <div key={log.id} style={{ marginLeft: level * 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', backgroundColor: level === 0 ? '#f0f9ff' : '#fafafa', borderLeft: `3px solid ${getLevelColor(log.level)}` }}>
        <Tag color={getLevelColor(log.level)}>{log.level.toUpperCase()}</Tag>
        <Tag color={getCategoryText(log.category)}>{getCategoryText(log.category)}</Tag>
        <span style={{ flex: 1 }}>{log.message}</span>
        <span style={{ fontSize: '12px', color: '#666' }}>{formatDateTime(log.created_at)}</span>
      </div>
      {log.children && log.children.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {renderTraceTree(log.children, level + 1)}
        </div>
      )}
    </div>
  ));
};
```

## 七、数据库迁移

### 1. 迁移脚本

**文件**: `migrations/versions/add_parent_id_to_drive_logs.py`

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

### 2. 执行步骤
1. 生成迁移脚本: `alembic revision --autogenerate -m "add parent_id to drive_logs"`
2. 应用迁移: `alembic upgrade head`

## 八、测试方案

### 1. 单元测试

- 测试 `log_event_with_parent` 函数正确记录父子关系
- 测试 `get_trace_chain` 函数正确构建树形结构
- 测试API端点返回正确的数据格式

### 2. 集成测试

- 模拟完整的数据感知 → 驱动逻辑 → Agent任务流程
- 验证生成的日志具有正确的 `trace_id` 和 `parent_id`
- 验证前端能够正确展示链路结构

### 3. 性能测试

- 测试大量日志数据下的查询性能
- 验证分页功能正常工作
- 测试树形结构渲染性能

## 九、部署说明

### 1. 后端部署
1. 应用数据库迁移
2. 更新代码并重启服务

### 2. 前端部署
1. 更新前端代码
2. 重新构建并部署

### 3. 兼容性说明
- 现有日志数据的 `parent_id` 将为 `null`
- 现有API接口保持不变
- 新功能对现有功能无影响

## 十、后续优化

### 1. 性能优化
- 添加复合索引 `(trace_id, parent_id)` 提升查询性能
- 实现日志数据的自动清理机制

### 2. 功能扩展
- 支持链路搜索和过滤
- 添加链路统计和分析功能
- 实现链路导出功能

### 3. 可视化增强
- 添加时间轴视图
- 支持链路图谱可视化
- 实现交互式链路探索