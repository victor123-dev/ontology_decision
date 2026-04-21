// 供应链控制塔 - 供应链地图组件
// 只渲染：图例 + SVG节点 + 路线连线
// 无任何背景填充、无蒙层、无遮罩
import { useState, useEffect } from "react";

// 城市坐标映射（相对于SVG画布 viewBox="300 60 480 440"）
const cityCoords = {
  '北京':   { x: 650, y: 215 },
  '武汉':   { x: 628, y: 308 },
  '上海':   { x: 693, y: 300 },
  '上海港': { x: 695, y: 302 },
  '天津港': { x: 662, y: 232 },
  '天津':   { x: 660, y: 230 },
  '深圳':   { x: 630, y: 390 },
  '深圳港': { x: 632, y: 391 },
  '广州港': { x: 621, y: 389 },
  '广州':   { x: 619, y: 387 } };

// 全屏模式城市坐标
const cityCoordsFullscreen = {
  '深圳':   { x: 660, y: 413 },
  '深圳港': { x: 663, y: 414 },
  '北京':   { x: 670, y: 215 },
  '武汉':   { x: 650, y: 330 },
  '上海':   { x: 720, y: 320 },
  '上海港': { x: 722, y: 319 },
  '天津港': { x: 686, y: 232 },
  '天津':   { x: 685, y: 230 },
  '广州港': { x: 636, y: 412 },
  '广州':   { x: 638, y: 414 } };

const nodeTypeConfig = { factory:   { color: '#3b82f6', size: 12, label: '工厂' },
  customer:  { color: '#22c55e', size: 9,  label: '客户' },
  supplier:  { color: '#f59e0b', size: 9,  label: '供应商' },
  logistics: { color: '#8b5cf6', size: 8,  label: '物流' } };

const routeTypeConfig = { supply:    { color: '#f59e0b', dash: '6,4' },
  delivery:  { color: '#22c55e', dash: '6,4' },
  logistics: { color: '#8b5cf6', dash: '4,6' } };

export default function SupplyChainMap({ mapData = { nodes: [], routes: [] }, loading = false, isFullscreen = false }) {
  const [hoveredNode, setHoveredNode] = useState(null);
  const [animFrame, setAnimFrame] = useState(0);

  // 根据全屏状态选择对应的城市坐标
  const coords = isFullscreen ? cityCoordsFullscreen : cityCoords;

  useEffect(() => { const interval = setInterval(() => { setAnimFrame(f => (f + 1) % 60); }, 50);
    return () => clearInterval(interval); }, []);

  // 加载状态
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <div style={{
          width: '32px', height: '32px',
          border: '3px solid rgba(59,130,246,0.2)',
          borderTop: '3px solid #3b82f6',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }} />
      </div>
    );
  }

  const mapNodes = mapData?.nodes || [];
  const mapRoutes = mapData?.routes || [];

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%',
      display: 'flex', flexDirection: 'column', background: 'transparent' }}>
      {/* 图例 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px',
        padding: '8px 12px', flexShrink: 0, flexWrap: 'wrap' }}>
        {Object.entries(nodeTypeConfig).map(([type, cfg]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%',
              background: cfg.color }} />
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>{cfg.label}</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
          <div style={{ width: '24px', borderTop: '2px dashed', borderColor: '#f59e0b' }} />
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>供应</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '24px', borderTop: '2px dashed', borderColor: '#22c55e' }} />
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>配送</span>
        </div>
      </div>

      {/* SVG 层：只有节点 + 路线，完全透明背景 */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <svg
          viewBox="300 60 480 440"
          style={{ width: '100%', height: '100%', background: 'transparent' }}
        >
          {/* 路线 */}
          {mapRoutes.map((route, idx) => { const fromNode = mapNodes.find(n => n.id === route.from);
            const toNode   = mapNodes.find(n => n.id === route.to);
            if (!fromNode || !toNode) return null;
            const fromCoord = coords[fromNode.city];
            const toCoord   = coords[toNode.city];
            if (!fromCoord || !toCoord) return null;
            const cfg = routeTypeConfig[route.type];
            const midX = (fromCoord.x + toCoord.x) / 2;
            const midY = (fromCoord.y + toCoord.y) / 2 - 30;

            return (
              <g key={idx}>
                <path
                  d={`M ${fromCoord.x} ${fromCoord.y} Q ${midX} ${midY} ${toCoord.x} ${toCoord.y}`}
                  fill="none"
                  stroke={cfg.color}
                  strokeWidth={route.active ? 1.8 : 0.8}
                  strokeDasharray={cfg.dash}
                  opacity={route.active ? 0.85 : 0.35}
                />
              </g>
            ); })}

          {/* 节点 */}
          {mapNodes.map((node) => { const coord = coords[node.city];
            if (!coord) return null;
            const cfg = nodeTypeConfig[node.type];
            const isHovered = hoveredNode?.id === node.id;
            const pulse = Math.sin(animFrame * 0.1) * 0.3 + 0.7;

            return (
              <g
                key={node.id}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* 脉冲光晕 */}
                <circle
                  cx={coord.x}
                  cy={coord.y}
                  r={cfg.size * 2.8}
                  fill={cfg.color}
                  opacity={pulse * 0.18}
                />
                {/* 主节点 */}
                <circle
                  cx={coord.x}
                  cy={coord.y}
                  r={isHovered ? cfg.size * 1.4 : cfg.size}
                  fill={cfg.color}
                  opacity={0.92}
                  stroke={isHovered ? '#fff' : 'rgba(255,255,255,0.3)'}
                  strokeWidth={isHovered ? 2 : 1}
                />
                {/* 内圆白点 */}
                <circle
                  cx={coord.x}
                  cy={coord.y}
                  r={cfg.size * 0.45}
                  fill="rgba(255,255,255,0.95)"
                />
                {/* 城市标签（带轻微文字阴影增强可读性） */}
                <text
                  x={coord.x}
                  y={coord.y + cfg.size + 13}
                  textAnchor="middle"
                  fill="rgba(226,232,240,0.95)"
                  fontSize="9"
                  fontFamily="Noto Sans SC, sans-serif"
                  fontWeight="600"
                  style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.8))' }}
                >
                  {node.city}
                </text>
              </g>
            ); })}

          {/* 悬停提示框 */}
          {hoveredNode && (() => { const coord = coords[hoveredNode.city];
            if (!coord) return null;
            const cfg = nodeTypeConfig[hoveredNode.type];
            const boxX = Math.min(coord.x + 15, 700);
            const boxY = Math.max(coord.y - 40, 70);
            return (
              <g>
                <rect x={boxX} y={boxY} width={165} height={44} rx="4"
                  fill="rgba(11,20,38,0.96)" stroke={cfg.color} strokeWidth="1" />
                <text x={boxX + 8} y={boxY + 17} fill={cfg.color} fontSize="10"
                  fontFamily="Noto Sans SC" fontWeight="700">{hoveredNode.name}</text>
                <text x={boxX + 8} y={boxY + 33} fill="rgba(148,163,184,0.9)" fontSize="9"
                  fontFamily="Noto Sans SC">{cfg.label} · {hoveredNode.city}</text>
              </g>
            ); })()}
        </svg>
      </div>
    </div>
  ); }
