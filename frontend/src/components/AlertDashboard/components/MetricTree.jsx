const CARD_WIDTH = 168;
const CARD_HEIGHT = 58;
const COLUMN_GAP = 50;
const ROW_GAP = 8;
const PADDING_X = 18;
const PADDING_Y = 12;

const STATUS_THEME = {
  normal: {
    label: '正常',
    color: '#16a34a',
    background: 'linear-gradient(135deg, rgba(22,163,74,0.12) 0%, rgba(240,253,244,0.98) 100%)',
    border: 'rgba(22,163,74,0.38)',
    shadow: '0 8px 18px rgba(22,163,74,0.12)',
  },
  abnormal: {
    label: '异常',
    color: '#dc2626',
    background: 'linear-gradient(135deg, rgba(220,38,38,0.12) 0%, rgba(254,242,242,0.98) 100%)',
    border: 'rgba(220,38,38,0.42)',
    shadow: '0 8px 18px rgba(220,38,38,0.13)',
  },
  unknown: {
    label: '无数据',
    color: '#64748b',
    background: 'linear-gradient(135deg, rgba(100,116,139,0.10) 0%, rgba(248,250,252,0.98) 100%)',
    border: 'rgba(100,116,139,0.26)',
    shadow: '0 8px 18px rgba(100,116,139,0.08)',
  },
};

const METRIC_TREE_DATA = {
  id: 'root',
  label: '订单准时交付率',
  icon: '🎯',
  dataKey: 'orderOnTimeDeliveryRate',
  target: 0.95,
  children: [
    {
      id: 'supply-chain',
      label: '供应链保障率',
      icon: '🎯',
      dataKey: 'supplyChain.supplyChainRate',
      target: 0.95,
      children: [
        {
          id: 'po-on-time',
          label: '采购准时到货率',
          dataKey: 'supplyChain.poOnTimeRate',
          target: 0.96,
          children: [
            {
              id: 'supplier-delivery',
              label: '供应商交期达成率',
              dataKey: 'supplyChain.supplierDeliveryRate',
              target: 0.95,
            },
            {
              id: 'po-execution',
              label: '采购订单执行率',
              dataKey: 'supplyChain.poExecutionRate',
              target: 0.98,
            },
          ],
        },
        {
          id: 'inventory-completeness',
          label: '库存齐套率',
          dataKey: 'supplyChain.inventoryCompletenessRate',
          target: 0.96,
          children: [
            {
              id: 'material-availability',
              label: '原材料库存满足率',
              dataKey: 'supplyChain.materialAvailabilityRate',
              target: 0.8,
            },
            {
              id: 'substitute-available',
              label: '物料替代可用率',
              dataKey: 'supplyChain.substituteAvailableRate',
              target: 0.9,
            },
          ],
        },
      ],
    },
    {
      id: 'production',
      label: '生产达成率',
      icon: '🏭',
      dataKey: 'production.productionRate',
      target: 0.92,
      children: [
        {
          id: 'wo-plan-achievement',
          label: '工单计划达成率',
          dataKey: 'production.woPlanAchievementRate',
          target: 0.93,
          children: [
            {
              id: 'operation-on-time',
              label: '工序准时完成率',
              dataKey: 'production.operationOnTimeRate',
              target: 0.94,
            },
            {
              id: 'machine-utilization',
              label: '机台稼动率',
              dataKey: 'production.machineUtilizationRate',
              target: 0.85,
            },
          ],
        },
        {
          id: 'quality-rate',
          label: '质量合格率',
          dataKey: 'production.qualityPassRate',
          target: 0.98,
          children: [
            {
              id: 'first-pass-yield',
              label: '一次检验合格率',
              dataKey: 'production.firstPassYield',
              target: 0.97,
            },
            {
              id: 'rework-rate',
              label: '返工率',
              dataKey: 'production.reworkRate',
              target: 0.03,
              lowerBetter: true,
            },
          ],
        },
      ],
    },
    {
      id: 'logistics',
      label: '物流交付率',
      icon: '📦',
      dataKey: 'logistics.logisticsRate',
      target: 0.95,
      children: [
        {
          id: 'shipping-on-time',
          label: '发货及时率',
          dataKey: 'logistics.shippingOnTimeRate',
          target: 0.96,
        },
        {
          id: 'transport-on-time',
          label: '运输准时率',
          dataKey: 'logistics.transportOnTimeRate',
          target: 0.95,
        },
      ],
    },
  ],
};

function getNestedValue(obj, path) {
  if (!obj || !path) return undefined;
  const keys = path.split('.');
  let result = obj;
  for (const key of keys) {
    if (result === undefined || result === null) return undefined;
    result = result[key];
  }
  return result;
}

function formatPercent(value) {
  return value !== undefined && value !== null && Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : '--';
}

function getMetricTarget(node, metricsData) {
  const explicitTarget = getNestedValue(metricsData, node.targetKey);
  const inferredTarget = getNestedValue(metricsData, `${node.dataKey}Target`);
  return explicitTarget ?? inferredTarget ?? node.target;
}

function getMetricStatus(node, metricsData) {
  const value = getNestedValue(metricsData, node.dataKey);
  const target = getMetricTarget(node, metricsData);

  if (value === undefined || value === null || target === undefined || target === null) {
    return 'unknown';
  }

  const numericValue = Number(value);
  const numericTarget = Number(target);

  if (!Number.isFinite(numericValue) || !Number.isFinite(numericTarget)) {
    return 'unknown';
  }

  return node.lowerBetter ? numericValue <= numericTarget ? 'normal' : 'abnormal' : numericValue >= numericTarget ? 'normal' : 'abnormal';
}

function getMaxDepth(node, depth = 0) {
  if (!node.children || node.children.length === 0) return depth;
  return Math.max(...node.children.map(child => getMaxDepth(child, depth + 1)));
}

function buildTreeLayout(root, metricsData) {
  const nodes = [];
  const edges = [];
  let leafIndex = 0;
  const maxDepth = getMaxDepth(root);

  function walk(node, depth, parent) {
    const children = node.children || [];
    const childLayouts = children.map(child => walk(child, depth + 1, node));
    const y = childLayouts.length > 0
      ? childLayouts.reduce((sum, child) => sum + child.y, 0) / childLayouts.length
      : PADDING_Y + leafIndex++ * (CARD_HEIGHT + ROW_GAP);
    const x = PADDING_X + depth * (CARD_WIDTH + COLUMN_GAP);
    const status = getMetricStatus(node, metricsData);
    const layoutNode = { node, x, y, depth, status };

    nodes.push(layoutNode);

    if (parent) {
      edges.push({
        id: `${parent.id}-${node.id}`,
        fromId: parent.id,
        toId: node.id,
        color: STATUS_THEME[status].color,
      });
    }

    return layoutNode;
  }

  walk(root, 0, null);

  return {
    nodes,
    edges,
    width: PADDING_X * 2 + (maxDepth + 1) * CARD_WIDTH + maxDepth * COLUMN_GAP,
    height: PADDING_Y * 2 + Math.max(leafIndex, 1) * CARD_HEIGHT + Math.max(leafIndex - 1, 0) * ROW_GAP,
  };
}

function MetricCard({ layoutNode, metricsData }) {
  const { node, x, y, depth, status } = layoutNode;
  const value = getNestedValue(metricsData, node.dataKey);
  const target = getMetricTarget(node, metricsData);
  const theme = STATUS_THEME[status];

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
        borderRadius: 12,
        background: theme.background,
        border: `1px solid ${theme.border}`,
        boxShadow: theme.shadow,
        boxSizing: 'border-box',
        padding: '10px 12px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        zIndex: 2,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
          {/* {node.icon && (
            <span style={{ fontSize: depth === 0 ? 16 : 13, lineHeight: 1, flexShrink: 0 }}>
              {node.icon}
            </span>
          )} */}
          <span style={{
            color: depth === 0 ? '#17324d' : '#315a7d',
            fontSize: depth === 0 ? 13 : 12,
            fontWeight: depth === 0 ? 800 : 700,
            lineHeight: 1.25,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}>
            {node.label}
          </span>
        </div>
        <span style={{
          color: theme.color,
          background: `${theme.color}14`,
          border: `1px solid ${theme.color}24`,
          borderRadius: 999,
          fontSize: 8,
          fontWeight: 700,
          padding: '1px 5px',
          lineHeight: 1.2,
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}>
          {theme.label}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ color: '#7a9ab8', fontSize: 9, letterSpacing: '0.12em' }}>当前值</div>
          <div style={{
            color: theme.color,
            fontSize: 15,
            fontWeight: 800,
            fontFamily: "'IBM Plex Mono', monospace",
            lineHeight: 1.1,
            whiteSpace: 'nowrap',
          }}>
            {formatPercent(value)}
          </div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ color: '#7a9ab8', fontSize: 9, letterSpacing: '0.12em' }}>目标值</div>
          <div style={{
            color: '#1a3a5c',
            fontSize: 11,
            fontWeight: 700,
            fontFamily: "'IBM Plex Mono', monospace",
            lineHeight: 1.2,
            whiteSpace: 'nowrap',
          }}>
            {formatPercent(target)}
          </div>
        </div>
      </div>
    </div>
  );
}

function TreeConnectors({ layout }) {
  const nodeMap = new Map(layout.nodes.map(item => [item.node.id, item]));

  return (
    <svg
      width={layout.width}
      height={layout.height}
      style={{ position: 'absolute', left: 0, top: 0, zIndex: 1, overflow: 'visible' }}
    >
      {layout.edges.map(edge => {
        const from = nodeMap.get(edge.fromId);
        const to = nodeMap.get(edge.toId);
        const startX = from.x + CARD_WIDTH;
        const startY = from.y + CARD_HEIGHT / 2;
        const endX = to.x;
        const endY = to.y + CARD_HEIGHT / 2;
        const midX = startX + (endX - startX) / 2;
        const path = `M ${startX} ${startY} H ${midX} V ${endY} H ${endX}`;

        return (
          <path
            key={edge.id}
            d={path}
            fill="none"
            stroke={edge.color}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.58"
          />
        );
      })}
    </svg>
  );
}

function MetricTreeGraph({ metricsData }) {
  const layout = buildTreeLayout(METRIC_TREE_DATA, metricsData);

  return (
    <div style={{ minWidth: layout.width, minHeight: layout.height, position: 'relative' }}>
      <TreeConnectors layout={layout} />
      {layout.nodes.map(layoutNode => (
        <MetricCard key={layoutNode.node.id} layoutNode={layoutNode} metricsData={metricsData} />
      ))}
    </div>
  );
}

export default function MetricTree({ metricsData, loading = false }) {
  return (
    <div style={{
      height: '100%',
      overflow: 'auto',
      padding: '8px 10px',
      boxSizing: 'border-box',
    }}>
      {loading ? (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          color: '#7a9ab8',
          fontSize: 12,
        }}>
          <div style={{
            width: 20,
            height: 20,
            border: '2px solid rgba(24,144,255,0.2)',
            borderTop: '2px solid #1890ff',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            marginRight: 8,
          }} />
          加载中...
        </div>
      ) : (
        <MetricTreeGraph metricsData={metricsData || {}} />
      )}
    </div>
  );
}
