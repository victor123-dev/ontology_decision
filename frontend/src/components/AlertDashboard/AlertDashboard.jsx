// 供应链控制塔 - 主页面
// 深蓝科技风格：顶部导航 + 看板Tab + 预警Tab
// 支持：拖拽布局（react-grid-layout）、全屏展示、图表筛选+下钻
import "./index.css";
import { useState, useCallback, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import GridLayout from "react-grid-layout";
import { LayoutDashboard, Bell, TrendingUp, Package, Truck, Factory,
  ShoppingCart, AlertTriangle, CheckCircle, Clock, Filter,
  ChevronDown, RefreshCw, Settings, User, Search,
  Maximize2, Minimize2, GripHorizontal } from "lucide-react";
import KpiCard from "./components/KpiCard";
import SupplyChainMap from "./components/SupplyChainMap";

import AlertDrawer from "./components/AlertDrawer";
import SalesForecastChart from "./components/SalesForecastChart";
import ForecastTable from "./components/ForecastTable";
import { useKpiData, useLogisticsData, useAlertMessages } from "./hooks/useApiData";
import { getRiskTextColor, getStatusColor, getLogisticsStatusColor } from "./lib/data";
import { useWindowSize } from "./hooks/useWindowSize";

// rowHeight=8px，cols=24
// KPI行：独立于GridLayout，固定高度105px，无留白
// 图表/地图行：h=24 → 192+23=215px（匹配线上版本约190px）
// 图表占左宽57%（w=14/24），地图占右宽43%（w=10/24）
// 物流占左宽43%（w=10/24），预测占右宽57%（w=14/24）
// 物流/预测行：h=29 → 232+28=260px（匹配线上版本约230px）
// 预警概览行：h=14 → 112+13=125px（匹配线上版本约110px）
const INITIAL_LAYOUT = [
  // kpi 行已移出 GridLayout，不再占用 layout 格子
  { i: 'chart',     x: 0,  y: 0,  w: 14, h: 24,  minH: 18, minW: 8 },
  { i: 'map',       x: 14, y: 0,  w: 10, h: 24,  minH: 18, minW: 6 },
  { i: 'logistics', x: 0,  y: 24, w: 10, h: 29,  minH: 20, minW: 5 },
  { i: 'forecast',  x: 10, y: 24, w: 14, h: 29,  minH: 20, minW: 8 },
  { i: 'alertsnap', x: 0,  y: 53, w: 24, h: 14,  minH: 12 },
];

const ROW_HEIGHT = 8; // px per grid row unit
const GRID_MARGIN = [12, 12];

// ─── 内联 Widget 容器（支持拖拽手柄 + 全屏） ───────────────────────────────
function Widget({ title, subtitle, children, headerRight, fullscreenContent, fullscreenNoPadding }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 全屏 overlay 通过 Portal 渲染到 document.body，确保覆盖整个页面
  const fullscreenOverlay = isFullscreen ? createPortal(
    <div
      style={{ position: 'fixed', inset: 0, zIndex: 9999,
        background: '#0b1426',
        display: 'flex', flexDirection: 'column' }}
    >
      <div
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 24px', flexShrink: 0,
          borderBottom: '1px solid rgba(59,130,246,0.2)',
          background: 'rgba(15,29,53,0.98)' }}
      >
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: '#f1f5f9', margin: 0 }}>{title}</h2>
          {subtitle && <p style={{ fontSize: 11, color: '#64748b', margin: '2px 0 0' }}>{subtitle}</p>}
        </div>
        <button
          onClick={() => setIsFullscreen(false)}
          style={{ display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 8,
            fontSize: 13, color: '#cbd5e1', cursor: 'pointer',
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.12)' }}
        >
          <Minimize2 size={14} />
          退出全屏
        </button>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', padding: fullscreenNoPadding ? 0 : 24, display: 'flex', flexDirection: 'column' }}>
        {fullscreenContent ?? children}
      </div>
    </div>,
    document.body
  ) : null;

  return (
    <>
      {/* 正常卡片 */}
      <div style={{
        display: 'flex', flexDirection: 'column', height: '100%',
        background: '#0f1d35', borderRadius: '8px',
        border: '1px solid rgba(59,130,246,0.12)',
        overflow: 'hidden'
      }}>
        {/* 标题栏 - 拖拽手柄 */}
        <div
          className="widget-drag-handle"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '8px 16px', flexShrink: 0, userSelect: 'none',
            borderBottom: '1px solid rgba(59,130,246,0.12)', cursor: 'move' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
            <GripHorizontal size={13} style={{ color: '#475569', flexShrink: 0 }} />
            <div style={{ minWidth: 0 }}>
              <span style={{ fontSize: '14px', fontWeight: 600, color: '#e2e8f0',
                display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</span>
              {subtitle && <span style={{ fontSize: '10px', color: '#64748b' }}>{subtitle}</span>}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            {headerRight}
            <button
              onMouseDown={e => e.stopPropagation()}
              onClick={e => { e.stopPropagation(); setIsFullscreen(true); }}
              style={{ width: '24px', height: '24px', display: 'flex', alignItems: 'center',
                justifyContent: 'center', borderRadius: '4px', color: '#64748b', cursor: 'pointer',
                background: 'transparent', border: 'none', transition: 'all 0.2s' }}
              onMouseOver={e => {
                e.currentTarget.style.color = '#cbd5e1';
                e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
              }}
              onMouseOut={e => {
                e.currentTarget.style.color = '#64748b';
                e.currentTarget.style.background = 'transparent';
              }}
              title="全屏展示"
            >
              <Maximize2 size={12} />
            </button>
          </div>
        </div>
        {/* 内容区 - 无多余 padding，内容自适应 */}
        <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
          {children}
        </div>
      </div>

      {/* 全屏 Portal */}
      {fullscreenOverlay}
    </>
  );
}

// ─── KPI 行容器（支持拖拽手柄 + 全屏） ────────────────────────────────────
function KpiWidget({ children }) {
  return (
    // 外层容器高度固定为105px，防止被 GridLayout 拉伸
    <div style={{ height: 105, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 拖拽手柄条 */}
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '8px',
          padding: '0 12px', flexShrink: 0, userSelect: 'none',
          cursor: 'move', borderBottom: '1px solid rgba(59,130,246,0.08)', height: 20, minHeight: 20 }}
      >
        <GripHorizontal size={11} style={{ color: '#334155' }} />
        <span style={{ fontSize: '10px', color: '#334155',
          letterSpacing: '0.2em', textTransform: 'uppercase' }}>KPI 指标</span>
      </div>
      {/* KPI 卡片网格 */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, padding: '6px 8px', minHeight: 0 }}>
        {children}
      </div>
    </div>
  );
}

export default function AlertDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [alertFilter, setAlertFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [lastRefresh] = useState(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
  const [layout, setLayout] = useState(INITIAL_LAYOUT);
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(1280);

  // 使用 API Hooks 获取数据
  const { data: kpiData, loading: kpiLoading } = useKpiData();
  const { data: logisticsData, loading: logisticsLoading } = useLogisticsData();
  const { data: alertsData, loading: alertsLoading, refetch: refetchAlerts } = useAlertMessages();
  const [alerts, setAlerts] = useState([]);

  // 监听容器宽度变化
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth);
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  // 当 API 数据加载完成后更新 alerts
  useEffect(() => {
    if (alertsData && alertsData.length > 0) {
      setAlerts(alertsData);
    }
  }, [alertsData]);

  const handleStatusChange = (id, status) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, status } : a));
    if (selectedAlert?.id === id) {
      setSelectedAlert(prev => prev ? { ...prev, status } : prev);
    }
  };

  const filteredAlerts = alerts.filter(a => {
    const matchStatus = alertFilter === 'all' || a.status === alertFilter;
    const matchRisk = riskFilter === 'all' || a.riskLevel === riskFilter;
    const matchSearch = !searchText || a.title.includes(searchText) || a.supplier.includes(searchText) || a.customer.includes(searchText);
    return matchStatus && matchRisk && matchSearch;
  });

  const unhandledCount = alerts.filter(a => a.status === '未处理').length;

  // 根据 layout 中的 h 计算实际像素高度
  const getItemPx = useCallback((id) => {
    const item = layout.find(l => l.i === id);
    return item ? item.h * ROW_HEIGHT + (item.h - 1) * GRID_MARGIN[1] : 300;
  }, [layout]);

  // 使用容器宽度，不额外减去padding（padding已在容器上设置）
  const gridWidth = Math.max(containerWidth, 800);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column',
      background: '#0b1426', fontFamily: "'Noto Sans SC', sans-serif", overflow: 'hidden', width: '100%' }}>
      {/* 顶部导航 */}
      <header
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          height: '64px',
          padding: '0 24px',
          background: 'linear-gradient(90deg, #0d1a2e, #0f1d35)',
          borderBottom: '1px solid rgba(59,130,246,0.2)',
          boxShadow: '0 2px 16px rgba(0,0,0,0.4)',
          flexShrink: 0 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '0 0 auto' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'linear-gradient(135deg, #1e40af, #0891b2)' }}>
            <Factory size={18} style={{ color: '#fff' }} />
          </div>
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: 'bold', color: '#f1f5f9',
              lineHeight: '1.2', letterSpacing: '-0.02em', margin: 0 }}>供应链控制塔</h1>
            <p style={{ fontSize: '10px', color: '#64748b', margin: '2px 0 0' }}>
              Supply Chain Control Tower · 半导体制造</p>
          </div>
        </div>

        <nav style={{ display: 'flex', alignItems: 'center', gap: '4px', flex: '0 1 auto', justifyContent: 'center' }}>
          {[
            { id: 'dashboard', label: '控制看板', icon: LayoutDashboard },
            { id: 'alerts', label: `预警中心${unhandledCount > 0 ? ` (${unhandledCount})` : ''}`, icon: Bell },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px',
                padding: '8px 16px', borderRadius: '6px',
                fontSize: '13px', fontWeight: 500,
                transition: 'all 0.2s',
                cursor: 'pointer',
                ...(activeTab === id
                  ? { background: 'rgba(59,130,246,0.15)', color: '#60a5fa',
                      border: '1px solid rgba(59,130,246,0.3)' }
                  : { color: '#64748b', border: '1px solid transparent',
                      background: 'transparent' }) }}
              onMouseOver={e => {
                if (activeTab !== id) {
                  e.currentTarget.style.color = '#94a3b8';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                }
              }}
              onMouseOut={e => {
                if (activeTab !== id) {
                  e.currentTarget.style.color = '#64748b';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '0 0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px',
            fontSize: '12px', color: '#64748b' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%',
              background: '#4ade80', animation: 'pulse 2s ease-out infinite' }} />
            <span>实时更新 {lastRefresh}</span>
          </div>
          <button style={{ width: '32px', height: '32px', borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#94a3b8', cursor: 'pointer',
            background: 'transparent', border: 'none', transition: 'all 0.2s' }}
            onMouseOver={e => e.currentTarget.style.color = '#e2e8f0'}
            onMouseOut={e => e.currentTarget.style.color = '#94a3b8'}
          >
            <RefreshCw size={14} />
          </button>
          <button style={{ width: '32px', height: '32px', borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#94a3b8', cursor: 'pointer',
            background: 'transparent', border: 'none', transition: 'all 0.2s' }}
            onMouseOver={e => e.currentTarget.style.color = '#e2e8f0'}
            onMouseOut={e => e.currentTarget.style.color = '#94a3b8'}
          >
            <Settings size={14} />
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px', borderRadius: '8px',
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div style={{ width: '24px', height: '24px', borderRadius: '50%',
              background: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <User size={12} style={{ color: '#fff' }} />
            </div>
            <span style={{ fontSize: '12px', color: '#cbd5e1' }}>供应链管理员</span>
            <ChevronDown size={12} style={{ color: '#64748b' }} />
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main style={{ flex: 1, overflow: 'auto', width: '100%', display: 'flex', flexDirection: 'column' }}>

        {/* ==================== 控制看板 ==================== */}
        {activeTab === 'dashboard' && (
          <div ref={containerRef} style={{ width: '100%', flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* ── KPI 卡片行：独立于GridLayout，宽度与GridLayout一致 ── */}
            <div style={{ padding: '16px 0 12px 0' }}>
              <KpiWidget>
                <KpiCard title="采购到货及时率" value={kpiData?.purchaseOnTimeRate?.val ?? 0} format="percent" trend={kpiData?.purchaseOnTimeRate?.trendVal > 0 ? 'up' : 'down'} trendValue={`${kpiData?.purchaseOnTimeRate?.trendVal > 0 ? '+' : ''}${kpiData?.purchaseOnTimeRate?.trendVal?.toFixed(1)}%`} icon={<Truck size={16} />} color="#3b82f6" delay={0} loading={kpiLoading} />
                <KpiCard title="当月销售金额" value={kpiData?.monthlySalesAmount?.val ?? 0} unit="万元" format="currency" trend={kpiData?.monthlySalesAmount?.trendVal > 0 ? 'up' : 'down'} trendValue={`${kpiData?.monthlySalesAmount?.trendVal > 0 ? '+' : ''}${kpiData?.monthlySalesAmount?.trendVal?.toFixed(1)}%`} icon={<ShoppingCart size={16} />} color="#22c55e" delay={100} loading={kpiLoading} />
                <KpiCard title="当月销售数量" value={kpiData?.monthlySalesQty?.val ?? 0} unit="件" format="integer" trend={kpiData?.monthlySalesQty?.trendVal > 0 ? 'up' : 'down'} trendValue={`${kpiData?.monthlySalesQty?.trendVal > 0 ? '+' : ''}${kpiData?.monthlySalesQty?.trendVal?.toFixed(1)}%`} icon={<Package size={16} />} color="#06b6d4" delay={200} loading={kpiLoading} />
                <KpiCard title="活跃预警消息" value={kpiData?.alertCount?.val ?? 0} unit="条" format="integer" trend={kpiData?.alertCount?.trendVal > 0 ? 'up' : 'down'} trendValue={`+${kpiData?.alertCount?.trendVal ?? 0}条`} icon={<AlertTriangle size={16} />} color="#ef4444" delay={300} loading={kpiLoading} />
                <KpiCard title="自动执行次数" value={kpiData?.alertExecCount?.val ?? 0} unit="次" format="integer" trend={kpiData?.alertExecCount?.trendVal > 0 ? 'up' : 'down'} trendValue={`+${kpiData?.alertExecCount?.trendVal ?? 0}次`} icon={<TrendingUp size={16} />} color="#8b5cf6" delay={400} loading={kpiLoading} />
              </KpiWidget>
            </div>

            <GridLayout
              className="layout"
              layout={layout}
              gridConfig={{ cols: 24,
                rowHeight: ROW_HEIGHT,
                margin: GRID_MARGIN,
                containerPadding: [0, 0] }}
              dragConfig={{ handle: '.widget-drag-handle' }}
              resizeConfig={{ handles: ['se', 's', 'e'] }}
              width={gridWidth}
              onLayoutChange={(newLayout) => setLayout([...newLayout])}
            >
              {/* ── 销售预测图表 ── */}
              <div key="chart">
                <Widget
                  title="销售预测 vs 实际订单 vs 采购量"
                  subtitle="近12个月 · 点击月份可下钻查看产品明细"
                  fullscreenContent={<SalesForecastChart height={window.innerHeight - 160} />}
                >
                  <SalesForecastChart height={getItemPx('chart') - 72} />
                </Widget>
              </div>

              {/* ── 供应链地图 ── */}
              <div key="map">
                <Widget
                  title="供应链地图"
                  subtitle="实时节点状态"
                  fullscreenNoPadding
                  fullscreenContent={ <div
                      style={{ flex: 1,
                        minHeight: 0,
                        backgroundImage: `url(https://d2xsxph8kpxj0f.cloudfront.net/310519663439243238/eAaE9FZQc3rqCtqMQX6MhY/china-map-bg-VBnkueTcA3KJzfiArGZZLF.webp)`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                        position: 'relative' }}
                    >
                      <SupplyChainMap />
                    </div> }
                >
                  {/* 地图容器：背景图 + SVG节点，无任何蒙层 */}
                  <div
                    style={{ width: '100%',
                      height: getItemPx('map') - 52,
                      backgroundImage: `url(https://d2xsxph8kpxj0f.cloudfront.net/310519663439243238/eAaE9FZQc3rqCtqMQX6MhY/china-map-bg-VBnkueTcA3KJzfiArGZZLF.webp)`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                      position: 'relative' }}
                  >
                    <SupplyChainMap />
                  </div>
                </Widget>
              </div>

              {/* ── 物流动态 ── */}
              <div key="logistics">
                <Widget title="物流动态" subtitle={`今日 · ${logisticsData?.length ?? 0} 条`}>
                  <div style={{ overflow: 'hidden', padding: '0 16px',
                    height: getItemPx('logistics') - 48 }}>
                    <div style={{ height: '100%', overflowY: 'hidden' }}>
                      <div className="sct-scroll-list">
                        {[...logisticsData, ...logisticsData].map((item, idx) => (
                          <div
                            key={`${item.id}-${idx}`}
                            style={{ padding: '14px 0',
                              borderBottom: idx === logisticsData.length * 2 - 1 ? 'none' : '1px solid rgba(255,255,255,0.06)' }}
                          >
                            {/* 状态点 + 物料名称 + 状态标签 */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                              <div style={{ width: '6px', height: '6px', borderRadius: '50%',
                                background: getLogisticsStatusColor(item.status),
                                flexShrink: 0, alignSelf: 'center' }} />
                              <p style={{ fontSize: '14px', color: '#e2e8f0',
                                fontWeight: 500, flex: 1, lineHeight: '1.4',
                                margin: 0 }}>
                                {item.material}
                              </p>
                              <span
                                style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '4px',
                                  background: `${getLogisticsStatusColor(item.status)}20`,
                                  color: getLogisticsStatusColor(item.status),
                                  border: `1px solid ${getLogisticsStatusColor(item.status)}30`,
                                  fontWeight: 500, flexShrink: 0 }}
                              >
                                {item.status}
                              </span>
                            </div>
                            {/* 路线信息 */}
                            <p style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>
                              {item.from} → {item.to}
                            </p>
                            {/* 物流商和时间 */}
                            <p style={{ fontSize: '11px', color: '#475569' }}>
                              {item.carrier} · {item.time}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </Widget>
              </div>

              {/* ── 需求预测表 ── */}
              <div key="forecast">
                <Widget
                  title="需求预测（未来6个月）"
                  subtitle="点击产品可下钻查看月度明细与采购建议"
                  fullscreenContent={<ForecastTable maxHeight={window.innerHeight - 200} />}
                >
                  <ForecastTable maxHeight={getItemPx('forecast') - 56} />
                </Widget>
              </div>

              {/* ── 预警概览 ── */}
              <div key="alertsnap">
                <Widget
                  title="最新预警"
                  headerRight={ <button
                      onMouseDown={e => e.stopPropagation()}
                      onClick={e => { e.stopPropagation(); setActiveTab('alerts'); }}
                      style={{ fontSize: '12px', color: '#60a5fa',
                        transition: 'color 0.2s', display: 'flex',
                        alignItems: 'center', gap: '4px', cursor: 'pointer',
                        background: 'transparent', border: 'none' }}
                      onMouseOver={e => e.currentTarget.style.color = '#93c5fd'}
                      onMouseOut={e => e.currentTarget.style.color = '#60a5fa'}
                    >
                      查看全部 <ChevronDown size={10} style={{ transform: 'rotate(-90deg)' }} />
                    </button> }
                >
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: '12px', padding: '4px 16px 8px 16px', paddingTop: '4px' }}>
                    {alerts.slice(0, 4).map(alert => (
                      <div
                        key={alert.id}
                        style={{ padding: '12px', borderRadius: '8px', cursor: 'pointer',
                          background: 'rgba(255,255,255,0.04)',
                          border: `1px solid ${getRiskTextColor(alert.riskLevel)}30`,
                          transition: 'opacity 0.2s' }}
                        onMouseDown={e => e.stopPropagation()}
                        onMouseOver={e => e.currentTarget.style.opacity = '0.8'}
                        onMouseOut={e => e.currentTarget.style.opacity = '1'}
                        onClick={() => { setSelectedAlert(alert); setActiveTab('alerts'); }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center',
                          justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ fontSize: '10px', padding: '2px 6px',
                            borderRadius: '9999px',
                            background: `${getRiskTextColor(alert.riskLevel)}20`,
                            color: getRiskTextColor(alert.riskLevel) }}>
                            {alert.riskLevel}
                          </span>
                          <span style={{ fontSize: '10px',
                            color: getStatusColor(alert.status) }}>
                            {alert.status}
                          </span>
                        </div>
                        <p style={{ fontSize: '12px', color: '#cbd5e1',
                          lineHeight: '1.5',
                          display: '-webkit-box', WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {alert.title.replace(/【.*?】/, '')}
                        </p>
                        <p style={{ fontSize: '10px', color: '#64748b', marginTop: '6px' }}>
                          {alert.supplier}
                        </p>
                      </div>
                    ))}
                  </div>
                </Widget>
              </div>
            </GridLayout>
          </div>
        )}

        {/* ==================== 预警中心 ==================== */}
        {activeTab === 'alerts' && (
          <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', width: '100%' }}>
            {/* 统计卡片 */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', width: '100%' }}>
              {[
                { label: '全部预警', count: alerts.length, color: '#3b82f6', icon: Bell },
                { label: '未处理', count: alerts.filter(a => a.status === '未处理').length, color: '#ef4444', icon: AlertTriangle },
                { label: '处理中', count: alerts.filter(a => a.status === '处理中').length, color: '#f59e0b', icon: Clock },
                { label: '已处理', count: alerts.filter(a => a.status === '已处理').length, color: '#22c55e', icon: CheckCircle },
              ].map(({ label, count, color, icon: Icon }) => (
                <div key={label} style={{
                  background: '#0f1d35', borderRadius: '8px',
                  border: '1px solid rgba(59,130,246,0.12)',
                  padding: '16px', display: 'flex', alignItems: 'center', gap: '16px'
                }}>
                  <div style={{
                    width: '40px', height: '40px', borderRadius: '8px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, background: `${color}20`
                  }}>
                    <Icon size={18} style={{ color }} />
                  </div>
                  <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold', fontFamily: 'monospace', color }}>{count}</p>
                    <p style={{ fontSize: '12px', color: '#94a3b8' }}>{label}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* 筛选栏 */}
            <div style={{
              background: '#0f1d35', borderRadius: '8px',
              border: '1px solid rgba(59,130,246,0.12)',
              padding: '12px', display: 'flex', alignItems: 'center',
              gap: '12px', flexWrap: 'wrap', width: '100%'
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px', flex: 1,
                minWidth: '192px', borderRadius: '8px', padding: '8px 12px',
                background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <Search size={13} style={{ color: '#64748b', flexShrink: 0 }} />
                <input
                  type="text"
                  placeholder="搜索预警标题、供应商、客户..."
                  value={searchText}
                  onChange={e => setSearchText(e.target.value)}
                  style={{ flex: 1, background: 'transparent', fontSize: '14px',
                    color: '#e2e8f0', outline: 'none', border: 'none' }}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Filter size={12} style={{ color: '#64748b', marginRight: '4px' }} />
                {(['all', '未处理', '处理中', '已处理']).map((f, idx) => (
                  <button key={f} onClick={() => setAlertFilter(f)}
                    style={{ fontSize: '12px', padding: '6px 12px',
                      transition: 'all 0.2s', cursor: 'pointer',
                      borderRadius: idx === 0 ? '6px 0 0 6px' : idx === 3 ? '0 6px 6px 0' : '0',
                      ...(alertFilter === f
                        ? { background: 'rgba(59,130,246,0.2)', color: '#60a5fa',
                            border: '1px solid rgba(59,130,246,0.4)' }
                        : { color: '#94a3b8', border: '1px solid rgba(255,255,255,0.1)',
                            background: 'rgba(255,255,255,0.05)' }) }}
                    onMouseOver={e => {
                      if (alertFilter !== f) {
                        e.currentTarget.style.color = '#e2e8f0';
                        e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                      }
                    }}
                    onMouseOut={e => {
                      if (alertFilter !== f) {
                        e.currentTarget.style.color = '#94a3b8';
                        e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                      }
                    }}>
                    {f === 'all' ? '全部状态' : f}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {(['all', '最高风险', '高风险', '中风险', '低风险']).map((f, idx) => (
                  <button key={f} onClick={() => setRiskFilter(f)}
                    style={{ fontSize: '12px', padding: '6px 12px',
                      transition: 'all 0.2s', cursor: 'pointer',
                      borderRadius: idx === 0 ? '6px 0 0 6px' : idx === 4 ? '0 6px 6px 0' : '0',
                      ...(riskFilter === f
                        ? { background: f === 'all' ? 'rgba(59,130,246,0.2)' : `${getRiskTextColor(f)}20`,
                            color: f === 'all' ? '#60a5fa' : getRiskTextColor(f),
                            border: `1px solid ${f === 'all' ? 'rgba(59,130,246,0.4)' : getRiskTextColor(f) + '50'}` }
                        : { color: '#94a3b8', border: '1px solid rgba(255,255,255,0.1)',
                            background: 'rgba(255,255,255,0.05)' }) }}
                    onMouseOver={e => {
                      if (riskFilter !== f) {
                        e.currentTarget.style.color = '#e2e8f0';
                        e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                      }
                    }}
                    onMouseOut={e => {
                      if (riskFilter !== f) {
                        e.currentTarget.style.color = '#94a3b8';
                        e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                      }
                    }}>
                    {f === 'all' ? '全部风险' : f}
                  </button>
                ))}
              </div>
              <span style={{ fontSize: '12px', color: '#64748b', marginLeft: 'auto' }}>共 {filteredAlerts.length} 条</span>
            </div>

            {/* 预警列表 */}
            <div style={{
              background: '#0f1d35', borderRadius: '8px',
              border: '1px solid rgba(59,130,246,0.12)',
              overflow: 'hidden', width: '100%'
            }}>
              <table style={{ width: '100%' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.15)',
                    background: 'rgba(59,130,246,0.05)' }}>
                    {['风险等级', '预警标题', '规则编码', '供应商', '关联客户', '创建时间', '状态', '操作'].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '12px 16px',
                        fontSize: '12px', fontWeight: 500, color: '#94a3b8',
                        whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredAlerts.map((alert, idx) => (
                    <tr key={alert.id}
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.04)',
                        background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
                        transition: 'background 0.2s', cursor: 'pointer' }}
                      onMouseOver={e => e.currentTarget.style.background = 'rgba(59,130,246,0.08)'}
                      onMouseOut={e => e.currentTarget.style.background = idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)'}
                      onClick={() => setSelectedAlert(alert)}>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '9999px',
                          fontWeight: 500, whiteSpace: 'nowrap',
                          background: `${getRiskTextColor(alert.riskLevel)}20`,
                          color: getRiskTextColor(alert.riskLevel),
                          border: `1px solid ${getRiskTextColor(alert.riskLevel)}40` }}>
                          {alert.riskLevel}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <p style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 500,
                          maxWidth: '280px' }}>{alert.title}</p>
                        <p style={{ fontSize: '10px', color: '#64748b', marginTop: '2px',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          maxWidth: '280px' }}>
                          {alert.content.slice(0, 60)}...
                        </p>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontSize: '12px', fontFamily: 'monospace', color: '#94a3b8' }}>
                          {alert.ruleCode}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                          {alert.supplier}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                          {alert.customer}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontSize: '12px', color: '#94a3b8', whiteSpace: 'nowrap' }}>
                          {alert.createdAt}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '9999px',
                          whiteSpace: 'nowrap',
                          background: `${getStatusColor(alert.status)}20`,
                          color: getStatusColor(alert.status),
                          border: `1px solid ${getStatusColor(alert.status)}40` }}>
                          {alert.status}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <button style={{ fontSize: '12px', padding: '6px 12px', borderRadius: '8px',
                          transition: 'all 0.2s', cursor: 'pointer',
                          background: 'rgba(59,130,246,0.15)', color: '#60a5fa',
                          border: '1px solid rgba(59,130,246,0.3)' }}
                          onClick={e => { e.stopPropagation(); setSelectedAlert(alert); }}>
                          查看详情
                        </button>
                      </td>
                    </tr>
                  ))}
                  {filteredAlerts.length === 0 && (
                    <tr><td colSpan={8} style={{ padding: '48px', textAlign: 'center',
                      color: '#64748b', fontSize: '14px' }}>暂无符合条件的预警消息</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* 预警详情抽屉 */}
      {selectedAlert && (
        <AlertDrawer alert={selectedAlert} onClose={() => setSelectedAlert(null)} onStatusChange={handleStatusChange} />
      )}


    </div>
  );
}