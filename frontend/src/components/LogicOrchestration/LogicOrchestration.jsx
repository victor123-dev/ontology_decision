import ReactFlow, { 
  Background, 
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
  ConnectionLineType,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { useCallback, useState, useRef, useMemo, useEffect } from 'react';
import { Card, Typography, Space, Button, message, List, Tag, Input, Select, Modal, Form, Checkbox } from 'antd';
import { SearchOutlined, SaveOutlined, DownloadOutlined, DeleteOutlined, BranchesOutlined, LayoutOutlined, PlusOutlined, SettingOutlined, UndoOutlined } from '@ant-design/icons';
import { actionApi } from '../../services/api';
import './LogicOrchestration.css';

const { Title, Text } = Typography;
const { Search } = Input;

const ActionNode = ({ data, id }) => {
  const [showAddButton, setShowAddButton] = useState(false);

  const handleAddClick = (e) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('addEdgeFromNode', { 
      detail: { nodeId: id, nodeData: data } 
    }));
  };

  const handleConfigClick = (e) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('configActionParams', {
      detail: { nodeId: id, nodeData: data }
    }));
  };

  const paramValues = data.paramValues || {};
  const paramDefs = data.params || [];
  const hasParams = paramDefs.length > 0;
  const configuredCount = paramDefs.filter(p => paramValues[p.name] !== undefined && paramValues[p.name] !== '').length;

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
        <span className="action-node-title">{data.label}</span>
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
          {data.apiName}
        </Text>
        <Tag color="blue" style={{ fontSize: '10px', marginTop: '4px', margin: 0 }}>{data.actionType}</Tag>
      </div>
      {hasParams && (
        <div className="action-node-params" onClick={handleConfigClick}>
          <SettingOutlined style={{ fontSize: '12px', marginRight: 4 }} />
          <span>参数 {configuredCount > 0 ? `(${configuredCount}/${paramDefs.length})` : ''}</span>
        </div>
      )}
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

const StartEndNode = ({ data, id, type }) => {
  const [showAddButton, setShowAddButton] = useState(false);

  const handleAddClick = (e) => {
    e.stopPropagation();
    // 开始节点也支持添加功能
    if (type === 'start') {
      window.dispatchEvent(new CustomEvent('addEdgeFromNode', { 
        detail: { nodeId: id, nodeData: data } 
      }));
    }
  };

  return (
    <div 
      className={`start-end-node ${type}`}
      onMouseEnter={() => type === 'start' && setShowAddButton(true)}
      onMouseLeave={() => type === 'start' && setShowAddButton(false)}
    >
      {type === 'start' && (
        <Handle 
          type="source" 
          position={Position.Bottom} 
          id="start"
          style={{ background: '#52c41a', width: 14, height: 14 }}
          isConnectable={true}
        />
      )}
      {type === 'end' && (
        <Handle 
          type="target" 
          position={Position.Top} 
          id="end"
          style={{ background: '#f5222d', width: 14, height: 14 }}
          isConnectable={true}
        />
      )}
      <div className="start-end-label">{data.label}</div>
      {showAddButton && (
        <div className="node-add-button" onClick={handleAddClick}>
          <PlusOutlined />
        </div>
      )}
    </div>
  );
};

// 增强条件分支节点组件 - 支持多个分支
// 关键：直接使用 data.branches 渲染，不使用内部 state
// 预渲染足够多的 Handle 组件（未使用的隐藏），确保 ReactFlow 内部 store 中始终有注册
const MAX_BRANCHES = 8;

const ConditionNode = ({ data, id }) => {
  const branches = data.branches || [];

  const handleAddBranch = () => {
    window.dispatchEvent(new CustomEvent('requestAddBranch', { 
      detail: { nodeId: id } 
    }));
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
        <span className="condition-node-title">{data.label || '条件判断'}</span>
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
          {data.condition || '请添加分支并配置条件'}
        </Text>
      </div>
      {branches.length > 0 ? (
        <div className="condition-branches">
          {branches.map((branch, index) => (
            <div key={index} className="branch-item">
              <Handle 
                type="source" 
                position={Position.Bottom} 
                id={`branch${index}`} 
                style={{ 
                  left: `${(index + 0.5) * (100 / branches.length)}%`, 
                  background: '#faad14', 
                  width: 12, 
                  height: 12 
                }}
                isConnectable={true}
              />
              <div className="branch-label">{branch.title || branch}</div>
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
      {/* 预渲染额外的隐藏 Handle，确保 ReactFlow 在内部 store 中已注册 */}
      {Array.from({ length: MAX_BRANCHES - branches.length }, (_, i) => (
        <Handle
          key={`hidden-${i}`}
          type="source"
          position={Position.Bottom}
          id={`branch${branches.length + i}`}
          style={{ 
            background: 'transparent', 
            width: 0, 
            height: 0,
            opacity: 0,
            pointerEvents: 'none',
          }}
          isConnectable={true}
        />
      ))}
      <button className="add-branch-btn" onClick={handleAddBranch}>
        + 添加分支
      </button>
    </div>
  );
};

// 虚线框引导节点组件
const GhostNode = ({ data }) => {
  return (
    <div className="ghost-node">
      <Handle 
        type="target" 
        position={Position.Top} 
        id="input"
        style={{ background: '#1890ff', width: 12, height: 12 }}
        isConnectable={true}
      />
      <div className="ghost-node-content">
        <div className="ghost-icon">+</div>
        <div className="ghost-text">{data.label}</div>
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

// 分支合并节点组件
const MergeNode = ({ data, id }) => {
  const [showAddButton, setShowAddButton] = useState(false);

  const handleAddClick = (e) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('addEdgeFromNode', { 
      detail: { nodeId: id, nodeData: data } 
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
        <span className="merge-node-title">{data.label || '分支合并'}</span>
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



const LogicOrchestrationContent = () => {
  const reactFlowWrapper = useRef(null);
  const { screenToFlowPosition, fitView } = useReactFlow();
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [actionList, setActionList] = useState([]); // 从 API 获取的 Action 列表
  const [actionListLoading, setActionListLoading] = useState(false);
  const [pendingEdgeSource, setPendingEdgeSource] = useState(null);
  const [ghostNode, setGhostNode] = useState(null); // 虚线框节点
  const [ghostEdge, setGhostEdge] = useState(null); // 虚线框的连线
  const [isDragging, setIsDragging] = useState(false); // 是否正在拖拽
  const [workflowParams, setWorkflowParams] = useState([]); // 工作流入参配置
  const [paramModalVisible, setParamModalVisible] = useState(false); // 入参配置弹窗
  const [paramForm] = Form.useForm();
  // Action 节点参数配置
  const [actionParamModalVisible, setActionParamModalVisible] = useState(false);
  const [actionParamNodeId, setActionParamNodeId] = useState(null);
  const [actionParamDefs, setActionParamDefs] = useState([]);
  const [actionParamValues, setActionParamValues] = useState({});
  const [actionParamForm] = Form.useForm();
  // 分支配置弹窗
  const [branchModalVisible, setBranchModalVisible] = useState(false);
  const [branchModalNodeId, setBranchModalNodeId] = useState(null);
  const [branchForm] = Form.useForm();
  // 撤回/重做历史
  const historyRef = useRef([]);     // { nodes, edges } 快照栈
  const historyIndexRef = useRef(-1); // 当前指向的快照索引
  const isUndoRedoRef = useRef(false); // 标记是否正在执行 undo/redo，避免重复记录

  // 使用 ref 保存 getLayoutedElements，避免 useEffect 循环依赖
  const getLayoutedElementsRef = useRef(null);
  // 使用 ref 保存最新的 edges，供事件回调使用
  const edgesRef = useRef(edges);
  edgesRef.current = edges;
  const nodesRef = useRef(nodes);

  // 计算条件分支节点的动态高度
  const getConditionNodeHeight = (node) => {
    const branchCount = node.data?.branches?.length || 0;
    const baseHeight = 80;
    const branchRowHeight = 56;
    const addButtonHeight = 40;
    return baseHeight + branchCount * branchRowHeight + addButtonHeight;
  };
  nodesRef.current = nodes;

  // 辅助函数：沿边向下级联收集所有下游节点 ID
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

  // 辅助函数：重新映射条件分支的 ghost 节点（branchIndex 前移）
  const remapGhostNodes = useCallback((nodes, parentId, deletedBranchIndex) => {
    return nodes.map(n => {
      if (n.type === 'ghost' && n.data?.parentId === parentId) {
        const oldIndex = n.data.branchIndex;
        if (oldIndex > deletedBranchIndex) {
          const newIndex = oldIndex - 1;
          const newId = `ghost-${parentId}-${newIndex}`;
          return { ...n, id: newId, data: { ...n.data, branchIndex: newIndex } };
        }
      }
      return n;
    });
  }, []);

  // 辅助函数：重新映射条件分支边的 sourceHandle
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

  // 监听删除节点事件
  useEffect(() => {
    const handleDeleteNode = (event) => {
      const { nodeId } = event.detail;
      const currentEdges = edgesRef.current;

      setNodes((nds) => {
        const deletedNode = nds.find(n => n.id === nodeId);
        if (!deletedNode) return nds;

        // 级联收集所有下游节点 ID
        const downstreamIds = collectDownstreamIds(nodeId, currentEdges);

        // 判断删除的节点是否在某个条件分支下方（通过边找到上游条件分支节点）
        let parentId = null;
        let branchIndex = null;
        if (deletedNode.type === 'ghost' && deletedNode.data?.parentId) {
          parentId = deletedNode.data.parentId;
          branchIndex = deletedNode.data.branchIndex;
        } else {
          // 非 ghost 节点：通过边回溯找到来源条件分支
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
          // 联动删除分支：从条件分支的 branches 中移除
          updatedNodes = updatedNodes.map(n => {
            if (n.id === parentId && n.type === 'condition') {
              const newBranches = (n.data.branches || []).filter((_, idx) => idx !== branchIndex);
              return { ...n, data: { ...n.data, branches: newBranches } };
            }
            return n;
          });
          // 删除所有下游节点
          updatedNodes = updatedNodes.filter(n => !downstreamIds.has(n.id));
          // 重新映射 ghost 节点
          updatedNodes = remapGhostNodes(updatedNodes, parentId, branchIndex);
        } else if (deletedNode.type === 'condition') {
          // 删除条件分支节点：级联删除所有 ghost 和下游
          updatedNodes = updatedNodes.filter(n => !downstreamIds.has(n.id));
        } else {
          // 普通 Action/Merge 节点：级联删除下游
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

        // 删除所有下游相关的边
        let updatedEdges = eds.filter(e => !downstreamIds.has(e.source) && !downstreamIds.has(e.target));

        // 如果联动删除了分支，重新映射剩余边的 sourceHandle
        if (parentId !== null && branchIndex !== null) {
          updatedEdges = remapBranchEdges(updatedEdges, parentId, branchIndex);
        }

        return updatedEdges;
      });

      message.success('节点已删除');
    };

    window.addEventListener('deleteNode', handleDeleteNode);
    return () => {
      window.removeEventListener('deleteNode', handleDeleteNode);
    };
  }, [collectDownstreamIds, remapGhostNodes, remapBranchEdges]);

  // 监听删除分支事件
  useEffect(() => {
    const handleDeleteBranch = (event) => {
      const { nodeId, branchIndex } = event.detail;
      const currentEdges = edgesRef.current;

      setNodes((nds) => {
        // 找到该分支直连的下游节点（ghost 或 action）
        const branchEdge = currentEdges.find(e => e.source === nodeId && e.sourceHandle === `branch${branchIndex}`);
        // 级联收集所有下游节点
        let downstreamIds = new Set();
        if (branchEdge) {
          downstreamIds = collectDownstreamIds(branchEdge.target, currentEdges);
        }

        // 更新条件分支节点的 branches
        let updatedNodes = nds.map(n => {
          if (n.id === nodeId && n.type === 'condition') {
            const newBranches = (n.data.branches || []).filter((_, idx) => idx !== branchIndex);
            return { ...n, data: { ...n.data, branches: newBranches } };
          }
          return n;
        });

        // 删除所有下游节点
        updatedNodes = updatedNodes.filter(n => !downstreamIds.has(n.id));

        // 重新映射 ghost 节点
        updatedNodes = remapGhostNodes(updatedNodes, nodeId, branchIndex);

        return updatedNodes;
      });

      setEdges((eds) => {
        // 找到该分支直连的下游节点
        const branchEdge = currentEdges.find(e => e.source === nodeId && e.sourceHandle === `branch${branchIndex}`);
        let downstreamIds = new Set();
        if (branchEdge) {
          downstreamIds = collectDownstreamIds(branchEdge.target, currentEdges);
        }

        // 删除所有下游相关的边
        let updatedEdges = eds.filter(e => !downstreamIds.has(e.source) && !downstreamIds.has(e.target));

        // 重新映射剩余边的 sourceHandle
        updatedEdges = remapBranchEdges(updatedEdges, nodeId, branchIndex);

        return updatedEdges;
      });

      message.success('分支已删除');
    };

    window.addEventListener('deleteBranch', handleDeleteBranch);
    return () => {
      window.removeEventListener('deleteBranch', handleDeleteBranch);
    };
  }, [collectDownstreamIds, remapGhostNodes, remapBranchEdges]);

  // 监听 Action 节点参数配置事件
  useEffect(() => {
    const handleConfigActionParams = (event) => {
      const { nodeId, nodeData } = event.detail;
      setActionParamNodeId(nodeId);
      setActionParamDefs(nodeData.params || []);
      setActionParamValues(nodeData.paramValues || {});
      setActionParamModalVisible(true);
    };

    window.addEventListener('configActionParams', handleConfigActionParams);
    return () => {
      window.removeEventListener('configActionParams', handleConfigActionParams);
    };
  }, []);

  // 监听请求添加分支事件（打开配置弹窗）
  useEffect(() => {
    const handleRequestAddBranch = (event) => {
      const { nodeId } = event.detail;
      setBranchModalNodeId(nodeId);
      branchForm.resetFields();
      setBranchModalVisible(true);
    };

    window.addEventListener('requestAddBranch', handleRequestAddBranch);
    return () => {
      window.removeEventListener('requestAddBranch', handleRequestAddBranch);
    };
  }, [branchForm]);

  // 确认添加分支
  const handleAddBranch = useCallback(async () => {
    try {
      const values = await branchForm.validateFields();
      const { branchTitle, branchCondition } = values;
      const nodeId = branchModalNodeId;
      
      setNodes((currentNodes) => {
        const sourceNode = currentNodes.find(n => n.id === nodeId);
        if (!sourceNode) return currentNodes;
        
        const currentBranches = sourceNode.data.branches || [];
        const newBranchIndex = currentBranches.length;
        const newBranch = { title: branchTitle, condition: branchCondition };
        const newBranches = [...currentBranches, newBranch];
        
        const ghostId = `ghost-${nodeId}-${newBranchIndex}`;
        const branchColor = newBranchIndex === 0 ? '#52c41a' : newBranchIndex === 1 ? '#f5222d' : '#faad14';
        
        const newEdge = {
          id: `edge-${nodeId}-${ghostId}-${Date.now()}`,
          source: nodeId,
          target: ghostId,
          sourceHandle: `branch${newBranchIndex}`,
          targetHandle: 'input',
          type: 'smoothstep',
          animated: true,
          style: { 
            stroke: branchColor, 
            strokeWidth: 2,
            strokeDasharray: '5,5',
          },
          markerEnd: {
            type: 'arrowclosed',
            color: branchColor,
          },
          label: branchTitle,
          labelStyle: { fill: branchColor, fontWeight: 'bold', fontSize: '12px' },
          labelBgStyle: { fill: '#fff', fillOpacity: 0.8 },
        };
        
        const nodeWidth = 220;
        const verticalGap = 120;
        const horizontalGap = 80;
        const conditionHeight = getConditionNodeHeight(sourceNode);
        // 与 adjustConditionBranchLayout 保持一致的布局
        const ghostX = sourceNode.position.x + nodeWidth + newBranchIndex * (nodeWidth + horizontalGap);
        const ghostY = sourceNode.position.y + conditionHeight + verticalGap;
        
        const newGhostNode = {
          id: ghostId,
          type: 'ghost',
          position: { x: ghostX, y: ghostY },
          data: { 
            label: `${branchTitle} 分支`,
            parentId: nodeId,
            branchIndex: newBranchIndex,
          },
        };
        
        const updatedNodes = currentNodes.map(n => {
          if (n.id === nodeId) {
            return { ...n, data: { ...n.data, branches: newBranches } };
          }
          return n;
        });
        
        const finalNodes = [...updatedNodes, newGhostNode];
        // 将新创建的 edge 也包含在布局计算中
        const { nodes: layoutedNodes } = getLayoutedElementsRef.current(finalNodes, [...edgesRef.current, newEdge], 'TB');
        
        // 延迟添加边
        setTimeout(() => {
          setEdges((currentEdges) => {
            const exists = currentEdges.some(e => e.source === newEdge.source && e.target === newEdge.target && e.sourceHandle === newEdge.sourceHandle);
            if (exists) return currentEdges;
            return [...currentEdges, newEdge];
          });
        }, 50);
        
        return layoutedNodes;
      });
      
      setBranchModalVisible(false);
      message.success(`已添加分支: ${branchTitle}`);
    } catch {
      // 表单校验失败
    }
  }, [branchForm, branchModalNodeId, setNodes, setEdges]);

  // 监听添加连线事件
  useEffect(() => {
    const handleAddEdgeEvent = (event) => {
      const { nodeId, nodeData, branchIndex } = event.detail;
      setPendingEdgeSource({ nodeId, nodeData, branchIndex });
      
      // 在源节点下方创建虚线框
      const sourceNode = nodes.find(n => n.id === nodeId);
      if (sourceNode) {
        const nodeWidth = 220;
        const verticalGap = 120;
        const horizontalGap = 80;
        let ghostX = sourceNode.position.x;
        let ghostY = sourceNode.position.y + 150;
        
        // 与 adjustConditionBranchLayout 保持一致的布局
        if (nodeData.actionType === '条件分支' && branchIndex !== undefined) {
          const conditionHeight = getConditionNodeHeight(sourceNode);
          ghostX = sourceNode.position.x + nodeWidth + branchIndex * (nodeWidth + horizontalGap);
          ghostY = sourceNode.position.y + conditionHeight + verticalGap;
        }
        
        const ghostPosition = {
          x: ghostX,
          y: ghostY,
        };
        setGhostNode({
          id: 'ghost-node',
          type: 'ghost',
          position: ghostPosition,
          data: { label: '拖拽 Action 到这里' },
        });
        
        // 创建源节点到虚线框的虚线连线
        // 条件分支节点使用分支端口，其他节点使用output端口
        const sourceHandle = nodeData.actionType === '条件分支' && branchIndex !== undefined ? 
          `branch${branchIndex}` : 'output';
        
        setGhostEdge({
          id: 'ghost-edge',
          source: nodeId,
          target: 'ghost-node',
          sourceHandle: sourceHandle,
          targetHandle: 'input',
          type: 'smoothstep',
          animated: true,
          style: { 
            stroke: '#1890ff', 
            strokeWidth: 2,
            strokeDasharray: '5,5',
          },
          markerEnd: {
            type: 'arrowclosed',
            color: '#1890ff',
          },
        });
      }
      
      message.info(`请拖拽 Action 到画布中的虚线框`);
    };

    window.addEventListener('addEdgeFromNode', handleAddEdgeEvent);
    return () => {
      window.removeEventListener('addEdgeFromNode', handleAddEdgeEvent);
    };
  }, [nodes]);

  // 从 API 获取 Action 列表
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
      description: '根据条件进行分支判断（True/False）',
      action_type: 'condition',
    };
    event.dataTransfer.setData('application/reactflow', JSON.stringify(conditionAction));
    event.dataTransfer.effectAllowed = 'move';
    setIsDragging(true);
  };

  const onDragEnd = useCallback(() => {
    setIsDragging(false);
    // 拖拽结束后清除虚线框和虚线
    setGhostNode(null);
    setGhostEdge(null);
  }, []);

  // 将虚线框节点添加到节点列表
  const displayNodes = useMemo(() => {
    if (ghostNode) {
      return [...nodes, ghostNode];
    }
    return nodes;
  }, [nodes, ghostNode]);

  // 将虚线连线添加到连线列表
  const displayEdges = useMemo(() => {
    if (ghostEdge) {
      return [...edges, ghostEdge];
    }
    return edges;
  }, [edges, ghostEdge]);

  // 使用 dagre 进行自动布局 - 严格树形结构，节点中心对齐
  const getLayoutedElements = useCallback((nodes, edges, direction = 'TB') => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const nodeWidth = 220;
    const nodeHeight = 110;

    dagreGraph.setGraph({ 
      rankdir: direction,
      nodesep: 60,      // 节点水平间距（同层级）
      ranksep: 120,     // 层级垂直间距
      marginx: 80,
      marginy: 80,
      align: 'DL',      // 中心对齐（Down-Left），确保节点中心在垂直中轴线上
      ranker: 'network-simplex', // 网络单纯形算法，最适合树形布局
      edgesep: 40,      // 边之间的间距
    });

    // 所有节点都参与布局计算（包括虚拟节点）
    // 过滤掉临时 ghost-node（点击+按钮生成的），只保留条件分支关联的 ghost 节点
    const layoutNodes = nodes.filter(n => n.id === 'ghost-node' ? false : true);
    const layoutEdges = edges.filter(e => e.target === 'ghost-node' ? false : true);

    // 所有节点使用统一宽度，确保中心对齐
    layoutNodes.forEach((node) => {
      dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    layoutEdges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    // 对所有节点应用布局
    const layoutedNodes = nodes.map((node) => {
      // 临时 ghost-node（点击+按钮）保持原位置
      if (node.id === 'ghost-node') {
        return node;
      }
      const nodeWithPosition = dagreGraph.node(node.id);
      if (!nodeWithPosition) {
        return node;
      }
      return {
        ...node,
        position: {
          x: nodeWithPosition.x - nodeWidth / 2,
          y: nodeWithPosition.y - nodeHeight / 2,
        },
        style: {
          width: nodeWidth,
          height: nodeHeight,
        },
      };
    });

    return { nodes: layoutedNodes, edges };
  }, []);

  // 保持 ref 始终指向最新的 getLayoutedElements
  getLayoutedElementsRef.current = getLayoutedElements;

  // 快照管理：保存当前 nodes/edges 到历史栈
  const pushHistory = useCallback((currentNodes, currentEdges) => {
    if (isUndoRedoRef.current) return;
    const snapshot = {
      nodes: JSON.parse(JSON.stringify(currentNodes)),
      edges: JSON.parse(JSON.stringify(currentEdges)),
    };
    const newHistory = [...historyRef.current, snapshot];
    // 限制历史栈最大长度
    if (newHistory.length > 50) newHistory.shift();
    historyRef.current = newHistory;
    historyIndexRef.current = newHistory.length - 1;
  }, []);

  // 撤回
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

  // 键盘快捷键 Ctrl+Z
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

  // 自动记录快照：nodes/edges 变更时推入历史栈
  const prevNodesLengthRef = useRef(0);
  const prevEdgesLengthRef = useRef(0);
  useEffect(() => {
    // 跳过初始化和 undo/redo 时的记录
    if (isUndoRedoRef.current) return;
    // 只在有实质性变化时记录（避免空数据初始化时记录）
    if (nodes.length === 0 && edges.length === 0 && historyRef.current.length === 0) return;
    // 使用防抖，避免短时间内多次变更产生过多快照
    const timer = setTimeout(() => {
      pushHistory(nodes, edges);
      prevNodesLengthRef.current = nodes.length;
      prevEdgesLengthRef.current = edges.length;
    }, 300);
    return () => clearTimeout(timer);
  }, [nodes, edges, pushHistory]);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const actionData = event.dataTransfer.getData('application/reactflow');
      if (!actionData) return;

      const action = JSON.parse(actionData);
      
      // 获取拖拽位置（flow坐标系）
      const dropPosition = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      
      // 检测是否拖拽到了某个虚线框节点上（条件分支生成的虚线框）
      let targetGhostNode = null;
      const ghostNodeWidth = 220;
      const ghostNodeHeight = 110;
      
      // 遍历所有节点，查找虚线框节点
      nodes.forEach(node => {
        if (node.type === 'ghost' && node.id.startsWith('ghost-')) {
          // node.position 是节点左上角坐标，计算节点中心点
          const nodeCenterX = node.position.x + ghostNodeWidth / 2;
          const nodeCenterY = node.position.y + ghostNodeHeight / 2;
          const dx = dropPosition.x - nodeCenterX;
          const dy = dropPosition.y - nodeCenterY;
          // 检查是否在虚线框范围内
          if (Math.abs(dx) < ghostNodeWidth / 2 && Math.abs(dy) < ghostNodeHeight / 2) {
            targetGhostNode = node;
          }
        }
      });
      
      // 确定新节点的放置位置
      let position;
      if (targetGhostNode) {
        // 拖拽到条件分支虚线框，使用虚线框的位置
        position = { ...targetGhostNode.position };
      } else if (ghostNode) {
        // 点击"+"按钮生成的临时虚线框
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
      } else if (action.action_type === 'parallel') {
        newNode = {
          id: `${action.id}-${Date.now()}`,
          type: 'parallel',
          position,
          data: {
            label: action.name,
            actionId: action.id,
            apiName: action.api_name,
            actionType: '并行处理',
            category: action.category,
            description: action.description,
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

      // 添加节点：只删除被命中的虚线框（保留其他虚线框）
      setNodes((nds) => {
        let nodesWithoutGhost = nds.filter(n => n.id !== 'ghost-node');
        if (targetGhostNode) {
          // 只删除被拖拽命中的虚线框
          nodesWithoutGhost = nodesWithoutGhost.filter(n => n.id !== targetGhostNode.id);
        }
        const updatedNodes = [...nodesWithoutGhost, newNode];
        const { nodes: layoutedNodes } = getLayoutedElements(updatedNodes, edges, 'TB');
        return layoutedNodes;
      });
      
      // 清除临时虚线框状态
      if (ghostNode) {
        setGhostNode(null);
        setGhostEdge(null);
      }

      // 判断连接来源：优先使用 targetGhostNode（拖拽到条件分支的虚线框），其次使用 ghostNode，最后使用 pendingEdgeSource
      let sourceNodeId = null;
      let sourceNodeData = null;
      let sourceBranchIndex = null;
      let sourceHandle = 'output';
      let branchColor = '#1890ff';
      
      if (targetGhostNode && targetGhostNode.data.parentId) {
        // 来自条件分支节点自动生成的虚线框（用户拖拽action到虚线框）
        sourceNodeId = targetGhostNode.data.parentId;
        sourceBranchIndex = targetGhostNode.data.branchIndex;
        // 找到源节点数据
        const sourceNode = nodes.find(n => n.id === sourceNodeId);
        if (sourceNode) {
          sourceNodeData = sourceNode.data;
          sourceHandle = `branch${sourceBranchIndex !== undefined ? sourceBranchIndex : 0}`;
        }
        // 根据分支索引确定颜色
        branchColor = sourceBranchIndex === 0 ? '#52c41a' : sourceBranchIndex === 1 ? '#f5222d' : '#faad14';
      } else if (ghostNode && ghostNode.data.parentId) {
        // 来自点击"+"按钮生成的临时虚线框
        sourceNodeId = ghostNode.data.parentId;
        sourceBranchIndex = ghostNode.data.branchIndex;
        const sourceNode = nodes.find(n => n.id === sourceNodeId);
        if (sourceNode) {
          sourceNodeData = sourceNode.data;
          sourceHandle = `branch${sourceBranchIndex || 0}`;
        }
        branchColor = sourceBranchIndex === 0 ? '#52c41a' : sourceBranchIndex === 1 ? '#f5222d' : '#faad14';
      } else if (pendingEdgeSource) {
        // 来自点击"+"按钮的主动连接
        sourceNodeId = pendingEdgeSource.nodeId;
        sourceNodeData = pendingEdgeSource.nodeData;
        sourceBranchIndex = pendingEdgeSource.branchIndex;
        sourceHandle = sourceNodeData.actionType === '条件分支' ? 
          `branch${sourceBranchIndex || 0}` : 'output';
        branchColor = sourceBranchIndex === 0 ? '#52c41a' : sourceBranchIndex === 1 ? '#f5222d' : '#faad14';
      }
      
      // 如果有连接来源，创建连线
      if (sourceNodeId) {
        // 如果拖拽到了条件分支的虚线框，需要删除该虚线框对应的旧连线
        if (targetGhostNode) {
          setEdges((eds) => {
            // 删除指向该虚线框的连线
            const filteredEdges = eds.filter(e => e.target !== targetGhostNode.id);
            // 添加新的连线（从条件分支到新节点，使用分支颜色）
            const newEdge = {
              id: `edge-${sourceNodeId}-${newNode.id}-${Date.now()}`,
              source: sourceNodeId,
              target: newNode.id,
              sourceHandle: sourceHandle,
              targetHandle: 'input',
              type: 'smoothstep',
              animated: true,
              style: { stroke: branchColor, strokeWidth: 2 },
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
      
      // 清除pendingEdgeSource
      setPendingEdgeSource(null);
    },
    [screenToFlowPosition, setNodes, setEdges, pendingEdgeSource, ghostNode, ghostEdge, edges, getLayoutedElements, nodes]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onConnect = useCallback(
    (params) => {
      const edge = {
        ...params,
        animated: true,
        style: { stroke: '#1890ff', strokeWidth: 2 },
      };
      
      // 根据源端口添加标签
      if (params.sourceHandle === 'true') {
        edge.label = 'True';
        edge.style = { stroke: '#52c41a', strokeWidth: 2 };
      } else if (params.sourceHandle === 'false') {
        edge.label = 'False';
        edge.style = { stroke: '#f5222d', strokeWidth: 2 };
      } else if (params.sourceHandle?.startsWith('branch')) {
        edge.label = params.sourceHandle.replace('branch', '分支 ');
      }
      
      setEdges((eds) => {
        const updatedEdges = addEdge(edge, eds);
        // 自动排版
        setTimeout(() => {
          setNodes((nds) => {
            const { nodes: layoutedNodes } = getLayoutedElements(nds, updatedEdges, 'TB');
            return layoutedNodes;
          });
        }, 100);
        return updatedEdges;
      });
    },
    [setEdges, getLayoutedElements]
  );

  // 将画布节点/边转换为标准 DAG 格式
  // 格式说明：
  //   - nodes 保留完整信息（id, label, type 等）
  //   - condition 放到 edges 上，值为条件表达式
  // 示例：
  //   nodes: [
  //     { "id": "data_quality_check", "label": "数据质量检查" },
  //     { "id": "data_analysis", "label": "数据分析" },
  //     { "id": "data_cleaning", "label": "数据清洗" }
  //   ]
  //   edges: [
  //     { "source": "data_quality_check", "target": "data_analysis", "condition": "data_quality_check.score >= 90" },
  //     { "source": "data_quality_check", "target": "data_cleaning", "condition": "data_quality_check.score < 90" }
  //   ]
  const toDAGData = useCallback(() => {
    // 过滤掉虚拟节点（ghost类型），只保留真实节点
    const realNodes = nodes.filter(n => n.type !== 'ghost');
    // 过滤掉指向虚拟节点的边
    const realEdges = edges.filter(e => {
      const targetNode = nodes.find(n => n.id === e.target);
      return targetNode && targetNode.type !== 'ghost';
    });

    // 找出所有条件分支节点的分支映射
    const conditionBranchMap = {};
    realNodes.forEach(n => {
      if (n.type === 'condition') {
        conditionBranchMap[n.id] = {
          branches: n.data.branches || [],
          condition: n.data.condition || '',
        };
      }
    });

    return {
      nodes: realNodes.map(n => {
        const dagNode = { id: n.id, label: n.data.label || n.id };
        if (n.type === 'action') {
          dagNode.type = 'action';
          dagNode.actionId = n.data.actionId;
          dagNode.category = n.data.category;
          const paramValues = n.data.paramValues || {};
          if (Object.keys(paramValues).length > 0) {
            dagNode.params = paramValues;
          }
        } else if (n.type === 'condition') {
          dagNode.type = 'condition';
        } else if (n.type === 'merge') {
          dagNode.type = 'merge';
        }
        return dagNode;
      }),
      edges: realEdges.map(e => {
        const dagEdge = { source: e.source, target: e.target };
        // 如果边来自条件分支节点，将 condition 表达式放到边上
        if (e.sourceHandle && conditionBranchMap[e.source]) {
          const condInfo = conditionBranchMap[e.source];
          const branchIdx = parseInt(e.sourceHandle.replace('branch', ''), 10);
          const branchInfo = condInfo.branches[branchIdx];
          if (branchInfo) {
            const branchTitle = typeof branchInfo === 'object' ? branchInfo.title : branchInfo;
            const branchCondition = typeof branchInfo === 'object' ? branchInfo.condition : '';
            // 生成表达式：源节点ID.条件 => 分支标题
            dagEdge.condition = branchCondition
              ? `${e.source}.${branchCondition} => ${branchTitle}`
              : branchTitle;
          }
        }
        return dagEdge;
      }),
    };
  }, [nodes, edges]);

  // 工作流入参配置相关
  const handleOpenParamModal = useCallback(() => {
    paramForm.setFieldsValue({
      params: workflowParams.length > 0
        ? workflowParams.map(p => ({ ...p }))
        : [{ name: '', type: 'string', required: false, defaultValue: '', description: '' }],
    });
    setParamModalVisible(true);
  }, [workflowParams, paramForm]);

  const handleSaveParams = useCallback(async () => {
    try {
      const values = await paramForm.validateFields();
      const params = (values.params || []).filter(p => p.name);
      setWorkflowParams(params);
      setParamModalVisible(false);
      message.success(`已配置 ${params.length} 个入参`);
    } catch {
      // 表单校验失败
    }
  }, [paramForm]);

  // 保存 Action 节点参数值
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
      // 更新节点的 paramValues
      setNodes((nds) => nds.map(n => {
        if (n.id === actionParamNodeId) {
          return { ...n, data: { ...n.data, paramValues } };
        }
        return n;
      }));
      setActionParamModalVisible(false);
      const configured = Object.keys(paramValues).length;
      message.success(configured > 0 ? `已配置 ${configured} 个参数` : '已清除参数配置');
    } catch {
      // 表单校验失败
    }
  }, [actionParamForm, actionParamNodeId, actionParamDefs, setNodes]);

  const handleSave = useCallback(() => {
    const flowData = toDAGData();
    // 附加工作流入参
    flowData.inputs = workflowParams;
    console.log('保存的流程数据 (DAG):', flowData);
    message.success('流程已保存');
  }, [toDAGData, workflowParams]);

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

  const addConditionNode = useCallback(() => {
    const newNode = {
      id: `condition-${Date.now()}`,
      type: 'condition',
      position: { x: 250, y: 300 },
      data: {
        label: '条件分支',
        actionType: '条件分支',
        category: '流程控制',
        condition: '',
        branches: [],
      },
    };
    
    setNodes((nds) => {
      const nodesWithoutGhost = nds.filter(n => n.id !== 'ghost-node');
      const updatedNodes = [...nodesWithoutGhost, newNode];
      const { nodes: layoutedNodes } = getLayoutedElements(updatedNodes, edges, 'TB');
      return layoutedNodes;
    });
    
    message.success('已添加条件分支节点，请点击节点上的"添加分支"按钮配置分支');
  }, [setNodes, edges, getLayoutedElements]);

  // 自动排版
  const handleAutoLayout = useCallback(() => {
    const layouted = getLayoutedElements(nodes, edges, 'TB');
    setNodes(layouted.nodes);
    message.success('已自动排版');
  }, [nodes, edges, getLayoutedElements]);

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
                  <Title level={4} style={{ margin: 0 }}>DAG 流程编排画布</Title>
                </Space>
              }
              extra={
                <Space>
                  <Button 
                    icon={<UndoOutlined />} 
                    onClick={handleUndo}
                    size="small"
                    title="撤回 (Ctrl+Z)"
                  >
                    撤回
                  </Button>
                  <Button 
                    icon={<BranchesOutlined />} 
                    draggable
                    onDragStart={onDragStartCondition}
                    size="small"
                    style={{ cursor: 'grab' }}
                  >
                    条件分支
                  </Button>
                  <Button 
                    icon={<SettingOutlined />} 
                    onClick={handleOpenParamModal}
                    size="small"
                  >
                    入参配置
                  </Button>
                  <Button 
                    type="primary" 
                    icon={<SaveOutlined />} 
                    onClick={handleSave}
                    size="small"
                  >
                    保存
                  </Button>
                  <Button 
                    icon={<DownloadOutlined />} 
                    onClick={handleExport}
                    size="small"
                  >
                    导出
                  </Button>
                  <Button 
                    danger 
                    icon={<DeleteOutlined />} 
                    onClick={handleClear}
                    size="small"
                  >
                    清空
                  </Button>
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
                  connectionLineType={ConnectionLineType.SmoothStep}
                  defaultEdgeOptions={{
                    type: 'smoothstep',
                    animated: true,
                    style: { stroke: '#1890ff', strokeWidth: 2 },
                  }}
                  nodesDraggable={false}
                  nodesConnectable={true}
                  elementsSelectable={true}
                  zoomOnScroll={true}
                  panOnScroll={true}
                  panOnDrag={false}
                  defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
                >
                  <Background color="#aaa" gap={16} />
                </ReactFlow>
              </div>
            </Card>
          </div>
        </div>
        {/* 工作流入参配置弹窗 */}
        <Modal
          title="工作流入参配置"
          open={paramModalVisible}
          onOk={handleSaveParams}
          onCancel={() => setParamModalVisible(false)}
          width={720}
          okText="确认"
          cancelText="取消"
        >
          <Form form={paramForm} layout="vertical">
            {/* 表头 */}
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
                      <Form.Item
                        {...restField}
                        name={[name, 'name']}
                        rules={[{ required: true, message: '请输入参数名' }]}
                        style={{ flex: 2, marginBottom: 0 }}
                      >
                        <Input placeholder="如: score" size="small" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'type']}
                        style={{ flex: 1, marginBottom: 0 }}
                      >
                        <Select size="small">
                          <Select.Option value="string">string</Select.Option>
                          <Select.Option value="integer">integer</Select.Option>
                          <Select.Option value="float">float</Select.Option>
                          <Select.Option value="boolean">boolean</Select.Option>
                          <Select.Option value="array">array</Select.Option>
                          <Select.Option value="object">object</Select.Option>
                        </Select>
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'required']}
                        valuePropName="checked"
                        style={{ flex: '0 0 80px', marginBottom: 0 }}
                      >
                        <Checkbox style={{ display: 'flex', justifyContent: 'center' }} />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'defaultValue']}
                        style={{ flex: 1, marginBottom: 0 }}
                      >
                        <Input placeholder="可选" size="small" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'description']}
                        style={{ flex: 2, marginBottom: 0 }}
                      >
                        <Input placeholder="参数说明" size="small" />
                      </Form.Item>
                      <Button
                        type="text"
                        danger
                        onClick={() => remove(name)}
                        style={{ marginLeft: 4, flex: '0 0 48px' }}
                        size="small"
                      >
                        删除
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="dashed"
                    onClick={() => add({ name: '', type: 'string', required: false, defaultValue: '', description: '' })}
                    block
                    icon={<PlusOutlined />}
                    size="small"
                    style={{ marginTop: 12 }}
                  >
                    添加参数
                  </Button>
                </>
              )}
            </Form.List>
          </Form>
        </Modal>
        {/* Action 节点参数配置弹窗 */}
        <Modal
          title="Action 参数配置"
          open={actionParamModalVisible}
          onOk={handleSaveActionParams}
          onCancel={() => setActionParamModalVisible(false)}
          width={600}
          okText="确认"
          cancelText="取消"
          destroyOnClose
        >
          {actionParamDefs.length > 0 ? (
            <Form form={actionParamForm} layout="vertical">
              {/* 表头 */}
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
                    {p.description && (
                      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 2 }}>{p.description}</Text>
                    )}
                  </div>
                  <div style={{ flex: 1, textAlign: 'center' }}>
                    <Tag color="blue" style={{ fontSize: 10 }}>{p.type}</Tag>
                  </div>
                  <div style={{ flex: 1, textAlign: 'center' }}>
                    {p.required ? <Tag color="red" style={{ fontSize: 10 }}>必填</Tag> : <Tag style={{ fontSize: 10 }}>可选</Tag>}
                  </div>
                  <Form.Item
                    name={p.name}
                    initialValue={actionParamValues[p.name] || ''}
                    style={{ flex: 3, marginBottom: 0 }}
                    rules={p.required ? [{ required: true, message: '请输入参数值' }] : []}
                  >
                    <Input placeholder={`输入 ${p.type} 类型的值`} size="small" />
                  </Form.Item>
                </div>
              ))}
            </Form>
          ) : (
            <Text type="secondary">该 Action 无可配置参数</Text>
          )}
        </Modal>
        {/* 添加分支配置弹窗 */}
        <Modal
          title="添加分支"
          open={branchModalVisible}
          onOk={handleAddBranch}
          onCancel={() => setBranchModalVisible(false)}
          width={480}
          okText="确认添加"
          cancelText="取消"
          destroyOnClose
        >
          <Form form={branchForm} layout="vertical">
            <Form.Item
              name="branchTitle"
              label="分支标题"
              rules={[{ required: true, message: '请输入分支标题' }]}
            >
              <Input placeholder="如: 短缺分支、正常分支" />
            </Form.Item>
            <Form.Item
              name="branchCondition"
              label="分支条件"
              rules={[{ required: true, message: '请输入分支条件表达式' }]}
            >
              <Input placeholder='如: shortage_ratio > 0.8' />
            </Form.Item>
          </Form>
        </Modal>
      </div>
  );
};

export default function LogicOrchestration() {
  return (
    <ReactFlowProvider>
      <LogicOrchestrationContent />
    </ReactFlowProvider>
  );
}
