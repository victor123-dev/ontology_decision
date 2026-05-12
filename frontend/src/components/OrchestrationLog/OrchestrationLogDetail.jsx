import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactFlow, {
  Background,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  ReactFlowProvider,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { Card, Space, Button, Descriptions, Tag, Spin, message, Typography, Drawer, Tooltip } from 'antd';
import { ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, MinusCircleOutlined, SwapRightOutlined } from '@ant-design/icons';
import { orchestrationLogApi } from '../../services/api';
import '../LogicOrchestration/LogicOrchestration.css';

const { Text } = Typography;

const statusConfig = {
  success: { color: '#52c41a', borderColor: '#52c41a', bg: '#f6ffed', icon: <CheckCircleOutlined />, text: '已执行', tagColor: 'green' },
  failed: { color: '#ff4d4f', borderColor: '#ff4d4f', bg: '#fff2f0', icon: <CloseCircleOutlined />, text: '执行失败', tagColor: 'red' },
  skipped: { color: '#d9d9d9', borderColor: '#d9d9d9', bg: '#fafafa', icon: <MinusCircleOutlined />, text: '已跳过', tagColor: 'default' },
  not_reached: { color: '#faad14', borderColor: '#faad14', bg: '#fffbe6', icon: <SwapRightOutlined />, text: '未执行', tagColor: 'orange' },
};

const LogActionNode = ({ data, id }) => {
  const nodeData = data || {};
  const cfg = statusConfig[nodeData.logStatus] || statusConfig.not_reached;
  const isSkipped = nodeData.logStatus === 'skipped';

  return (
    <div
      className="action-node"
      style={{
        borderColor: cfg.borderColor,
        background: isSkipped ? cfg.bg : '#fff',
        opacity: isSkipped ? 0.65 : 1,
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Top} id="input" style={{ background: '#52c41a', width: 12, height: 12 }} isConnectable={false} />
      <div className="action-node-header" style={{ background: cfg.bg }}>
        {cfg.icon}
        <span className="action-node-title">{nodeData.label}</span>
        <Tag color={cfg.tagColor} style={{ fontSize: 10, marginLeft: 'auto' }}>{cfg.text}</Tag>
      </div>
      <div className="action-node-body">
        <Text type="secondary" style={{ fontSize: '10px', display: 'block', color: '#888' }}>
          {nodeData.apiName}
        </Text>
        <Tag color="blue" style={{ fontSize: '10px', marginTop: '4px', margin: 0 }}>{nodeData.actionType}</Tag>
      </div>
      <Handle type="source" position={Position.Bottom} id="output" style={{ background: '#1890ff', width: 12, height: 12 }} isConnectable={false} />
    </div>
  );
};

const LogConditionNode = ({ data, id }) => {
  const nodeData = data || {};
  const cfg = statusConfig[nodeData.logStatus] || statusConfig.not_reached;
  const branches = nodeData.branches || [];

  return (
    <div
      className="condition-node"
      style={{
        borderColor: cfg.borderColor,
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Top} id="input" style={{ background: '#52c41a', width: 12, height: 12 }} isConnectable={false} />
      <div className="condition-node-header" style={{ background: cfg.bg }}>
        {cfg.icon}
        <span className="condition-node-title">{nodeData.label || '条件分支'}</span>
        <Tag color={cfg.tagColor} style={{ fontSize: 10, marginLeft: 'auto' }}>{cfg.text}</Tag>
      </div>
      <div className="condition-node-body">
        <Text type="secondary" style={{ fontSize: '11px', display: 'block' }}>
          {nodeData.condition || '条件分支'}
        </Text>
      </div>
      {branches.length > 0 ? (
        <div className="condition-branches">
          {branches.map((branch, index) => (
            <div key={index} className="branch-row">
              <div className="branch-row-left">
                <Handle
                  type="source"
                  position={Position.Right}
                  id={`branch${index}`}
                  style={{ top: '50%', transform: 'translateY(-50%)', background: '#faad14', width: 12, height: 12 }}
                  isConnectable={false}
                />
                <span className="branch-index">{index + 1}</span>
              </div>
              <div className="branch-row-content">
                <div className="branch-row-item">
                  <span className="branch-row-label">名称:</span>
                  <span className="branch-row-value">{branch.title || '分支'}</span>
                </div>
                <div className="branch-row-item">
                  <span className="branch-row-label">条件:</span>
                  <span className="branch-row-value">{branch.condition || ''}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

const LogMergeNode = ({ data, id }) => {
  const nodeData = data || {};
  const cfg = statusConfig[nodeData.logStatus] || statusConfig.not_reached;

  return (
    <div
      className="merge-node"
      style={{
        borderColor: cfg.borderColor,
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Top} id="input" style={{ background: '#52c41a', width: 12, height: 12 }} isConnectable={false} />
      <div className="merge-node-header" style={{ background: cfg.bg }}>
        {cfg.icon}
        <span className="merge-node-title">{nodeData.label || '分支合并'}</span>
        <Tag color={cfg.tagColor} style={{ fontSize: 10, marginLeft: 'auto' }}>{cfg.text}</Tag>
      </div>
      <div className="merge-node-body">
        <Text type="secondary" style={{ fontSize: '11px', display: 'block' }}>汇聚多个分支路径</Text>
      </div>
      <Handle type="source" position={Position.Bottom} id="output" style={{ background: '#1890ff', width: 12, height: 12 }} isConnectable={false} />
    </div>
  );
};

const logNodeTypes = {
  action: LogActionNode,
  condition: LogConditionNode,
  merge: LogMergeNode,
};

const getConditionNodeHeight = (node) => {
  const branchCount = node.data?.branches?.length || 0;
  return 80 + branchCount * 56 + 40;
};

const getNodeHeight = (node) => {
  if (node.type === 'condition') return getConditionNodeHeight(node);
  if (node.type === 'merge') return 100;
  return 130;
};

const getLayoutedElements = (nodes, edges) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  const nodeWidth = 220;

  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 150, marginx: 100, marginy: 100, align: 'DL', ranker: 'network-simplex', edgesep: 50 });

  nodes.forEach((node) => {
    const height = getNodeHeight(node);
    dagreGraph.setNode(node.id, { width: nodeWidth, height });
  });
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });
  dagre.layout(dagreGraph);

  let layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    if (!nodeWithPosition) return node;
    const height = getNodeHeight(node);
    return {
      ...node,
      position: { x: nodeWithPosition.x - nodeWidth / 2, y: nodeWithPosition.y - height / 2 },
      style: { width: nodeWidth, height },
    };
  });

  // Adjust condition branch children positions
  const conditionNodes = layoutedNodes.filter(n => n.type === 'condition');
  conditionNodes.forEach(conditionNode => {
    const branches = conditionNode.data?.branches || [];
    if (branches.length === 0) return;
    const conditionHeight = getConditionNodeHeight(conditionNode);
    const childY = conditionNode.position.y + conditionHeight + 120;
    branches.forEach((_, branchIndex) => {
      const sourceHandle = `branch${branchIndex}`;
      const branchEdge = edges.find(e => e.source === conditionNode.id && e.sourceHandle === sourceHandle);
      if (!branchEdge) return;
      const childIdx = layoutedNodes.findIndex(n => n.id === branchEdge.target);
      if (childIdx === -1) return;
      layoutedNodes[childIdx] = {
        ...layoutedNodes[childIdx],
        position: { x: conditionNode.position.x + nodeWidth + branchIndex * (nodeWidth + 80), y: childY },
      };
    });
  });

  // Adjust action/merge child nodes
  const conditionChildIds = new Set();
  conditionNodes.forEach(condNode => {
    (condNode.data?.branches || []).forEach((_, branchIndex) => {
      const branchEdge = edges.find(e => e.source === condNode.id && e.sourceHandle === `branch${branchIndex}`);
      if (branchEdge) conditionChildIds.add(branchEdge.target);
    });
  });

  layoutedNodes.forEach(node => {
    if (node.type === 'condition' || node.id.startsWith('ghost-')) return;
    const outputEdges = edges.filter(e => e.source === node.id && e.sourceHandle === 'output' && !conditionChildIds.has(e.target));
    outputEdges.forEach(edge => {
      const childIdx = layoutedNodes.findIndex(n => n.id === edge.target);
      if (childIdx === -1 || layoutedNodes[childIdx].id.startsWith('ghost-')) return;
      const parentHeight = getNodeHeight(node);
      layoutedNodes[childIdx] = {
        ...layoutedNodes[childIdx],
        position: { x: node.position.x, y: node.position.y + parentHeight + 150 },
      };
    });
  });

  return { nodes: layoutedNodes, edges };
};

const OrchestrationLogDetailContent = () => {
  const { id: logId } = useParams();
  const navigate = useNavigate();
  const [logData, setLogData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [nodes, setNodes] = useNodesState([]);
  const [edges, setEdges] = useEdgesState([]);
  const [selectedNodeLog, setSelectedNodeLog] = useState(null);
  const [drawerVisible, setDrawerVisible] = useState(false);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const res = await orchestrationLogApi.get(logId);
        const data = res.data;
        setLogData(data);

        if (data?.graph_data) {
          const graphData = data.graph_data;
          const nodeLogsMap = {};
          (data.node_logs || []).forEach(nl => {
            nodeLogsMap[nl.node_id] = nl;
          });

          // Collect branch info from edges
          const branchInfoMap = {};
          (graphData.edges || []).forEach(edge => {
            if (edge.sourceHandle?.startsWith('branch')) {
              const branchIndex = parseInt(edge.sourceHandle.replace('branch', ''), 10);
              const key = `${edge.source}-${branchIndex}`;
              if (!branchInfoMap[key]) branchInfoMap[key] = { condition: '', title: '' };
              branchInfoMap[key].condition = edge.condition || branchInfoMap[key].condition;
              branchInfoMap[key].title = edge.branchTitle || branchInfoMap[key].title;
            }
          });

          const loadedNodes = (graphData.nodes || []).map((node, idx) => {
            const nodeData = node.data || {};
            const nodeLog = nodeLogsMap[node.id];
            const logStatus = nodeLog?.status || 'not_reached';

            const baseData = {
              id: node.id || `node-${idx}`,
              type: node.type || 'action',
              position: node.position || { x: 100, y: 150 * idx + 50 },
              data: {
                label: nodeData.label || node.label || node.id,
                actionId: node.actionId || nodeData.actionId,
                apiName: nodeData.apiName || '',
                actionType: nodeData.actionType || '',
                logStatus,
                paramValues: nodeData.paramValues || {},
                contextHandler: nodeData.contextHandler || '',
              },
            };

            if (baseData.type === 'condition') {
              baseData.data.label = nodeData.label || node.label || '条件分支';
              if (nodeData.branches && nodeData.branches.length > 0) {
                baseData.data.branches = nodeData.branches;
              } else {
                const nodeBranchKeys = Object.keys(branchInfoMap).filter(k => k.startsWith(`${baseData.id}-`));
                if (nodeBranchKeys.length > 0) {
                  baseData.data.branches = nodeBranchKeys
                    .sort((a, b) => parseInt(a.split('-').pop()) - parseInt(b.split('-').pop()))
                    .map(key => ({ title: branchInfoMap[key].title || '分支', condition: branchInfoMap[key].condition || '' }));
                } else {
                  baseData.data.branches = [];
                }
              }
            } else {
              baseData.data.branches = [];
            }

            return baseData;
          });

          const seenIds = new Set();
          const loadedEdges = (graphData.edges || []).map((edge, idx) => {
            const edgeId = edge.id || `edge-${idx}`;
            let uniqueId = edgeId;
            let counter = 0;
            while (seenIds.has(uniqueId)) {
              counter++;
              uniqueId = `${edgeId}-${counter}`;
            }
            seenIds.add(uniqueId);

            let branchColor = '#1890ff';
            if (edge.sourceHandle?.startsWith('branch')) {
              const bIdx = parseInt(edge.sourceHandle.replace('branch', ''), 10);
              branchColor = bIdx === 0 ? '#52c41a' : bIdx === 1 ? '#f5222d' : '#faad14';
            }

            return {
              id: uniqueId,
              source: edge.source,
              target: edge.target,
              sourceHandle: edge.sourceHandle || 'output',
              targetHandle: edge.targetHandle || 'input',
              type: 'smoothstep',
              animated: false,
              style: { stroke: branchColor, strokeWidth: 2 },
              label: edge.branchTitle,
              labelStyle: { fill: branchColor, fontWeight: 'bold', fontSize: '12px' },
              labelBgStyle: { fill: '#fff', fillOpacity: 0.8 },
            };
          });

          const { nodes: layoutedNodes } = getLayoutedElements(loadedNodes, loadedEdges);
          setNodes(layoutedNodes);
          setEdges(loadedEdges);
        }
      } catch (err) {
        console.error('获取日志详情失败:', err);
        message.error('获取日志详情失败');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [logId, setNodes, setEdges]);

  const nodeLogsMap = useMemo(() => {
    const map = {};
    (logData?.node_logs || []).forEach(nl => { map[nl.node_id] = nl; });
    return map;
  }, [logData]);

  const onNodeClick = useCallback((event, node) => {
    const nodeLog = nodeLogsMap[node.id];
    if (nodeLog) {
      setSelectedNodeLog(nodeLog);
      setDrawerVisible(true);
    }
  }, [nodeLogsMap]);

  const formatDateTime = (str) => {
    if (!str) return '-';
    const d = new Date(str);
    if (isNaN(d.getTime())) return str;
    return d.toLocaleString('zh-CN', { hour12: false });
  };

  const getDuration = (startedAt, finishedAt) => {
    if (!startedAt || !finishedAt) return '-';
    const ms = new Date(finishedAt) - new Date(startedAt);
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const statusTagMap = {
    success: <Tag color="green" icon={<CheckCircleOutlined />}>成功</Tag>,
    failed: <Tag color="red" icon={<CloseCircleOutlined />}>失败</Tag>,
    running: <Tag color="blue" icon={<Spin size="small" />}>运行中</Tag>,
  };

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>;
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f0f2f5' }}>
      {/* Header info bar */}
      <Card
        size="small"
        style={{ margin: '8px 8px 0', flexShrink: 0 }}
        title={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/orchestration-log')} size="small" />
            <span style={{ fontWeight: 600 }}>执行日志详情</span>
            {logData && statusTagMap[logData.status]}
          </Space>
        }
      >
        {logData && (
          <Descriptions size="small" column={6}>
            <Descriptions.Item label="编排名称">{logData.orchestration_name}</Descriptions.Item>
            <Descriptions.Item label="开始时间">{formatDateTime(logData.started_at)}</Descriptions.Item>
            <Descriptions.Item label="结束时间">{formatDateTime(logData.finished_at)}</Descriptions.Item>
            <Descriptions.Item label="耗时">{getDuration(logData.started_at, logData.finished_at)}</Descriptions.Item>
            <Descriptions.Item label="流程入参">
              <Tooltip title={<pre style={{ margin: 0, fontSize: 11 }}>{JSON.stringify(logData.input_data, null, 2)}</pre>}>
                <Text ellipsis style={{ maxWidth: 200, display: 'inline-block', verticalAlign: 'bottom' }}>
                  {JSON.stringify(logData.input_data)}
                </Text>
              </Tooltip>
            </Descriptions.Item>
            {logData.error && (
              <Descriptions.Item label="错误"><Text type="danger">{logData.error}</Text></Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Card>

      {/* Canvas */}
      <div style={{ flex: 1, margin: '0 8px 8px' }}>
        <Card size="small" style={{ height: '100%' }} styles={{ body: { height: 'calc(100% - 57px)', padding: 0, overflow: 'hidden' } }}>
          <div style={{ width: '100%', height: '100%' }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodeClick={onNodeClick}
              nodeTypes={logNodeTypes}
              minZoom={0.2}
              maxZoom={2}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
              zoomOnScroll={false}
              panOnScroll={true}
              panOnDrag={true}
              zoomOnDoubleClick={false}
              defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
            >
              <Background color="#aaa" gap={16} />
            </ReactFlow>
          </div>
        </Card>
      </div>

      {/* Node detail drawer */}
      <Drawer
        title={selectedNodeLog ? `节点详情 - ${selectedNodeLog.node_label}` : '节点详情'}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={480}
      >
        {selectedNodeLog && (() => {
          const cfg = statusConfig[selectedNodeLog.status] || statusConfig.not_reached;
          return (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                {cfg.icon}
                <Tag color={cfg.tagColor}>{cfg.text}</Tag>
                <Tag color="blue">{selectedNodeLog.node_type}</Tag>
              </div>
              <Descriptions bordered size="small" column={1}>
                {selectedNodeLog.input_params !== undefined && selectedNodeLog.input_params !== null && (
                  <Descriptions.Item label="入参">
                    <pre style={{ margin: 0, maxHeight: 200, overflow: 'auto', fontSize: 12 }}>
                      {JSON.stringify(selectedNodeLog.input_params, null, 2)}
                    </pre>
                  </Descriptions.Item>
                )}
                {selectedNodeLog.output !== undefined && selectedNodeLog.output !== null && (
                  <Descriptions.Item label="返回结果">
                    <pre style={{ margin: 0, maxHeight: 200, overflow: 'auto', fontSize: 12 }}>
                      {JSON.stringify(selectedNodeLog.output, null, 2)}
                    </pre>
                  </Descriptions.Item>
                )}
                {selectedNodeLog.context_snapshot && (
                  <Descriptions.Item label="执行后上下文">
                    <pre style={{ margin: 0, maxHeight: 200, overflow: 'auto', fontSize: 12 }}>
                      {JSON.stringify(selectedNodeLog.context_snapshot, null, 2)}
                    </pre>
                  </Descriptions.Item>
                )}
                {selectedNodeLog.selected_branch && (
                  <Descriptions.Item label="选中分支">{selectedNodeLog.selected_branch}</Descriptions.Item>
                )}
                {selectedNodeLog.error && (
                  <Descriptions.Item label="错误信息">
                    <span style={{ color: '#ff4d4f' }}>{selectedNodeLog.error}</span>
                  </Descriptions.Item>
                )}
              </Descriptions>
            </div>
          );
        })()}
      </Drawer>
    </div>
  );
};

export default function OrchestrationLogDetail() {
  return (
    <ReactFlowProvider>
      <OrchestrationLogDetailContent />
    </ReactFlowProvider>
  );
}
