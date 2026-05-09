import ReactFlow, { 
  Background, 
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { useCallback, useState, useRef, useMemo, useEffect } from 'react';
import { Card, Typography, Space, Button, message, List, Tag, Input, Select, Modal, Form, Checkbox } from 'antd';
import { SearchOutlined, SaveOutlined, DownloadOutlined, DeleteOutlined, BranchesOutlined, PlusOutlined, SettingOutlined, UndoOutlined, ArrowLeftOutlined, EditOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { actionApi, orchestrationApi } from '../../services/api';
import './LogicOrchestration.css';

const { Title, Text } = Typography;
const { Search } = Input;

const ActionNode = ({ data, id }) => {
  const [showAddButton, setShowAddButton] = useState(false);

  const nodeData = data || {};
  
  const handleAddClick = (e) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('addEdgeFromNode', { 
      detail: { nodeId: id, nodeData } 
    }));
  };

  const handleConfigClick = (e) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('configActionParams', {
      detail: { nodeId: id, nodeData }
    }));
  };

  const handleContextClick = (e) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('configContextHandler', {
      detail: { nodeId: id, nodeData }
    }));
  };

  const paramValues = nodeData.paramValues || {};
  const paramDefs = nodeData.params || [];
  const hasParams = paramDefs.length > 0;
  const configuredCount = paramDefs.filter(p => paramValues[p.name] !== undefined && paramValues[p.name] !== '').length;
  const hasContextHandler = !!nodeData.contextHandler;

  return (
    <div 
      className="action-node"
      onMouseEnter={() => setShowAddButton(true)}
      onMouseLeave={() => setShowAddButton(false)}
    >
      <Handle 
        type="target" 
        position={Position.Top} 
        id="input"
        style={{ background: '#52c41a', width: 12, height: 12 }}
        isConnectable={true}
      />
      <div className="action-node-header">
        <span className="action-node-icon"></span>
        <span className="action-node-title">{nodeData.label}</span>
        <button 
          className="node-delete-btn"
          onClick={(e) => {
            e.stopPropagation();
            window.dispatchEvent(new CustomEvent('deleteNode', { detail: { nodeId: id } }));
          }}
        >
          ×
        </button>
      </div>
      <div className="action-node-body">
        <Text type="secondary" style={{ fontSize: '10px', display: 'block', color: '#888' }}>
          {nodeData.apiName}
        </Text>
        <Tag color="blue" style={{ fontSize: '10px', marginTop: '4px', margin: 0 }}>{nodeData.actionType}</Tag>
      </div>
      {hasParams && (
        <div className="action-node-params" onClick={handleConfigClick}>
          <SettingOutlined style={{ fontSize: '12px', marginRight: 4 }} />
          <span>参数 {configuredCount > 0 ? `(${configuredCount}/${paramDefs.length})` : ''}</span>
        </div>
      )}
      <div className="action-node-context" onClick={handleContextClick}>
        <span style={{ fontSize: '11px', color: hasContextHandler ? '#52c41a' : '#8c8c8c' }}>
          {hasContextHandler ? '✓ 上下文处理' : '+ 上下文处理'}
        </span>
      </div>
      <Handle 
        type="source" 
        position={Position.Bottom} 
        id="output"
        style={{ background: '#1890ff', width: 12, height: 12 }}
        isConnectable={true}
      />
      {showAddButton && (
        <div className="node-add-button" onClick={handleAddClick}>
          <PlusOutlined />
        </div>
      )}
    </div>
  );
};

const ConditionNode = ({ data, id }) => {
  const [isEditingLabel, setIsEditingLabel] = useState(false);

  const branches = data?.branches || [];

  const handleAddBranch = () => {
    window.dispatchEvent(new CustomEvent('requestAddBranch', { 
      detail: { nodeId: id } 
    }));
  };

  const handleEditBranch = (index) => {
    window.dispatchEvent(new CustomEvent('requestEditBranch', { 
      detail: { nodeId: id, branchIndex: index } 
    }));
  };

  const handleLabelDoubleClick = (e) => {
    e.stopPropagation();
    setIsEditingLabel(true);
  };

  const handleLabelBlur = () => {
    setIsEditingLabel(false);
  };

  const handleLabelKeyDown = (e) => {
    if (e.key === 'Enter') {
      const newLabel = e.target.value.trim() || '条件分支';
      window.dispatchEvent(new CustomEvent('updateConditionNode', {
        detail: { nodeId: id, updates: { label: newLabel } }
      }));
      setIsEditingLabel(false);
    } else if (e.key === 'Escape') {
      setIsEditingLabel(false);
    }
  };

  return (
    <div className="condition-node">
      <Handle 
        type="target" 
        position={Position.Top} 
        id="input"
        style={{ background: '#52c41a', width: 12, height: 12 }}
        isConnectable={true}
      />
      <div className="condition-node-header">
        <span className="condition-node-icon"></span>
        {isEditingLabel ? (
          <input
            className="condition-node-title-input"
            defaultValue={data?.label || '条件分支'}
            autoFocus
            onBlur={handleLabelBlur}
            onKeyDown={handleLabelKeyDown}
            onClick={(e) => e.stopPropagation()}
            onDoubleClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            style={{ 
              fontSize: '12px', 
              padding: '2px 4px', 
              border: '1px solid #1890ff', 
              borderRadius: '2px',
              width: '80px'
            }}
          />
        ) : (
          <span 
            className="condition-node-title" 
            onDoubleClick={handleLabelDoubleClick}
            title="双击编辑名称"
            style={{ cursor: 'pointer' }}
          >
            {data?.label || '条件分支'}
          </span>
        )}
        <button 
          className="node-delete-btn"
          onClick={(e) => {
            e.stopPropagation();
            window.dispatchEvent(new CustomEvent('deleteNode', { detail: { nodeId: id } }));
          }}
        >
          ×
        </button>
      </div>
      <div className="condition-node-body">
        <Text type="secondary" style={{ fontSize: '11px', display: 'block' }}>
          {data?.condition || '请添加分支并配置条件'}
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
                  style={{ 
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: '#faad14', 
                    width: 12, 
                    height: 12 
                  }}
                  isConnectable={true}
                />
                <span className="branch-index">{index + 1}</span>
              </div>
              <div className="branch-row-content" onClick={() => handleEditBranch(index)}>
                <div className="branch-row-item">
                  <span className="branch-row-label">名称:</span>
                  <span className="branch-row-value">
                    {branch.title || '点击设置名称'}
                  </span>
                </div>
                <div className="branch-row-item">
                  <span className="branch-row-label">条件:</span>
                  <span className="branch-row-value">
                    {branch.condition || '点击设置条件'}
                  </span>
                </div>
              </div>
              <button 
                className="branch-delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  window.dispatchEvent(new CustomEvent('deleteBranch', { 
                    detail: { nodeId: id, branchIndex: index } 
                  }));
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="condition-no-branches">
          <Text type="secondary" style={{ fontSize: '11px' }}>暂无分支，请点击下方按钮添加</Text>
        </div>
      )}
      <button className="add-branch-btn" onClick={handleAddBranch}>
        + 添加分支
      </button>
    </div>
  );
};

const GhostNode = ({ data, id }) => {
  const nodeData = data || {};
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(nodeData.label || '');

  const handleDoubleClick = (e) => {
    e.stopPropagation();
    setEditValue(nodeData.label || '');
    setIsEditing(true);
  };

  const handleBlur = () => {
    setIsEditing(false);
    if (editValue.trim() && editValue !== nodeData.label) {
      window.dispatchEvent(new CustomEvent('updateGhostNode', {
        detail: { nodeId: id, updates: { label: editValue.trim() } }
      }));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleBlur();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
    }
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (id === 'ghost-node') {
      // 临时 ghost 节点，只需清除状态
      window.dispatchEvent(new CustomEvent('cancelGhostNode'));
    } else {
      // 条件分支的 ghost 节点，走正常删除逻辑
      window.dispatchEvent(new CustomEvent('deleteNode', { detail: { nodeId: id } }));
    }
  };

  return (
    <div className="ghost-node">
      <Handle 
        type="target" 
        position={Position.Top} 
        id="input"
        style={{ background: '#1890ff', width: 12, height: 12 }}
        isConnectable={true}
      />
      <button 
        className="node-delete-btn"
        onClick={handleDelete}
        title="删除"
      >
        ×
      </button>
      <div className="ghost-node-content">
        <div className="ghost-icon">+</div>
        {isEditing ? (
          <input
            className="ghost-text-input"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            onClick={(e) => e.stopPropagation()}
            onDoubleClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            autoFocus
            style={{ 
              fontSize: '10px', 
              padding: '1px 4px', 
              border: '1px solid #1890ff', 
              borderRadius: '2px',
              width: '80px',
              textAlign: 'center'
            }}
          />
        ) : (
          <div 
            className="ghost-text"
            onDoubleClick={handleDoubleClick}
            title="双击编辑名称"
            style={{ cursor: 'pointer' }}
          >
            {nodeData.label}
          </div>
        )}
      </div>
      <Handle 
        type="source" 
        position={Position.Bottom} 
        id="output"
        style={{ background: '#1890ff', width: 12, height: 12 }}
        isConnectable={true}
      />
    </div>
  );
};

const MergeNode = ({ data, id }) => {
  const [showAddButton, setShowAddButton] = useState(false);
  const nodeData = data || {};

  const handleAddClick = (e) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('addEdgeFromNode', { 
      detail: { nodeId: id, nodeData } 
    }));
  };

  return (
    <div 
      className="merge-node"
      onMouseEnter={() => setShowAddButton(true)}
      onMouseLeave={() => setShowAddButton(false)}
    >
      <Handle 
        type="target" 
        position={Position.Top} 
        id="input"
        style={{ background: '#52c41a', width: 12, height: 12 }}
        isConnectable={true}
      />
      <div className="merge-node-header">
        <span className="merge-node-icon"></span>
        <span className="merge-node-title">{nodeData.label || '分支合并'}</span>
        <button 
          className="node-delete-btn"
          onClick={(e) => {
            e.stopPropagation();
            window.dispatchEvent(new CustomEvent('deleteNode', { detail: { nodeId: id } }));
          }}
        >
          ×
        </button>
      </div>
      <div className="merge-node-body">
        <Text type="secondary" style={{ fontSize: '11px', display: 'block' }}>
          汇聚多个分支路径
        </Text>
      </div>
      <Handle 
        type="source" 
        position={Position.Bottom} 
        id="output"
        style={{ background: '#1890ff', width: 12, height: 12 }}
        isConnectable={true}
      />
      {showAddButton && (
        <div className="node-add-button" onClick={handleAddClick}>
          <PlusOutlined />
        </div>
      )}
    </div>
  );
};

const nodeTypes = {
  action: ActionNode,
  condition: ConditionNode,
  ghost: GhostNode,
  merge: MergeNode,
};

const LogicOrchestrationCanvasContent = ({ orchestrationId }) => {
  const navigate = useNavigate();
  const reactFlowWrapper = useRef(null);
  const { screenToFlowPosition } = useReactFlow();
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [actionList, setActionList] = useState([]);
  const [actionListLoading, setActionListLoading] = useState(false);
  const [pendingEdgeSource, setPendingEdgeSource] = useState(null);
  const [ghostNode, setGhostNode] = useState(null);
  const [ghostEdge, setGhostEdge] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [workflowParams, setWorkflowParams] = useState([]);
  const [paramModalVisible, setParamModalVisible] = useState(false);
  const [paramForm] = Form.useForm();
  const [actionParamModalVisible, setActionParamModalVisible] = useState(false);
  const [actionParamNodeId, setActionParamNodeId] = useState(null);
  const [actionParamDefs, setActionParamDefs] = useState([]);
  const [actionParamValues, setActionParamValues] = useState({});
  const [actionParamForm] = Form.useForm();
  const [branchModalVisible, setBranchModalVisible] = useState(false);
  const [branchModalNodeId, setBranchModalNodeId] = useState(null);
  const [branchForm] = Form.useForm();
  const [editBranchModalVisible, setEditBranchModalVisible] = useState(false);
  const [editBranchNodeId, setEditBranchNodeId] = useState(null);
  const [editBranchIndex, setEditBranchIndex] = useState(null);
  const [editBranchForm] = Form.useForm();
  const [contextHandlerModalVisible, setContextHandlerModalVisible] = useState(false);
  const [contextHandlerNodeId, setContextHandlerNodeId] = useState(null);
  const [contextHandlerForm] = Form.useForm();
  const [contextHandlerValue, setContextHandlerValue] = useState('');  // 当前编辑的脚本内容
  const historyRef = useRef([]);
  const historyIndexRef = useRef(-1);
  const isUndoRedoRef = useRef(false);
  const getLayoutedElementsRef = useRef(null);
  const edgesRef = useRef(edges);
  edgesRef.current = edges;
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;

  // 加载编排数据
  useEffect(() => {
    if (orchestrationId) {
      const loadOrchestration = async () => {
        try {
          const res = await orchestrationApi.get(orchestrationId);
          const orchestration = res.data;
          if (orchestration?.graph_data) {
            // 收集 edges 上的条件信息（从条件分支出来的边带条件和标题）
            const branchInfoMap = {};  // { 'nodeId-branchIndex': { condition, title } }
            (orchestration.graph_data.edges || []).forEach(edge => {
              if (edge.sourceHandle?.startsWith('branch')) {
                const branchIndex = parseInt(edge.sourceHandle.replace('branch', ''), 10);
                const key = `${edge.source}-${branchIndex}`;
                if (!branchInfoMap[key]) {
                  branchInfoMap[key] = { condition: '', title: '' };
                }
                branchInfoMap[key].condition = edge.condition || branchInfoMap[key].condition;
                branchInfoMap[key].title = edge.branchTitle || branchInfoMap[key].title;
              }
            });

            // 通过 actionId 匹配获取完整 action 数据
            const loadedNodes = (orchestration.graph_data.nodes || []).map((node, idx) => {
              // 兼容旧格式（actionId 在根级别）和新格式（actionId 在 data 中）
              const nodeData = node.data || {};
              const actionId = node.actionId || nodeData.actionId;
              const matchedAction = actionList.find(a => a.id === actionId);
              
              // 计算默认位置，增加间距避免重叠
              const defaultPosition = node.position || { 
                x: 100, 
                y: 150 * idx + 50 
              };
              
              const baseData = {
                id: node.id || `loaded-node-${idx}`,
                type: node.type || 'action',
                position: defaultPosition,
                data: {
                  label: matchedAction?.name || nodeData.label || node.label || `Action ${actionId}` || node.id,
                  actionId: actionId,
                  apiName: matchedAction?.api_name || matchedAction?.name || '',
                  actionType: matchedAction?.action_type || matchedAction?.category || 'function',
                  category: matchedAction?.category || '其他',
                  description: matchedAction?.description || '',
                  params: matchedAction?.params || [],
                  paramValues: nodeData.paramValues || {},
                  contextHandler: nodeData.contextHandler || '',
                },
              };
              
              // 条件节点恢复标签和分支信息
              if (baseData.type === 'condition') {
                baseData.data.label = nodeData.label || node.label || '条件分支';
                // 优先从 nodeData.branches 恢复，否则从 edges 恢复
                if (nodeData.branches && nodeData.branches.length > 0) {
                  baseData.data.branches = nodeData.branches;
                } else {
                  // 从 edges 恢复分支信息
                  const nodeBranchKeys = Object.keys(branchInfoMap).filter(k => k.startsWith(`${baseData.id}-`));
                  if (nodeBranchKeys.length > 0) {
                    baseData.data.branches = nodeBranchKeys
                      .sort((a, b) => parseInt(a.split('-').pop()) - parseInt(b.split('-').pop()))
                      .map((key) => {
                        const info = branchInfoMap[key];
                        return { 
                          title: info.title || '分支', 
                          condition: info.condition || '' 
                        };
                      });
                  } else {
                    baseData.data.branches = [];
                  }
                }
              } else {
                baseData.data.branches = [];
              }
              
              return baseData;
            });
            
            // 对 edges 进行去重
            const seenIds = new Set();
            const loadedEdges = (orchestration.graph_data.edges || []).map((edge, idx) => {
              const edgeId = edge.id || `loaded-edge-${idx}`;
              let uniqueId = edgeId;
              let counter = 0;
              while (seenIds.has(uniqueId)) {
                counter++;
                uniqueId = `${edgeId}-${counter}`;
              }
              seenIds.add(uniqueId);
              return {
                id: uniqueId,
                source: edge.source,
                target: edge.target,
                sourceHandle: edge.sourceHandle || 'output',
                targetHandle: edge.targetHandle || 'input',
                type: edge.type || 'smoothstep',
                animated: true,
                style: { stroke: '#1890ff', strokeWidth: 2 },
              };
            });
            
            // 触发自动布局
            setTimeout(() => {
              const { nodes: layoutedNodes } = getLayoutedElements(loadedNodes, loadedEdges, 'TB');
              setNodes(layoutedNodes);
            }, 100);
            setEdges(loadedEdges);
          } else {
            setNodes([]);
            setEdges([]);
          }
          // inputs 保存在 graph_data 中
          if (orchestration.graph_data?.inputs !== undefined) {
            setWorkflowParams(Array.isArray(orchestration.graph_data.inputs) ? orchestration.graph_data.inputs : []);
          }
        } catch (err) {
          console.error('加载编排失败:', err);
          message.error('加载编排失败');
          setNodes([]);
          setEdges([]);
        }
      };
      loadOrchestration();
    }
  }, [orchestrationId, actionList, setNodes, setEdges]);

  // 辅助函数
  const collectDownstreamIds = useCallback((startId, currentEdges) => {
    const ids = new Set();
    const queue = [startId];
    while (queue.length > 0) {
      const current = queue.shift();
      if (ids.has(current)) continue;
      ids.add(current);
      currentEdges.forEach(e => {
        if (e.source === current && !ids.has(e.target)) {
          queue.push(e.target);
        }
      });
    }
    return ids;
  }, []);

  const remapGhostNodes = useCallback((nodes, parentId, deletedBranchIndex) => {
    return nodes.map(n => {
      if (n.type === 'ghost' && n.data?.parentId === parentId) {
        const oldIndex = n.data.branchIndex;
        if (oldIndex > deletedBranchIndex) {
          const newIndex = oldIndex - 1;
          return { ...n, id: `ghost-${parentId}-${newIndex}`, data: { ...n.data, branchIndex: newIndex } };
        }
      }
      return n;
    });
  }, []);

  const remapBranchEdges = useCallback((edges, parentId, deletedBranchIndex) => {
    return edges.map(e => {
      if (e.source === parentId && e.sourceHandle?.startsWith('branch')) {
        const idx = parseInt(e.sourceHandle.replace('branch', ''), 10);
        if (idx > deletedBranchIndex) {
          return { ...e, sourceHandle: `branch${idx - 1}` };
        }
      }
      return e;
    });
  }, []);

  // 事件监听
  useEffect(() => {
    const handleDeleteNode = (event) => {
      const { nodeId } = event.detail;
      const currentEdges = edgesRef.current;

      setNodes((nds) => {
        const deletedNode = nds.find(n => n.id === nodeId);
        if (!deletedNode) return nds;
        const downstreamIds = collectDownstreamIds(nodeId, currentEdges);

        let parentId = null;
        let branchIndex = null;
        if (deletedNode.type === 'ghost' && deletedNode.data?.parentId) {
          parentId = deletedNode.data.parentId;
          branchIndex = deletedNode.data.branchIndex;
        } else {
          const incomingEdge = currentEdges.find(e => e.target === nodeId);
          if (incomingEdge && incomingEdge.sourceHandle?.startsWith('branch')) {
            const sourceNode = nds.find(n => n.id === incomingEdge.source);
            if (sourceNode && sourceNode.type === 'condition') {
              parentId = sourceNode.id;
              branchIndex = parseInt(incomingEdge.sourceHandle.replace('branch', ''), 10);
            }
          }
        }

        let updatedNodes = nds;
        if (parentId !== null && branchIndex !== null) {
          updatedNodes = updatedNodes.map(n => {
            if (n.id === parentId && n.type === 'condition') {
              const newBranches = (n.data.branches || []).filter((_, idx) => idx !== branchIndex);
              return { ...n, data: { ...n.data, branches: newBranches } };
            }
            return n;
          });
          updatedNodes = updatedNodes.filter(n => !downstreamIds.has(n.id));
          updatedNodes = remapGhostNodes(updatedNodes, parentId, branchIndex);
        } else {
          updatedNodes = updatedNodes.filter(n => !downstreamIds.has(n.id));
        }
        return updatedNodes;
      });

      setEdges((eds) => {
        const currentNodes = nodesRef.current;
        const deletedNode = currentNodes.find(n => n.id === nodeId);
        const downstreamIds = collectDownstreamIds(nodeId, currentEdges);

        let parentId = null;
        let branchIndex = null;
        if (deletedNode && deletedNode.type === 'ghost' && deletedNode.data?.parentId) {
          parentId = deletedNode.data.parentId;
          branchIndex = deletedNode.data.branchIndex;
        } else if (deletedNode) {
          const incomingEdge = currentEdges.find(e => e.target === nodeId);
          if (incomingEdge && incomingEdge.sourceHandle?.startsWith('branch')) {
            const sourceNode = currentNodes.find(n => n.id === incomingEdge.source);
            if (sourceNode && sourceNode.type === 'condition') {
              parentId = sourceNode.id;
              branchIndex = parseInt(incomingEdge.sourceHandle.replace('branch', ''), 10);
            }
          }
        }

        let updatedEdges = eds.filter(e => !downstreamIds.has(e.source) && !downstreamIds.has(e.target));
        if (parentId !== null && branchIndex !== null) {
          updatedEdges = remapBranchEdges(updatedEdges, parentId, branchIndex);
        }
        return updatedEdges;
      });
      message.success('节点已删除');
    };

    const handleDeleteBranch = (event) => {
      const { nodeId, branchIndex } = event.detail;
      const currentEdges = edgesRef.current;

      setNodes((nds) => {
        const branchEdge = currentEdges.find(e => e.source === nodeId && e.sourceHandle === `branch${branchIndex}`);
        let downstreamIds = new Set();
        if (branchEdge) {
          downstreamIds = collectDownstreamIds(branchEdge.target, currentEdges);
        }

        let updatedNodes = nds.map(n => {
          if (n.id === nodeId && n.type === 'condition') {
            const newBranches = (n.data.branches || []).filter((_, idx) => idx !== branchIndex);
            return { ...n, data: { ...n.data, branches: newBranches } };
          }
          return n;
        });
        updatedNodes = updatedNodes.filter(n => !downstreamIds.has(n.id));
        updatedNodes = remapGhostNodes(updatedNodes, nodeId, branchIndex);
        return updatedNodes;
      });

      setEdges((eds) => {
        const branchEdge = currentEdges.find(e => e.source === nodeId && e.sourceHandle === `branch${branchIndex}`);
        let downstreamIds = new Set();
        if (branchEdge) {
          downstreamIds = collectDownstreamIds(branchEdge.target, currentEdges);
        }
        let updatedEdges = eds.filter(e => !downstreamIds.has(e.source) && !downstreamIds.has(e.target));
        updatedEdges = remapBranchEdges(updatedEdges, nodeId, branchIndex);
        return updatedEdges;
      });
      message.success('分支已删除');
    };

    const handleConfigActionParams = (event) => {
      const { nodeId, nodeData } = event.detail;
      setActionParamNodeId(nodeId);
      setActionParamDefs(nodeData.params || []);
      setActionParamValues(nodeData.paramValues || {});
      setActionParamModalVisible(true);
    };

    const handleRequestAddBranch = (event) => {
      const { nodeId } = event.detail;
      setBranchModalNodeId(nodeId);
      branchForm.resetFields();
      setBranchModalVisible(true);
    };

    const handleRequestEditBranch = (event) => {
      const { nodeId, branchIndex } = event.detail;
      setEditBranchNodeId(nodeId);
      setEditBranchIndex(branchIndex);
      setEditBranchModalVisible(true);
    };

    const handleConfigContextHandler = (event) => {
      const { nodeId, nodeData } = event.detail;
      setContextHandlerNodeId(nodeId);
      setContextHandlerModalVisible(true);
    };

    const handleUpdateConditionNode = (event) => {
      const { nodeId, updates } = event.detail;
      setNodes((nds) => nds.map(n => {
        if (n.id === nodeId) {
          return { ...n, data: { ...n.data, ...updates } };
        }
        return n;
      }));
    };

    const handleUpdateGhostNode = (event) => {
      const { nodeId, updates } = event.detail;
      setNodes((nds) => nds.map(n => {
        if (n.id === nodeId) {
          return { ...n, data: { ...n.data, ...updates } };
        }
        return n;
      }));
    };

    const handleCancelGhostNode = () => {
      setGhostNode(null);
      setGhostEdge(null);
      setPendingEdgeSource(null);
    };

    window.addEventListener('deleteNode', handleDeleteNode);
    window.addEventListener('deleteBranch', handleDeleteBranch);
    window.addEventListener('configActionParams', handleConfigActionParams);
    window.addEventListener('requestAddBranch', handleRequestAddBranch);
    window.addEventListener('requestEditBranch', handleRequestEditBranch);
    window.addEventListener('configContextHandler', handleConfigContextHandler);
    window.addEventListener('updateConditionNode', handleUpdateConditionNode);
    window.addEventListener('updateGhostNode', handleUpdateGhostNode);
    window.addEventListener('cancelGhostNode', handleCancelGhostNode);

    return () => {
      window.removeEventListener('deleteNode', handleDeleteNode);
      window.removeEventListener('deleteBranch', handleDeleteBranch);
      window.removeEventListener('configActionParams', handleConfigActionParams);
      window.removeEventListener('requestAddBranch', handleRequestAddBranch);
      window.removeEventListener('requestEditBranch', handleRequestEditBranch);
      window.removeEventListener('configContextHandler', handleConfigContextHandler);
      window.removeEventListener('updateConditionNode', handleUpdateConditionNode);
      window.removeEventListener('updateGhostNode', handleUpdateGhostNode);
      window.removeEventListener('cancelGhostNode', handleCancelGhostNode);
    };
  }, [collectDownstreamIds, remapGhostNodes, remapBranchEdges, branchForm]);

  // 当上下文处理弹窗打开时，从对应节点获取初始值
  useEffect(() => {
    if (contextHandlerModalVisible && contextHandlerNodeId) {
      const node = nodes.find(n => n.id === contextHandlerNodeId);
      if (node && node.data) {
        setContextHandlerValue(node.data.contextHandler || '');
      }
    }
  }, [contextHandlerModalVisible, contextHandlerNodeId, nodes]);

  // 确认添加分支
  const handleAddBranch = useCallback(async () => {
    try {
      const values = await branchForm.validateFields();
      const { branchTitle, branchCondition } = values;
      const nodeId = branchModalNodeId;
      
      // 先计算需要的值，在 setNodes 之前
      const sourceNodeForCalc = nodes.find(n => n.id === nodeId);
      if (!sourceNodeForCalc) return;
      
      const currentBranchesCount = (sourceNodeForCalc.data?.branches || []).length;
      const newBranchIndex = currentBranchesCount;
      const branchColor = newBranchIndex === 0 ? '#52c41a' : newBranchIndex === 1 ? '#f5222d' : '#faad14';
      const ghostId = `ghost-${nodeId}-${newBranchIndex}`;
      
      setNodes((currentNodes) => {
        const sourceNode = currentNodes.find(n => n.id === nodeId);
        if (!sourceNode) return currentNodes;
        
        const currentBranches = sourceNode.data.branches || [];
        const newBranch = { title: branchTitle, condition: branchCondition };
        const newBranches = [...currentBranches, newBranch];
        
        // 先添加分支信息但不加 ghost，先布局获取条件节点的新位置
        const updatedNodes = currentNodes.map(n => {
          if (n.id === nodeId) {
            return { ...n, data: { ...n.data, branches: newBranches } };
          }
          return n;
        });
        
        // 先对已有节点布局，获取条件节点布局后的位置
        const { nodes: layoutedNodes } = getLayoutedElementsRef.current(updatedNodes, edgesRef.current, 'TB');
        
        // 根据布局后的条件节点位置计算 ghost 节点位置
        const layoutedConditionNode = layoutedNodes.find(n => n.id === nodeId);
        const nodeWidth = 220;
        const verticalGap = 120;
        const horizontalGap = 80;
        const conditionHeight = getConditionNodeHeight(layoutedConditionNode);
        const ghostX = layoutedConditionNode.position.x + nodeWidth + newBranchIndex * (nodeWidth + horizontalGap);
        const ghostY = layoutedConditionNode.position.y + conditionHeight + verticalGap;
        
        const newGhostNode = {
          id: ghostId,
          type: 'ghost',
          position: { x: ghostX, y: ghostY },
          data: { label: `${branchTitle} 分支`, parentId: nodeId, branchIndex: newBranchIndex },
        };
        
        // 将 ghost 加入最终节点列表
        return [...layoutedNodes, newGhostNode];
      });
      
      // 在节点添加完成后，再添加边（参考普通节点 onConnect 的延迟逻辑）
      setTimeout(() => {
        setEdges((currentEdges) => {
          // 检查边是否已存在
          const exists = currentEdges.some(e => 
            e.source === nodeId && 
            e.target === ghostId
          );
          if (exists) return currentEdges;
          return [...currentEdges, {
            id: `edge-${nodeId}-${ghostId}-${Date.now()}`,
            source: nodeId,
            target: ghostId,
            sourceHandle: `branch${newBranchIndex}`,
            targetHandle: 'input',
            type: 'smoothstep',
            animated: true,
            style: { stroke: branchColor, strokeWidth: 2, strokeDasharray: '5,5' },
            markerEnd: { type: 'arrowclosed', color: branchColor },
            label: branchTitle,
            labelStyle: { fill: branchColor, fontWeight: 'bold', fontSize: '12px' },
            labelBgStyle: { fill: '#fff', fillOpacity: 0.8 },
          }];
        });
      }, 300);
      
      setBranchModalVisible(false);
      message.success(`已添加分支: ${branchTitle}`);
    } catch {}
  }, [branchForm, branchModalNodeId, nodes, setNodes, setEdges]);

  // 保存编辑分支
  const handleSaveEditBranch = useCallback(async () => {
    try {
      const values = await editBranchForm.validateFields();
      const { branchTitle, branchCondition } = values;
      
      if (editBranchNodeId !== null && editBranchIndex !== null) {
        setNodes((currentNodes) => {
          return currentNodes.map(n => {
            if (n.id === editBranchNodeId && n.type === 'condition') {
              const newBranches = [...(n.data.branches || [])];
              newBranches[editBranchIndex] = { 
                title: branchTitle, 
                condition: branchCondition 
              };
              return { ...n, data: { ...n.data, branches: newBranches } };
            }
            return n;
          });
        });
      }
      
      setEditBranchModalVisible(false);
      message.success('分支已更新');
    } catch {}
  }, [editBranchForm, editBranchNodeId, editBranchIndex, setNodes]);

  // 监听添加连线事件
  useEffect(() => {
    const handleAddEdgeEvent = (event) => {
      const { nodeId, nodeData, branchIndex } = event.detail;
      setPendingEdgeSource({ nodeId, nodeData, branchIndex });
      
      const sourceNode = nodes.find(n => n.id === nodeId);
      if (sourceNode) {
        const nodeWidth = 220;
        const verticalGap = 120;
        const horizontalGap = 80;
        const conditionHeight = getConditionNodeHeight(sourceNode);
        
        // ghost 节点位置：普通节点在正下方，条件分支在右下侧
        let ghostX, ghostY;
        if (nodeData.actionType === '条件分支' && branchIndex !== undefined) {
          ghostX = sourceNode.position.x + nodeWidth + branchIndex * (nodeWidth + horizontalGap);
          ghostY = sourceNode.position.y + conditionHeight + verticalGap;
        } else {
          ghostX = sourceNode.position.x;
          ghostY = sourceNode.position.y + getNodeHeight(sourceNode) + verticalGap;
        }
        
        const ghostNodeData = { label: '拖拽 Action 到这里' };
        // 保存来源信息，以便 onDrop 中正确判断连线来源
        if (nodeData.actionType === '条件分支' && branchIndex !== undefined) {
          ghostNodeData.parentId = nodeId;
          ghostNodeData.branchIndex = branchIndex;
        }
        
        setGhostNode({
          id: 'ghost-node',
          type: 'ghost',
          position: { x: ghostX, y: ghostY },
          data: ghostNodeData,
        });
        
        const sourceHandle = nodeData.actionType === '条件分支' && branchIndex !== undefined ? `branch${branchIndex}` : 'output';
        
        setGhostEdge({
          id: 'ghost-edge',
          source: nodeId,
          target: 'ghost-node',
          sourceHandle: sourceHandle,
          targetHandle: 'input',
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#1890ff', strokeWidth: 2, strokeDasharray: '5,5' },
          markerEnd: { type: 'arrowclosed', color: '#1890ff' },
        });
      }
      message.info(`请拖拽 Action 到画布中的虚线框`);
    };

    window.addEventListener('addEdgeFromNode', handleAddEdgeEvent);
    return () => window.removeEventListener('addEdgeFromNode', handleAddEdgeEvent);
  }, [nodes]);

  // 获取 Action 列表
  useEffect(() => {
    const fetchActions = async () => {
      setActionListLoading(true);
      try {
        const res = await actionApi.getAll();
        const actions = (res.data || []).map(a => ({
          id: a.id,
          name: a.name,
          api_name: a.api_name || a.name,
          description: a.description || '',
          action_type: a.action_type || 'function',
          params: a.parameters || [],
          category: a.category || '其他',
        }));
        setActionList(actions);
      } catch (err) {
        console.error('获取 Action 列表失败:', err);
        message.error('获取 Action 列表失败');
        setActionList([]);
      } finally {
        setActionListLoading(false);
      }
    };
    fetchActions();
  }, []);

  const filteredActions = useMemo(() => {
    return actionList.filter(action => {
      const matchSearch = action.name.toLowerCase().includes(searchText.toLowerCase()) ||
                         action.api_name.toLowerCase().includes(searchText.toLowerCase()) ||
                         action.id.toLowerCase().includes(searchText.toLowerCase());
      const matchCategory = categoryFilter === 'all' || action.action_type === categoryFilter;
      return matchSearch && matchCategory;
    });
  }, [actionList, searchText, categoryFilter]);

  const categories = useMemo(() => {
    const cats = [...new Set(actionList.map(a => a.action_type))];
    return ['all', ...cats];
  }, [actionList]);

  const onDragStart = (event, action) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(action));
    event.dataTransfer.effectAllowed = 'move';
    setIsDragging(true);
  };

  const onDragStartCondition = (event) => {
    const conditionAction = {
      id: 'condition_branch',
      name: '条件分支',
      description: '根据条件进行分支判断',
      action_type: 'condition',
    };
    event.dataTransfer.setData('application/reactflow', JSON.stringify(conditionAction));
    event.dataTransfer.effectAllowed = 'move';
    setIsDragging(true);
  };

  const onDragEnd = useCallback(() => {
    setIsDragging(false);
    setGhostNode(null);
    setGhostEdge(null);
  }, []);

  const displayNodes = useMemo(() => ghostNode ? [...nodes, ghostNode] : nodes, [nodes, ghostNode]);
  const displayEdges = useMemo(() => ghostEdge ? [...edges, ghostEdge] : edges, [edges, ghostEdge]);

  // 计算条件分支节点的动态高度
  const getConditionNodeHeight = (node) => {
    const branchCount = node.data?.branches?.length || 0;
    // 基础高度 + 每个分支行的高度 + 添加按钮高度
    const baseHeight = 80; // 头部和描述区域
    const branchRowHeight = 56; // 每个分支行的高度
    const addButtonHeight = 40; // 添加按钮区域
    return baseHeight + branchCount * branchRowHeight + addButtonHeight;
  };

  // 计算节点的高度
  const getNodeHeight = (node) => {
    if (node.type === 'condition') {
      return getConditionNodeHeight(node);
    }
    if (node.type === 'merge') {
      return 100;
    }
    return 130; // action node 默认高度
  };

  const getLayoutedElements = useCallback((nodes, edges, direction = 'TB') => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    const nodeWidth = 220;
    const baseNodeHeight = 130;

    dagreGraph.setGraph({ 
      rankdir: direction, 
      nodesep: 80, 
      ranksep: 150, 
      marginx: 100, 
      marginy: 100, 
      align: 'DL', 
      ranker: 'network-simplex', 
      edgesep: 50,
    });

    const layoutNodes = nodes.filter(n => n.id.startsWith('ghost-') ? false : true);
    const layoutEdges = edges.filter(e => e.target.startsWith('ghost-') ? false : true);

    // 为每个节点设置动态高度
    layoutNodes.forEach((node) => {
      const height = getNodeHeight(node);
      dagreGraph.setNode(node.id, { width: nodeWidth, height });
    });

    layoutEdges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    // 第一轮布局后，调整条件分支各分支下的子节点位置
    let layoutedNodes = nodes.map((node) => {
      if (node.id.startsWith('ghost-')) return node; // ghost node 保持原位置
      const nodeWithPosition = dagreGraph.node(node.id);
      if (!nodeWithPosition) return node;
      const height = getNodeHeight(node);
      return {
        ...node,
        position: { x: nodeWithPosition.x - nodeWidth / 2, y: nodeWithPosition.y - height / 2 },
        style: { width: nodeWidth, height },
      };
    });

    // 处理条件分支节点的子节点水平分布
    layoutedNodes = adjustConditionBranchLayout(layoutedNodes, edges, nodeWidth);

    // 处理普通节点（action/merge）的子节点：确保在父节点正下方
    layoutedNodes = adjustActionChildLayout(layoutedNodes, edges, nodeWidth);

    return { nodes: layoutedNodes, edges };
  }, []);

  // 调整条件分支下各分支子节点的布局 - 子节点在右下侧水平对齐
  const adjustConditionBranchLayout = useCallback((nodes, edges, nodeWidth) => {
    const conditionNodes = nodes.filter(n => n.type === 'condition');
    let adjustedNodes = [...nodes];

    conditionNodes.forEach(conditionNode => {
      const branches = conditionNode.data?.branches || [];
      const branchCount = branches.length;
      if (branchCount === 0) return;

      // 计算条件分支节点高度
      const conditionHeight = getConditionNodeHeight(conditionNode);
      const conditionX = conditionNode.position.x;
      const conditionY = conditionNode.position.y;
      
      // 子节点放在条件分支右下侧，水平对齐
      const verticalGap = 120; // 垂直间距
      const horizontalGap = 80; // 水平间距
      const childY = conditionY + conditionHeight + verticalGap;

      // 获取从该条件分支各分支出来的边和子节点
      branches.forEach((branch, branchIndex) => {
        const sourceHandle = `branch${branchIndex}`;
        const branchEdge = edges.find(e => e.source === conditionNode.id && e.sourceHandle === sourceHandle);
        if (!branchEdge) return;

        const childNodeId = branchEdge.target;
        const childNodeIndex = adjustedNodes.findIndex(n => n.id === childNodeId);
        if (childNodeIndex === -1) return;

        const childNode = adjustedNodes[childNodeIndex];

        // 子节点 x 坐标：从条件分支右侧开始，依次向右排列
        // conditionX 是条件分支左边界，+nodeWidth 后是右边界
        // 子节点0在条件分支右侧，子节点1、2...依次向右
        const childX = conditionX + nodeWidth + branchIndex * (nodeWidth + horizontalGap);

        adjustedNodes[childNodeIndex] = {
          ...childNode,
          position: {
            x: childX,
            y: childY,
          },
        };
      });
    });

    return adjustedNodes;
  }, []);

  // 调整普通节点（action/merge）的子节点布局 - 子节点在父节点正下方
  const adjustActionChildLayout = useCallback((nodes, edges, nodeWidth) => {
    let adjustedNodes = [...nodes];
    const verticalGap = 150; // 与 dagre ranksep 保持一致

    // 找出所有被条件分支调整过的子节点 ID，这些节点不再处理
    const conditionChildIds = new Set();
    const conditionNodes = nodes.filter(n => n.type === 'condition');
    conditionNodes.forEach(condNode => {
      const branches = condNode.data?.branches || [];
      branches.forEach((_, branchIndex) => {
        const sourceHandle = `branch${branchIndex}`;
        const branchEdge = edges.find(e => e.source === condNode.id && e.sourceHandle === sourceHandle);
        if (branchEdge) {
          conditionChildIds.add(branchEdge.target);
        }
      });
    });

    // 收集每个非条件节点的 "output" 边对应的子节点
    adjustedNodes.forEach((node) => {
      if (node.type === 'condition') return; // 条件节点由 adjustConditionBranchLayout 处理
      if (node.id.startsWith('ghost-')) return;

      // 找出从该节点 output 出发的边（排除条件分支的 branch 边）
      const outputEdges = edges.filter(e => 
        e.source === node.id && 
        e.sourceHandle === 'output' &&
        !conditionChildIds.has(e.target)
      );

      if (outputEdges.length === 0) return;

      const parentNode = adjustedNodes.find(n => n.id === node.id);
      if (!parentNode) return;

      const parentHeight = getNodeHeight(parentNode);

      outputEdges.forEach((edge) => {
        const childIndex = adjustedNodes.findIndex(n => n.id === edge.target);
        if (childIndex === -1) return;

        const childNode = adjustedNodes[childIndex];
        if (childNode.id.startsWith('ghost-')) return;

        // 子节点 x 坐标与父节点对齐（正下方）
        const childX = parentNode.position.x;
        const childY = parentNode.position.y + parentHeight + verticalGap;

        adjustedNodes[childIndex] = {
          ...childNode,
          position: {
            x: childX,
            y: childY,
          },
        };
      });
    });

    return adjustedNodes;
  }, []);

  getLayoutedElementsRef.current = getLayoutedElements;

  const pushHistory = useCallback((currentNodes, currentEdges) => {
    if (isUndoRedoRef.current) return;
    const snapshot = {
      nodes: JSON.parse(JSON.stringify(currentNodes)),
      edges: JSON.parse(JSON.stringify(currentEdges)),
    };
    const newHistory = [...historyRef.current, snapshot];
    if (newHistory.length > 50) newHistory.shift();
    historyRef.current = newHistory;
    historyIndexRef.current = newHistory.length - 1;
  }, []);

  const handleUndo = useCallback(() => {
    if (historyIndexRef.current <= 0) {
      message.info('没有可撤回的操作');
      return;
    }
    historyIndexRef.current -= 1;
    isUndoRedoRef.current = true;
    const snapshot = historyRef.current[historyIndexRef.current];
    setNodes(snapshot.nodes);
    setEdges(snapshot.edges);
    isUndoRedoRef.current = false;
    message.success('已撤回');
  }, [setNodes, setEdges]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        handleUndo();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleUndo]);

  useEffect(() => {
    if (isUndoRedoRef.current) return;
    if (nodes.length === 0 && edges.length === 0 && historyRef.current.length === 0) return;
    const timer = setTimeout(() => {
      pushHistory(nodes, edges);
    }, 300);
    return () => clearTimeout(timer);
  }, [nodes, edges, pushHistory]);

  const onDrop = useCallback((event) => {
    event.preventDefault();
    const actionData = event.dataTransfer.getData('application/reactflow');
    if (!actionData) return;

    const action = JSON.parse(actionData);
    const dropPosition = screenToFlowPosition({ x: event.clientX, y: event.clientY });
    
    let targetGhostNode = null;
    const ghostNodeWidth = 220;
    const ghostNodeHeight = 130;
    
    nodes.forEach(node => {
      if (node.type === 'ghost' && node.id.startsWith('ghost-')) {
        const nodeCenterX = node.position.x + ghostNodeWidth / 2;
        const nodeCenterY = node.position.y + ghostNodeHeight / 2;
        const dx = dropPosition.x - nodeCenterX;
        const dy = dropPosition.y - nodeCenterY;
        if (Math.abs(dx) < ghostNodeWidth / 2 && Math.abs(dy) < ghostNodeHeight / 2) {
          targetGhostNode = node;
        }
      }
    });
    
    let position;
    if (targetGhostNode) {
      position = { ...targetGhostNode.position };
    } else if (ghostNode) {
      position = ghostNode.position;
    } else {
      position = dropPosition;
    }

    let newNode;
    
    if (action.action_type === 'condition') {
      newNode = {
        id: `${action.id}-${Date.now()}`,
        type: 'condition',
        position,
        data: {
          label: action.name,
          actionId: action.id,
          apiName: action.api_name,
          actionType: '条件分支',
          category: action.category,
          description: action.description,
          condition: '',
          branches: [],
        },
      };
    } else {
      newNode = {
        id: `${action.id}-${Date.now()}`,
        type: 'action',
        position,
        data: {
          label: action.name,
          actionId: action.id,
          apiName: action.api_name,
          actionType: action.action_type,
          category: action.category,
          description: action.description,
          params: action.params || [],
          paramValues: {},
        },
      };
    }

    setNodes((nds) => {
      let nodesWithoutGhost = nds.filter(n => n.id !== 'ghost-node');
      if (targetGhostNode) {
        nodesWithoutGhost = nodesWithoutGhost.filter(n => n.id !== targetGhostNode.id);
      }
      const updatedNodes = [...nodesWithoutGhost, newNode];
      // 传入当前最新的边（去除指向 ghost 的边），确保布局时能正确处理条件分支子节点
      const currentEdges = edgesRef.current.filter(e => e.target !== 'ghost-node' && (!targetGhostNode || e.target !== targetGhostNode.id));
      const { nodes: layoutedNodes } = getLayoutedElements(updatedNodes, currentEdges, 'TB');
      return layoutedNodes;
    });
    
    if (ghostNode) {
      setGhostNode(null);
      setGhostEdge(null);
    }

    let sourceNodeId = null;
    let sourceNodeData = null;
    let sourceBranchIndex = null;
    let sourceHandle = 'output';
    let branchColor = '#1890ff';
    
    if (targetGhostNode && targetGhostNode.data.parentId) {
      sourceNodeId = targetGhostNode.data.parentId;
      sourceBranchIndex = targetGhostNode.data.branchIndex;
      const sourceNode = nodes.find(n => n.id === sourceNodeId);
      if (sourceNode) {
        sourceNodeData = sourceNode.data;
        sourceHandle = `branch${sourceBranchIndex !== undefined ? sourceBranchIndex : 0}`;
      }
      branchColor = sourceBranchIndex === 0 ? '#52c41a' : sourceBranchIndex === 1 ? '#f5222d' : '#faad14';
    } else if (ghostNode && ghostNode.data.parentId) {
      sourceNodeId = ghostNode.data.parentId;
      sourceBranchIndex = ghostNode.data.branchIndex;
      const sourceNode = nodes.find(n => n.id === sourceNodeId);
      if (sourceNode) {
        sourceNodeData = sourceNode.data;
        sourceHandle = `branch${sourceBranchIndex || 0}`;
      }
      branchColor = sourceBranchIndex === 0 ? '#52c41a' : sourceBranchIndex === 1 ? '#f5222d' : '#faad14';
    } else if (pendingEdgeSource) {
      sourceNodeId = pendingEdgeSource.nodeId;
      sourceNodeData = pendingEdgeSource.nodeData;
      sourceBranchIndex = pendingEdgeSource.branchIndex;
      sourceHandle = sourceNodeData.actionType === '条件分支' ? `branch${sourceBranchIndex || 0}` : 'output';
      branchColor = sourceBranchIndex === 0 ? '#52c41a' : sourceBranchIndex === 1 ? '#f5222d' : '#faad14';
    }
    
    if (sourceNodeId) {
      // 从 branches 获取该分支的条件
      const branchCondition = sourceBranchIndex !== null && sourceBranchIndex !== undefined && sourceNodeData?.branches?.[sourceBranchIndex]
        ? (typeof sourceNodeData.branches[sourceBranchIndex] === 'object' ? sourceNodeData.branches[sourceBranchIndex].condition : '') : '';
      
      if (targetGhostNode) {
        setEdges((eds) => {
          const filteredEdges = eds.filter(e => e.target !== targetGhostNode.id);
          const newEdge = {
            id: `edge-${sourceNodeId}-${newNode.id}-${Date.now()}`,
            source: sourceNodeId,
            target: newNode.id,
            sourceHandle: sourceHandle,
            targetHandle: 'input',
            type: 'smoothstep',
            animated: true,
            style: { stroke: branchColor, strokeWidth: 2 },
            condition: branchCondition,  // 保存条件到 edge 上
            label: sourceBranchIndex !== null && sourceNodeData?.branches?.[sourceBranchIndex] 
              ? (typeof sourceNodeData.branches[sourceBranchIndex] === 'object' ? sourceNodeData.branches[sourceBranchIndex].title : sourceNodeData.branches[sourceBranchIndex]) : undefined,
            labelStyle: { fill: branchColor, fontWeight: 'bold', fontSize: '12px' },
            labelBgStyle: { fill: '#fff', fillOpacity: 0.8 },
          };
          const updatedEdges = addEdge(newEdge, filteredEdges);
          setTimeout(() => {
            setNodes((nds) => {
              const { nodes: layoutedNodes } = getLayoutedElements(nds, updatedEdges, 'TB');
              return layoutedNodes;
            });
          }, 100);
          return updatedEdges;
        });
      } else {
        setEdges((eds) => {
          const newEdge = {
            id: `edge-${sourceNodeId}-${newNode.id}-${Date.now()}`,
            source: sourceNodeId,
            target: newNode.id,
            sourceHandle: sourceHandle,
            targetHandle: 'input',
            type: 'smoothstep',
            animated: true,
            style: { stroke: branchColor, strokeWidth: 2 },
            condition: branchCondition,  // 保存条件到 edge 上
          };
          const updatedEdges = addEdge(newEdge, eds);
          setTimeout(() => {
            setNodes((nds) => {
              const { nodes: layoutedNodes } = getLayoutedElements(nds, updatedEdges, 'TB');
              return layoutedNodes;
            });
          }, 100);
          return updatedEdges;
        });
      }
      const branchLabel = sourceBranchIndex !== null && sourceBranchIndex !== undefined ? ` (分支${sourceBranchIndex})` : '';
      message.success(`已连接: ${sourceNodeData?.label || '条件分支'}${branchLabel} → ${action.name}`);
    } else {
      message.success(`已添加节点: ${action.name}`);
    }
    
    setPendingEdgeSource(null);
  }, [screenToFlowPosition, setNodes, setEdges, pendingEdgeSource, ghostNode, ghostEdge, edges, getLayoutedElements, nodes]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onConnect = useCallback((params) => {
    // 获取源节点和分支条件
    let condition = '';
    let branchColor = '#1890ff';
    
    if (params.sourceHandle?.startsWith('branch')) {
      const sourceNode = nodes.find(n => n.id === params.source);
      if (sourceNode && sourceNode.type === 'condition') {
        const branchIndex = parseInt(params.sourceHandle.replace('branch', ''), 10);
        const branches = sourceNode.data.branches || [];
        if (branches[branchIndex]) {
          condition = branches[branchIndex].condition || '';
        }
        branchColor = branchIndex === 0 ? '#52c41a' : branchIndex === 1 ? '#f5222d' : '#faad14';
      }
    }
    
    const edge = {
      ...params,
      animated: true,
      style: { stroke: branchColor, strokeWidth: 2 },
      condition,  // 保存条件到 edge 上
    };
    
    if (params.sourceHandle === 'true') {
      edge.label = 'True';
    } else if (params.sourceHandle === 'false') {
      edge.label = 'False';
    } else if (params.sourceHandle?.startsWith('branch')) {
      edge.label = params.sourceHandle.replace('branch', '分支 ');
    }
    
    setEdges((eds) => {
      const updatedEdges = addEdge(edge, eds);
      setTimeout(() => {
        setNodes((nds) => {
          const { nodes: layoutedNodes } = getLayoutedElements(nds, updatedEdges, 'TB');
          return layoutedNodes;
        });
      }, 100);
      return updatedEdges;
    });
  }, [setEdges, getLayoutedElements, nodes]);

  const toDAGData = useCallback(() => {
    const realNodes = nodes.filter(n => n.type !== 'ghost');
    const realEdges = edges.filter(e => {
      const targetNode = nodes.find(n => n.id === e.target);
      return targetNode && targetNode.type !== 'ghost';
    });

    // 构建 nodeId -> index 的映射
    const nodeIndexMap = {};
    realNodes.forEach((n, idx) => { nodeIndexMap[n.id] = idx; });

    return {
      // 保存节点数据，包括条件分支的标签和分支信息
      nodes: realNodes.map(n => {
        const nodeData = {
          id: n.id,
          type: n.type,
          position: n.position,
          data: {
            actionId: n.data.actionId,
            paramValues: n.data.paramValues || {},
            contextHandler: n.data.contextHandler || '',
          },
        };
        // 条件节点保存标签和分支信息
        if (n.type === 'condition') {
          nodeData.data.label = n.data.label || '条件分支';
          nodeData.data.branches = n.data.branches || [];
        }
        return nodeData;
      }),
      // 条件分支的条件放在 edges 上
      edges: realEdges.map(e => {
        const edgeData = {
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle,
          targetHandle: e.targetHandle,
        };
        // 如果是从条件分支出来的边，附加该分支的条件和标题
        if (e.sourceHandle?.startsWith('branch')) {
          const sourceNode = realNodes.find(n => n.id === e.source);
          if (sourceNode && sourceNode.type === 'condition') {
            const branchIndex = parseInt(e.sourceHandle.replace('branch', ''), 10);
            const branches = sourceNode.data.branches || [];
            if (branches[branchIndex]) {
              edgeData.condition = branches[branchIndex].condition || '';
              edgeData.branchTitle = branches[branchIndex].title || '';
            }
          }
        }
        return edgeData;
      }),
    };
  }, [nodes, edges]);

  const handleOpenParamModal = useCallback(() => {
    setParamModalVisible(true);
  }, []);

  const handleParamModalOpenChange = useCallback((open) => {
    if (open) {
      setTimeout(() => {
        paramForm.setFieldsValue({
          params: workflowParams.length > 0
            ? workflowParams.map(p => ({ ...p }))
            : [{ name: '', type: 'string', required: false, defaultValue: '', description: '' }],
        });
      }, 50);
    }
  }, [workflowParams, paramForm]);

  const handleSaveParams = useCallback(async () => {
    try {
      const values = await paramForm.validateFields();
      const params = (values.params || []).filter(p => p.name);
      setWorkflowParams(params);
      setParamModalVisible(false);
      message.success(`已配置 ${params.length} 个入参`);
    } catch {}
  }, [paramForm]);

  // 编辑分支弹窗打开后回显数据
  const handleEditBranchModalOpenChange = useCallback((open) => {
    if (open && editBranchNodeId !== null && editBranchIndex !== null) {
      const node = nodes.find(n => n.id === editBranchNodeId);
      if (node && node.data.branches && node.data.branches[editBranchIndex]) {
        const branch = node.data.branches[editBranchIndex];
        setTimeout(() => {
          editBranchForm.setFieldsValue({
            branchTitle: branch.title || '',
            branchCondition: branch.condition || '',
          });
        }, 50);
      } else {
        editBranchForm.resetFields();
      }
    }
  }, [editBranchNodeId, editBranchIndex, nodes, editBranchForm]);

  const handleSaveActionParams = useCallback(async () => {
    try {
      const values = await actionParamForm.validateFields();
      const paramValues = {};
      actionParamDefs.forEach(p => {
        const val = values[p.name];
        if (val !== undefined && val !== '') {
          paramValues[p.name] = val;
        }
      });
      setNodes((nds) => nds.map(n => {
        if (n.id === actionParamNodeId) {
          return { ...n, data: { ...n.data, paramValues } };
        }
        return n;
      }));
      setActionParamModalVisible(false);
      const configured = Object.keys(paramValues).length;
      message.success(configured > 0 ? `已配置 ${configured} 个参数` : '已清除参数配置');
    } catch {}
  }, [actionParamForm, actionParamNodeId, actionParamDefs, setNodes]);

  // 保存上下文处理脚本
  const handleSaveContextHandler = useCallback(async () => {
    try {
      // 直接使用 state 中的值（通过 onChange 实时更新）
      const inputValue = contextHandlerValue;
      const hasContent = inputValue.replace(/\s/g, '').length > 0;
      const contextHandler = hasContent ? inputValue : '';
      setNodes((nds) => nds.map(n => {
        if (n.id === contextHandlerNodeId) {
          return { ...n, data: { ...n.data, contextHandler } };
        }
        return n;
      }));
      setContextHandlerModalVisible(false);
      if (contextHandler) {
        message.success('上下文处理脚本已保存');
      } else {
        message.info('已清除上下文处理脚本');
      }
    } catch {}
  }, [contextHandlerValue, contextHandlerNodeId, setNodes]);

  // 保存编排
  const handleSave = useCallback(async () => {
    const flowData = toDAGData();
    flowData.inputs = workflowParams;
    
    try {
      await orchestrationApi.update(orchestrationId, { graph_data: flowData });
      message.success('流程已保存');
    } catch (err) {
      message.error('保存失败');
    }
  }, [toDAGData, workflowParams, orchestrationId]);

  const handleExport = useCallback(() => {
    const flowData = toDAGData();
    flowData.inputs = workflowParams;
    const blob = new Blob([JSON.stringify(flowData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dag-flow.json';
    a.click();
    URL.revokeObjectURL(url);
    message.success('流程已导出');
  }, [toDAGData, workflowParams]);

  const handleClear = useCallback(() => {
    setNodes([]);
    setEdges([]);
    message.info('画布已清空');
  }, [setNodes, setEdges]);

  return (
    <div className="logic-orchestration-container">
      <div className="orchestration-layout">
        <div className="action-list-panel">
          <Card 
            title="📦 Action 列表" 
            size="small"
            className="action-list-card"
            loading={actionListLoading}
          >
            <div className="action-list-filters">
              <Search
                placeholder="搜索 Action"
                prefix={<SearchOutlined />}
                size="small"
                onChange={(e) => setSearchText(e.target.value)}
                style={{ marginBottom: 8 }}
              />
              <Select
                size="small"
                value={categoryFilter}
                onChange={setCategoryFilter}
                style={{ width: '100%', marginBottom: 8 }}
              >
                {categories.map(cat => (
                  <Select.Option key={cat} value={cat}>
                    {cat === 'all' ? '全部分类' : cat}
                  </Select.Option>
                ))}
              </Select>
            </div>
            <List
              size="small"
              dataSource={filteredActions}
              renderItem={(action) => (
                <List.Item
                  className="action-list-item"
                  draggable
                  onDragStart={(e) => onDragStart(e, action)}
                >
                  <div className="action-item-content">
                    <div className="action-item-header">
                      <span className="action-item-icon"></span>
                      <span className="action-item-name">{action.name}</span>
                    </div>
                    <div className="action-item-desc">{action.api_name}</div>
                    <div className="action-item-desc">{action.description}</div>
                    <Tag color="blue" style={{ marginTop: 4, fontSize: '10px' }}>
                      {action.action_type}
                    </Tag>
                  </div>
                </List.Item>
              )}
            />
            <div className="action-list-hint">
              <Text type="secondary" style={{ fontSize: '11px' }}>
                💡 拖拽 Action 到右侧画布
              </Text>
            </div>
          </Card>
        </div>

        <div className="canvas-panel">
          <Card
            title={
              <Space>
                <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/logic-orchestration')} size="small" />
                <Title level={4} style={{ margin: 0 }}>DAG 流程编排画布</Title>
              </Space>
            }
            extra={
              <Space>
                <Button icon={<UndoOutlined />} onClick={handleUndo} size="small" title="撤回 (Ctrl+Z)">撤回</Button>
                <Button icon={<BranchesOutlined />} draggable onDragStart={onDragStartCondition} size="small" style={{ cursor: 'grab' }}>条件分支</Button>
                <Button icon={<SettingOutlined />} onClick={handleOpenParamModal} size="small">入参配置</Button>
                <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} size="small">保存</Button>
                <Button icon={<DownloadOutlined />} onClick={handleExport} size="small">导出</Button>
                <Button danger icon={<DeleteOutlined />} onClick={handleClear} size="small">清空</Button>
              </Space>
            }
            className="canvas-card"
          >
            <div 
              ref={reactFlowWrapper} 
              className={`reactflow-wrapper ${isDragging ? 'dragging-active' : ''}`}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragEnd}
            >
              <ReactFlow
                nodes={displayNodes}
                edges={displayEdges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                nodeTypes={nodeTypes}
                minZoom={0.2}
                maxZoom={2}
                connectionLineType="smoothstep"
                defaultEdgeOptions={{ type: 'smoothstep', animated: true, style: { stroke: '#1890ff', strokeWidth: 2 } }}
                nodesDraggable={false}
                nodesConnectable={true}
                elementsSelectable={true}
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
      </div>

      {/* 工作流入参配置弹窗 */}
      <Modal title="工作流入参配置" open={paramModalVisible} onOk={handleSaveParams} onCancel={() => setParamModalVisible(false)} width={720} okText="确认" cancelText="取消" destroyOnHidden afterOpenChange={handleParamModalOpenChange}>
        <Form form={paramForm} layout="vertical">
          <div className="param-row param-header">
            <span style={{ flex: 2 }}>参数名</span>
            <span style={{ flex: 1 }}>类型</span>
            <span style={{ flex: '0 0 80px', textAlign: 'center' }}>是否必填</span>
            <span style={{ flex: 1 }}>默认值</span>
            <span style={{ flex: 2 }}>说明</span>
            <span style={{ flex: '0 0 52px' }}></span>
          </div>
          <Form.List name="params">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <div key={key} className="param-row">
                    <Form.Item {...restField} name={[name, 'name']} rules={[{ required: true, message: '请输入参数名' }]} style={{ flex: 2, marginBottom: 0 }}>
                      <Input placeholder="如: score" size="small" />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'type']} style={{ flex: 1, marginBottom: 0 }}>
                      <Select size="small">
                        <Select.Option value="string">string</Select.Option>
                        <Select.Option value="integer">integer</Select.Option>
                        <Select.Option value="float">float</Select.Option>
                        <Select.Option value="boolean">boolean</Select.Option>
                        <Select.Option value="array">array</Select.Option>
                        <Select.Option value="object">object</Select.Option>
                      </Select>
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'required']} valuePropName="checked" style={{ flex: '0 0 80px', marginBottom: 0 }}>
                      <Checkbox style={{ display: 'flex', justifyContent: 'center' }} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'defaultValue']} style={{ flex: 1, marginBottom: 0 }}>
                      <Input placeholder="可选" size="small" />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'description']} style={{ flex: 2, marginBottom: 0 }}>
                      <Input placeholder="参数说明" size="small" />
                    </Form.Item>
                    <Button type="text" danger onClick={() => remove(name)} style={{ marginLeft: 4, flex: '0 0 48px' }} size="small">删除</Button>
                  </div>
                ))}
                <Button type="dashed" onClick={() => add({ name: '', type: 'string', required: false, defaultValue: '', description: '' })} block icon={<PlusOutlined />} size="small" style={{ marginTop: 12 }}>
                  添加参数
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      {/* Action 节点参数配置弹窗 */}
      <Modal title="Action 参数配置" open={actionParamModalVisible} onOk={handleSaveActionParams} onCancel={() => setActionParamModalVisible(false)} width={720} okText="确认" cancelText="取消">
        {actionParamDefs.length > 0 ? (
          <div>
            <div style={{ marginBottom: 16, padding: 12, background: '#e6f7ff', borderRadius: 4, border: '1px solid #91d5ff' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                <strong>参数值填写说明：</strong>参数值可以是固定值，也可以引用动态数据
              </Text>
              <div style={{ marginTop: 8, fontSize: 11, color: '#8c8c8c', fontFamily: 'Consolas, Monaco, monospace' }}>
                <div><span style={{ color: '#1890ff' }}>固定值：</span>直接输入，如 <span style={{ color: '#52c41a' }}>123</span> 或 <span style={{ color: '#52c41a' }}>"hello"</span></div>
                <div><span style={{ color: '#1890ff' }}>请求参数：</span>req.body.xxx、req.query.xxx、req.params.xxx，如 <span style={{ color: '#52c41a' }}>req.body.userId</span></div>
                <div><span style={{ color: '#1890ff' }}>上下文数据：</span>context.xxx，如 <span style={{ color: '#52c41a' }}>context.userData</span></div>
              </div>
            </div>
            <Form form={actionParamForm} layout="vertical">
              <div className="param-row param-header">
                <span style={{ flex: 2 }}>参数名</span>
                <span style={{ flex: 1, textAlign: 'center' }}>类型</span>
                <span style={{ flex: 1, textAlign: 'center' }}>是否必填</span>
                <span style={{ flex: 3 }}>参数值</span>
              </div>
              {actionParamDefs.map(p => (
                <div key={p.name} className="param-row" style={{ alignItems: 'center' }}>
                  <div style={{ flex: 2 }}>
                    <Text strong style={{ fontSize: 13 }}>{p.name}</Text>
                    {p.description && <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 2 }}>{p.description}</Text>}
                  </div>
                  <div style={{ flex: 1, textAlign: 'center' }}><Tag color="blue" style={{ fontSize: 10 }}>{p.type}</Tag></div>
                  <div style={{ flex: 1, textAlign: 'center' }}>{p.required ? <Tag color="red" style={{ fontSize: 10 }}>必填</Tag> : <Tag style={{ fontSize: 10 }}>可选</Tag>}</div>
                  <Form.Item name={p.name} initialValue={actionParamValues[p.name] || ''} style={{ flex: 3, marginBottom: 0 }} rules={p.required ? [{ required: true, message: '请输入参数值' }] : []}>
                    <Input placeholder={`输入值或引用 req.xxx / context.xxx`} size="small" />
                  </Form.Item>
                </div>
              ))}
            </Form>
          </div>
        ) : (
          <Text type="secondary">该 Action 无可配置参数</Text>
        )}
      </Modal>

      {/* 添加分支配置弹窗 */}
      <Modal title="添加分支" open={branchModalVisible} onOk={handleAddBranch} onCancel={() => setBranchModalVisible(false)} width={480} okText="确认添加" cancelText="取消">
        <Form form={branchForm} layout="vertical">
          <Form.Item name="branchTitle" label="分支标题" rules={[{ required: true, message: '请输入分支标题' }]}>
            <Input placeholder="如: 短缺分支、正常分支" />
          </Form.Item>
          <Form.Item name="branchCondition" label="分支条件" rules={[{ required: true, message: '请输入分支条件表达式' }]}>
            <Input placeholder='如: shortage_ratio > 0.8' />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑分支配置弹窗 */}
      <Modal 
        title={`编辑分支 (第 ${editBranchIndex !== null ? editBranchIndex + 1 : ''} 个)`} 
        open={editBranchModalVisible} 
        onOk={handleSaveEditBranch} 
        onCancel={() => setEditBranchModalVisible(false)} 
        width={480} 
        okText="确认保存" 
        cancelText="取消"
        destroyOnHidden
        afterOpenChange={handleEditBranchModalOpenChange}
      >
        <Form form={editBranchForm} layout="vertical">
          <Form.Item name="branchTitle" label="分支标题" rules={[{ required: true, message: '请输入分支标题' }]}>
            <Input placeholder="如: 短缺分支、正常分支" />
          </Form.Item>
          <Form.Item name="branchCondition" label="分支条件" rules={[{ required: true, message: '请输入分支条件表达式' }]}>
            <Input placeholder='如: shortage_ratio > 0.8' />
          </Form.Item>
        </Form>
      </Modal>

      {/* 上下文处理脚本配置弹窗 */}
      <Modal 
        title="上下文处理脚本配置" 
        open={contextHandlerModalVisible} 
        onOk={handleSaveContextHandler} 
        onCancel={() => setContextHandlerModalVisible(false)} 
        width={640} 
        okText="确认" 
        cancelText="取消"
      >
        <div style={{ marginBottom: 16, padding: 12, background: '#f6ffed', borderRadius: 4, border: '1px solid #b7eb8f' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <strong>说明：</strong>此脚本在 Action 执行完成后运行，用于将返回结果中的部分数据提取并保存到上下文 context 中，供后续节点使用。
          </Text>
        </div>
        <Form form={contextHandlerForm} layout="vertical">
          <Form.Item 
            name="contextHandler" 
            label="上下文处理脚本"
          >
            <Input.TextArea 
              rows={6} 
              value={contextHandlerValue}
              onChange={(e) => setContextHandlerValue(e.target.value)}
              placeholder="# res 为 Action 返回结果&#10;# context 为之前节点设置的上下文对象&#10;# 直接给 context 属性赋值即可保存数据&#10;context.user_data = res['data']"
              style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 12 }}
            />
            <div style={{ marginTop: 12, fontSize: 12, color: '#8c8c8c' }}>
              <div style={{ marginBottom: 8 }}><strong>使用示例：</strong></div>
              <div style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, fontFamily: 'Consolas, Monaco, monospace', marginBottom: 8 }}>
                <div style={{ color: '#52c41a' }}>context.user_data = res['data']['user']</div>
                <div>context.token = res['headers']['token']</div>
              </div>
              <div style={{ marginBottom: 8 }}><strong>示例 1 - 提取用户信息：</strong></div>
              <div style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, fontFamily: 'Consolas, Monaco, monospace', marginBottom: 8 }}>
                <div>context.user_info = res['data']</div>
              </div>
              <div style={{ marginBottom: 8 }}><strong>示例 2 - 结合上下文：</strong></div>
              <div style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, fontFamily: 'Consolas, Monaco, monospace' }}>
                <div>user_id = context.user_id</div>
                <div>context.full_data = res['data'][user_id]</div>
              </div>
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default function LogicOrchestrationCanvas() {
  const { id } = useParams();
  return (
    <ReactFlowProvider>
      <LogicOrchestrationCanvasContent orchestrationId={id} />
    </ReactFlowProvider>
  );
}
