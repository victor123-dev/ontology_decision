// 供应链控制塔 - 主页面
// 深蓝科技风格：顶部导航 + 看板Tab + 预警Tab
// 支持：拖拽布局（react-grid-layout）、全屏展示、图表筛选+下钻
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import "./index.css";
import { useState, useCallback, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import GridLayout from "react-grid-layout";
import { LayoutDashboard, Bell, TrendingUp, Package, Truck, Factory,
  ShoppingCart, AlertTriangle, CheckCircle, Clock, Filter,
  ChevronDown, RefreshCw, Settings, User, Search,
  Maximize2, Minimize2, GripHorizontal } from "lucide-react";
import KpiCard from "./components/KpiCard";

// 供应链运营监控组件
import RiskList from './components/RiskList';
import PurchaseMonitoring from './components/PurchaseMonitoring';
import InventoryHealth from './components/InventoryHealth';
import ProductionTracking from './components/ProductionTracking';
import SalesOverview from './components/SalesOverview';
import RiskCharts from './components/RiskCharts';
import CustomerOrderTrend from './components/CustomerOrderTrend';

// 运营和风险数据hooks
import { usePOExecutionRate, useInventoryHealthRate, useWOOnTimeDeliveryRate, useMonthlyCustomerOrderAmount } from './hooks/useOperationData';
import { useActiveRiskCount, useHighRiskSupplierCount } from './hooks/useRiskData';
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
  // 第一行: 风险列表(左) + 采购执行(中) + 风险统计(右上) - 风险供应商(右下)
  { i: 'riskList', x: 0, y: 0, w: 10, h: 28, minH: 20, minW: 8 },
  { i: 'purchaseMonitoring', x: 10, y: 0, w: 8, h: 28, minH: 20, minW: 6 },
  { i: 'riskCharts', x: 18, y: 0, w: 6, h: 14, minH: 10, minW: 4 },
  { i: 'topRiskSuppliers', x: 18, y: 28, w: 6, h: 14, minH: 10, minW: 4 },
  
  // 第二行: 库存健康(左) + 客户订单趋势(中) + 生产交付(右)
  { i: 'inventoryHealth', x: 0, y: 28, w: 8, h: 22, minH: 16, minW: 6 },
  { i: 'customerOrderTrend', x: 8, y: 28, w: 8, h: 22, minH: 16, minW: 4 },
  { i: 'productionTracking', x: 18, y: 36, w: 8, h: 22, minH: 16, minW: 8 },
  
  // 第四行: 销售订单概览(全宽)
  { i: 'salesOverview', x: 0, y: 50, w: 24, h: 18, minH: 14, minW: 12 },
];

const ROW_HEIGHT = 8; // px per grid row unit
const GRID_MARGIN = [12, 12];

// ─── 内联 Widget 容器（支持拖拽手柄 + 全屏） ───────────────────────────────
function Widget({ title, subtitle, children, headerRight, fullscreenContent, fullscreenNoPadding }) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const fullscreenProps = { isFullscreen };

  // 获取全屏内容：支持函数形式或 React 元素形式
  const getFullscreenContent = () => {
    if (!fullscreenContent) return children;
    if (typeof fullscreenContent === 'function') {
      return fullscreenContent(fullscreenProps);
    }
    return fullscreenContent;
  };

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
        {getFullscreenContent()}
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
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8, padding: '6px 8px', minHeight: 0 }}>
        {children}
      </div>
    </div>
  );
}

export default function AlertDashboard() {
  const [lastRefresh, setLastRefresh] = useState(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
  const [layout, setLayout] = useState(INITIAL_LAYOUT);
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(1280);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 供应链运营KPI hooks
  const { data: poExecutionRate, loading: poExecutionRateLoading } = usePOExecutionRate();
  const { data: inventoryHealthRate, loading: inventoryHealthRateLoading } = useInventoryHealthRate();
  const { data: woOnTimeDeliveryRate, loading: woOnTimeDeliveryRateLoading } = useWOOnTimeDeliveryRate();
  const { data: monthlyCustomerOrderAmount, loading: monthlyCustomerOrderAmountLoading } = useMonthlyCustomerOrderAmount();
  const { data: activeRiskCount, loading: activeRiskCountLoading } = useActiveRiskCount();
  const { data: highRiskSupplierCount, loading: highRiskSupplierCountLoading } = useHighRiskSupplierCount();

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



  // 刷新所有页面数据
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // 刷新所有KPI数据
      await Promise.all([
        poExecutionRate?.refetch?.(),
        inventoryHealthRate?.refetch?.(),
        woOnTimeDeliveryRate?.refetch?.(),
        monthlyCustomerOrderAmount?.refetch?.(),
        activeRiskCount?.refetch?.(),
        highRiskSupplierCount?.refetch?.(),
      ]);
    } finally {
      setIsRefreshing(false);
      setLastRefresh(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }
  }, [poExecutionRate, inventoryHealthRate, woOnTimeDeliveryRate, monthlyCustomerOrderAmount, activeRiskCount, highRiskSupplierCount]);

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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px',
            padding: '8px 16px', borderRadius: '6px',
            fontSize: '13px', fontWeight: 500,
            background: 'rgba(59,130,246,0.15)', color: '#60a5fa',
            border: '1px solid rgba(59,130,246,0.3)' }}>
            <LayoutDashboard size={14} />
            供应链运营监控看板
          </div>
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
            background: 'transparent', border: 'none', transition: 'all 0.2s',
            animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }}
            onClick={handleRefresh}
            onMouseOver={e => e.currentTarget.style.color = '#e2e8f0'}
            onMouseOut={e => e.currentTarget.style.color = '#94a3b8'}
            title="刷新数据"
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
      <main style={{ flex: 1, overflow: 'auto', width: '100%', display: 'flex', flexDirection: 'column', paddingTop: '14px' }}>

        {/* ==================== 供应链运营监控看板 ==================== */}
        <div ref={containerRef} style={{ width: '100%', flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* ── KPI 卡片行：独立于 GridLayout，宽度与 GridLayout 一致 ── */}
            <div style={{ padding: '0px 0 12px 0' }}>
              <KpiWidget>
                <KpiCard title="采购订单执行率" value={poExecutionRate?.val ?? 0} format="percent" icon={<Truck size={16} />} color="#3b82f6" delay={0} loading={poExecutionRateLoading} />
                <KpiCard title="库存健康度" value={inventoryHealthRate?.val ?? 0} format="percent" icon={<Package size={16} />} color="#10b981" delay={100} loading={inventoryHealthRateLoading} />
                <KpiCard title="工单准时交付率" value={woOnTimeDeliveryRate?.val ?? 0} format="percent" icon={<Factory size={16} />} color="#f59e0b" delay={200} loading={woOnTimeDeliveryRateLoading} />
                <KpiCard title="活跃风险事件" value={activeRiskCount?.val ?? 0} unit="个" format="integer" icon={<AlertTriangle size={16} />} color="#ef4444" delay={300} loading={activeRiskCountLoading} />
                <KpiCard title="本月订单金额" value={monthlyCustomerOrderAmount?.val ?? 0} unit="元" format="currency" icon={<ShoppingCart size={16} />} color="#8b5cf6" delay={400} loading={monthlyCustomerOrderAmountLoading} />
                <KpiCard title="高风险供应商" value={highRiskSupplierCount?.val ?? 0} unit="个" format="integer" icon={<TrendingUp size={16} />} color="#f97316" delay={500} loading={highRiskSupplierCountLoading} />
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
              {/* ── 外部供应链风险列表 ── */}
              <div key="riskList">
                <Widget title="外部供应链风险" subtitle="实时风险监控">
                  <RiskList />
                </Widget>
              </div>

              {/* ── 采购执行监控 ── */}
              <div key="purchaseMonitoring">
                <Widget title="采购执行监控" subtitle="延迟订单与供应商表现">
                  <PurchaseMonitoring />
                </Widget>
              </div>

              {/* ── 风险统计分析 ── */}
              <div key="riskCharts">
                <Widget title="风险统计分析" subtitle="等级分布与类别统计">
                  <RiskCharts />
                </Widget>
              </div>

              {/* ── 库存健康监控 ── */}
              <div key="inventoryHealth">
                <Widget title="库存健康监控" subtitle="低库存预警">
                  <InventoryHealth />
                </Widget>
              </div>

              {/* ── 生产交付跟踪 ── */}
              <div key="productionTracking">
                <Widget title="生产交付跟踪" subtitle="延期工单监控">
                  <ProductionTracking />
                </Widget>
              </div>

              {/* ── 受影响供应商TOP5 ── */}
              <div key="topRiskSuppliers">
                <Widget title="受影响供应商TOP5" subtitle="风险关联分析">
                  <RiskCharts />
                </Widget>
              </div>

              {/* ── 客户订单交付趋势 ── */}
              <div key="customerOrderTrend">
                <Widget title="客户订单交付趋势" subtitle="近30天状态分布">
                  <CustomerOrderTrend />
                </Widget>
              </div>

              {/* ── 销售订单概览 ── */}
              <div key="salesOverview">
                <Widget title="销售订单概览" subtitle="即将到期订单">
                  <SalesOverview />
                </Widget>
              </div>
            </GridLayout>
        </div>
      </main>
    </div>
  );
}