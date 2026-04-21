import { useState, useEffect, useCallback } from 'react'
import { Table, Button, Select, message, Input, Card, Tag } from 'antd'
import { ReactFlow, Controls, Background, useNodesState, useEdgesState, MiniMap, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import dagre from 'dagre'
import { driveLogApi } from '../../services/api'

const { Option } = Select
const { Search } = Input

// 自定义节点组件
const LogNode = ({ data }) => {
  const getLevelColor = (level) => {
    switch (level) {
      case 'info': return 'green';
      case 'warning': return 'orange';
      case 'error': return 'red';
      default: return 'blue';
    }
  };

  const getCategoryText = (category) => {
    switch (category) {
      case 'data_sensing': return '数据感知';
      case 'drive_logic': return '驱动逻辑';
      case 'agent_task': return '行动执行';
      default: return category;
    }
  };

  const getCategoryColor = (category) => {
    switch (category) {
      case 'data_sensing': return 'geekblue';
      case 'drive_logic': return 'purple';
      case 'agent_task': return 'volcano';
      default: return 'blue';
    }
  };

  const formatDateTime = (dateTimeString) => {
    if (!dateTimeString) return '';
    const date = new Date(dateTimeString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };

  return (
    <div style={{
      backgroundColor: 'white',
      border: `2px solid #e8e8e8`,
      borderRadius: '8px',
      padding: '16px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      minWidth: '240px',
      maxWidth: '300px',
      position: 'relative'
    }}>
      {/* 顶部连接点 - 用于接收来自父节点的连接 */}
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        style={{ 
          background: '#555', 
          width: '10px', 
          height: '10px',
          top: '-5px',
          left: '50%',
          transform: 'translateX(-50%)'
        }}
      />
      
      {/* 步骤头部 */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '8px',
        marginBottom: '12px'
      }}>
        <div style={{
          width: '24px',
          height: '24px',
          borderRadius: '50%',
          backgroundColor: getLevelColor(data.level),
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          fontSize: '12px'
        }}>
          {data.stepNumber}
        </div>
        <Tag color={getLevelColor(data.level)}>{data.level.toUpperCase()}</Tag>
        <Tag color={getCategoryColor(data.category)}>{getCategoryText(data.category)}</Tag>
      </div>
      
      {/* 步骤内容 */}
      <div style={{ marginBottom: '12px' }}>
        <p style={{ margin: 0, fontSize: '14px', lineHeight: '1.4' }}>{data.message}</p>
      </div>
      
      {/* 详细数据（可折叠） */}
      {data.data && (
        <div style={{ 
          fontSize: '12px', 
          backgroundColor: '#f9f9f9', 
          padding: '8px', 
          borderRadius: '4px',
          maxHeight: '120px',
          overflow: 'auto'
        }}>
          <details>
            <summary style={{ cursor: 'pointer', marginBottom: '4px' }}>详细数据</summary>
            <pre style={{ margin: 0, fontSize: '11px' }}>{JSON.stringify(data.data, null, 2)}</pre>
          </details>
        </div>
      )}
      
      {/* 时间戳 */}
      <div style={{ 
        fontSize: '11px', 
        color: '#999', 
        marginTop: '8px',
        textAlign: 'right'
      }}>
        {formatDateTime(data.created_at)}
      </div>
      
      {/* 底部连接点 - 用于连接到子节点 */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        style={{ 
          background: '#555', 
          width: '10px', 
          height: '10px',
          bottom: '-5px',
          left: '50%',
          transform: 'translateX(-50%)'
        }}
      />
    </div>
  );
};

// 定义nodeTypes在组件外部
const nodeTypes = {
  logNode: LogNode
};

function DriveLog() {
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

  const fetchTraces = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.level) params.level = filters.level
      if (filters.search) params.search = filters.search
      
      const response = await driveLogApi.getAllTraces(params)
      setTraces(response.data.traces)
    } catch (_error) {
      message.error('获取链路列表失败')
    } finally {
      setLoading(false)
    }
  }, [filters]);

  const fetchTraceChain = async (traceId) => {
    setLoading(true)
    try {
      const response = await driveLogApi.getTraceChain(traceId)
      setSelectedTrace(response.data.chain)
      setTraceView('chain')
    } catch (_error) {
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
      case 'agent_task': return '行动执行'
      default: return category
    }
  }

  const getCategoryColor = (category) => {
    switch (category) {
      case 'data_sensing': return 'geekblue';
      case 'drive_logic': return 'purple';
      case 'agent_task': return 'volcano';
      default: return 'blue';
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

  // 使用dagre进行自动布局
  const getLayoutedElements = (nodes, edges, options) => {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    
    // 设置图的方向和间距
    g.setGraph({ 
      rankdir: options.rankdir || 'TB', // TB: top-bottom, LR: left-right
      ranksep: options.ranksep || 50,
      nodesep: options.nodesep || 50,
      marginx: options.marginx || 20,
      marginy: options.marginy || 20
    });
    
    // 添加节点到图中
    nodes.forEach((node) => {
      g.setNode(node.id, { width: 300, height: 150 }); // 节点的宽高
    });
    
    // 添加边到图中
    edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });
    
    // 执行布局计算
    dagre.layout(g);
    
    // 更新节点位置
    const layoutedNodes = nodes.map((node) => {
      const nodeWithPosition = g.node(node.id);
      return {
        ...node,
        position: {
          x: nodeWithPosition.x - nodeWithPosition.width / 2,
          y: nodeWithPosition.y - nodeWithPosition.height / 2
        },
        style: { width: nodeWithPosition.width, height: nodeWithPosition.height }
      };
    });
    
    return { nodes: layoutedNodes, edges };
  };

  // 将森林结构转换为ReactFlow的nodes和edges
  const convertForestToFlow = (forest) => {
    const nodes = [];
    const edges = [];
    
    // 先扁平化森林结构以获得正确的步骤编号
    const flattenForest = (logs, result = []) => {
      logs.forEach((log) => {
        result.push(log);
        if (log.children && log.children.length > 0) {
          flattenForest(log.children, result);
        }
      });
      return result;
    };
    
    const flattenedLogs = flattenForest(forest);
    const logStepMap = new Map();
    flattenedLogs.forEach((log, index) => {
      logStepMap.set(log.id, index + 1);
    });
    
    const traverse = (logs, parentId = null) => {
      logs.forEach((log) => {
        // 添加节点
        nodes.push({
          id: log.id.toString(),
          type: 'logNode',
          position: { x: 0, y: 0 }, // 位置由布局算法自动计算
          data: {
            ...log,
            stepNumber: logStepMap.get(log.id)
          },
          draggable: false
        });
        
        // 添加边（如果存在父节点）
        if (parentId !== null) {
          edges.push({
            id: `e${parentId}-${log.id}`,
            source: parentId.toString(),
            target: log.id.toString(),
            sourceHandle: 'bottom',
            targetHandle: 'top',
            animated: true
          });
        }
        
        // 递归处理子节点
        if (log.children && log.children.length > 0) {
          traverse(log.children, log.id);
        }
      });
    };
    
    traverse(forest);
    
    // 应用自动布局
    return getLayoutedElements(nodes, edges, { rankdir: 'TB' });
  };

  // ReactFlow组件
  const FlowChart = ({ forest }) => {
    const { nodes: initialNodes, edges: initialEdges } = convertForestToFlow(forest);
    const [nodes, , onNodesChange] = useNodesState(initialNodes);
    const [edges, , onEdgesChange] = useEdgesState(initialEdges);
    
    // 计算图的实际边界
    const bounds = {
      minX: Math.min(...nodes.map(node => node.position.x)),
      maxX: Math.max(...nodes.map(node => node.position.x + (node.style?.width || 300))),
      minY: Math.min(...nodes.map(node => node.position.y)),
      maxY: Math.max(...nodes.map(node => node.position.y + (node.style?.height || 150)))
    };
    
    const graphHeight = bounds.maxY - bounds.minY + 100; // 添加一些padding
    const containerHeight = Math.max(graphHeight, window.innerHeight - 216);
    
    return (
      <div style={{ height: `${containerHeight}px`, width: '100%', background: '#f5f5f5', borderRadius: '8px' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.1 }}
          proOptions={{ hideAttribution: true }}
          style={{ width: '100%', height: '100%' }}
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    );
  };

  return (
    <div style={{ width: '100%', height: '100%' }}>
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
                render: (category) => <Tag color={getCategoryColor(category)}>{getCategoryText(category)}</Tag>
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
        <Card style={{ width: '100%' }}>
          <h3>链路详情 - {selectedTrace?.[0]?.trace_id}</h3>
          {selectedTrace && <FlowChart forest={selectedTrace} />}
        </Card>
      )}
    </div>
  )
}

export default DriveLog