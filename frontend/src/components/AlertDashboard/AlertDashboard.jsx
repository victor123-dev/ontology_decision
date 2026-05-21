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
import MetricTree from "./components/MetricTree";

// 供应链运营监控组件
import RiskList from './components/RiskList';
import PurchaseMonitoring from './components/PurchaseMonitoring';
import InventoryHealth from './components/InventoryHealth';
import ProductionTracking from './components/ProductionTracking';
import SalesOverview from './components/SalesOverview';
import RiskCharts from './components/RiskCharts';
import CustomerOrderTrend from './components/CustomerOrderTrend';
import ProductionGantt from './components/ProductionGantt';

// 运营和风险数据hooks
import { usePOExecutionRate, useInventoryHealthRate, useWOOnTimeDeliveryRate, useMonthlyCustomerOrderAmount, useDelayedPurchaseOrders, useSupplierPerformance, useLowInventoryAlerts, useDelayedWorkOrders, useUpcomingCustomerOrders, useCustomerOrderTrend } from './hooks/useOperationData';
import { useActiveRiskCount, useHighRiskSupplierCount, useActiveRisks, useRiskStatistics, useTopAffectedSuppliers } from './hooks/useRiskData';
import { useMetricTree } from './hooks/useMetricTree';
import { getRiskTextColor, getStatusColor, getLogisticsStatusColor } from "./lib/data";
import { useWindowSize } from "./hooks/useWindowSize";

// rowHeight=8px，cols=24
const INITIAL_LAYOUT = [
  { i: 'metricTree', x: 0, y: 0, w: 12, h: 28, minH: 24, minW: 10 },
  { i: 'purchaseMonitoring', x: 12, y: 0, w: 12, h: 28, minH: 20, minW: 8 },

  { i: 'riskList', x: 0, y: 28, w: 10, h: 28, minH: 20, minW: 8 },
  { i: 'riskCharts', x: 10, y: 28, w: 6, h: 28, minH: 20, minW: 4 },
  { i: 'inventoryHealth', x: 16, y: 28, w: 8, h: 28, minH: 16, minW: 6 },

  { i: 'customerOrderTrend', x: 0, y: 56, w: 8, h: 22, minH: 16, minW: 4 },
  { i: 'productionTracking', x: 8, y: 56, w: 8, h: 22, minH: 16, minW: 8 },
  { i: 'salesOverview', x: 16, y: 56, w: 8, h: 22, minH: 14, minW: 8 },

  { i: 'productionGantt', x: 0, y: 78, w: 24, h: 24, minH: 18, minW: 12 },
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
        background: '#eef6fc',
        display: 'flex', flexDirection: 'column' }}
    >
      <div
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 24px', flexShrink: 0,
          borderBottom: '1px solid rgba(59,130,246,0.2)',
          background: 'rgba(255,255,255,0.98)' }}
      >
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: '#1a3a5c', margin: 0 }}>{title}</h2>
          {subtitle && <p style={{ fontSize: 11, color: '#7a9ab8', margin: '2px 0 0' }}>{subtitle}</p>}
        </div>
        <button
          onClick={() => setIsFullscreen(false)}
          style={{ display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 8,
            fontSize: 13, color: '#4a6fa5', cursor: 'pointer',
            background: 'rgba(24,144,255,0.06)',
            border: '1px solid rgba(24,144,255,0.15)' }}
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
        background: 'linear-gradient(135deg, #ffffff 0%, #f5fbff 100%)', borderRadius: '8px',
        border: '1px solid rgba(24,144,255,0.15)',
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        overflow: 'hidden'
      }}>
        {/* 标题栏 - 拖拽手柄 */}
        <div
          className="widget-drag-handle"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '8px 16px', flexShrink: 0, userSelect: 'none',
            borderBottom: '1px solid rgba(24,144,255,0.15)', cursor: 'move',
            background: 'rgba(24,144,255,0.04)' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
            <GripHorizontal size={13} style={{ color: '#7a9ab8', flexShrink: 0 }} />
            <div style={{ minWidth: 0 }}>
              <span style={{ fontSize: '14px', fontWeight: 600, color: '#1a3a5c',
                display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</span>
              {subtitle && <span style={{ fontSize: '10px', color: '#7a9ab8' }}>{subtitle}</span>}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            {headerRight}
            <button
              onMouseDown={e => e.stopPropagation()}
              onClick={e => { e.stopPropagation(); setIsFullscreen(true); }}
              style={{ width: '24px', height: '24px', display: 'flex', alignItems: 'center',
                justifyContent: 'center', borderRadius: '4px', color: '#7a9ab8', cursor: 'pointer',
                background: 'transparent', border: 'none', transition: 'all 0.2s' }}
              onMouseOver={e => {
                e.currentTarget.style.color = '#4a6fa5';
                e.currentTarget.style.background = 'rgba(24,144,255,0.1)';
              }}
              onMouseOut={e => {
                e.currentTarget.style.color = '#7a9ab8';
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
    <div style={{ height: 105, display: 'flex', flexDirection: 'column', overflow: 'hidden',
      background: 'linear-gradient(135deg, #ffffff 0%, #f5fbff 100%)', borderRadius: '8px',
      border: '1px solid rgba(24,144,255,0.15)',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
      {/* 拖拽手柄条 */}
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '8px',
          padding: '0 12px', flexShrink: 0, userSelect: 'none',
          cursor: 'move', borderBottom: '1px solid rgba(24,144,255,0.15)', height: 20, minHeight: 20,
          background: 'rgba(24,144,255,0.04)' }}
      >
        <GripHorizontal size={11} style={{ color: '#7a9ab8' }} />
        <span style={{ fontSize: '10px', color: '#7a9ab8',
          letterSpacing: '0.2em', textTransform: 'uppercase' }}>KPI 指标</span>
      </div>
      {/* KPI 卡片网格 */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8, padding: '6px 8px', minHeight: 0 }}>
        {children}
      </div>
    </div>
  );
}

export default function AlertDashboard({ hideHeader = false }) {
  const [lastRefresh, setLastRefresh] = useState(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
  const [layout, setLayout] = useState(INITIAL_LAYOUT);
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(1280);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);  // 刷新触发器

  // 指标树数据 hook
  const { data: metricTreeData, loading: metricTreeLoading, refetch: refetchMetricTree } = useMetricTree();
  const { data: poExecutionRate, loading: poExecutionRateLoading, refetch: refetchPOExecutionRate } = usePOExecutionRate();
  const { data: inventoryHealthRate, loading: inventoryHealthRateLoading, refetch: refetchInventoryHealthRate } = useInventoryHealthRate();
  const { data: woOnTimeDeliveryRate, loading: woOnTimeDeliveryRateLoading, refetch: refetchWOOnTimeDeliveryRate } = useWOOnTimeDeliveryRate();
  const { data: monthlyCustomerOrderAmount, loading: monthlyCustomerOrderAmountLoading, refetch: refetchMonthlyCustomerOrderAmount } = useMonthlyCustomerOrderAmount();
  const { data: activeRiskCount, loading: activeRiskCountLoading, refetch: refetchActiveRiskCount } = useActiveRiskCount();
  const { data: highRiskSupplierCount, loading: highRiskSupplierCountLoading, refetch: refetchHighRiskSupplierCount } = useHighRiskSupplierCount();

  // 业务组件hooks
  const { refetch: refetchDelayedPurchaseOrders } = useDelayedPurchaseOrders();
  const { refetch: refetchSupplierPerformance } = useSupplierPerformance();
  const { refetch: refetchLowInventoryAlerts } = useLowInventoryAlerts();
  const { refetch: refetchDelayedWorkOrders } = useDelayedWorkOrders();
  const { refetch: refetchUpcomingCustomerOrders } = useUpcomingCustomerOrders();
  const { refetch: refetchCustomerOrderTrend } = useCustomerOrderTrend();
  const { refetch: refetchActiveRisks } = useActiveRisks();
  const { refetch: refetchRiskStatistics } = useRiskStatistics();
  const { refetch: refetchTopAffectedSuppliers } = useTopAffectedSuppliers();

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
    // 立即触发业务组件刷新,不等待KPI完成
    setRefreshTrigger(prev => prev + 1);
    
    try {
      // 并发刷新所有KPI数据 + 业务组件数据 + 指标树
      await Promise.all([
        // KPI数据
        refetchPOExecutionRate?.(),
        refetchInventoryHealthRate?.(),
        refetchWOOnTimeDeliveryRate?.(),
        refetchMonthlyCustomerOrderAmount?.(),
        refetchActiveRiskCount?.(),
        refetchHighRiskSupplierCount?.(),
        // 指标树
        refetchMetricTree?.(),
        // 业务组件数据
        refetchDelayedPurchaseOrders?.(),
        refetchSupplierPerformance?.(),
        refetchLowInventoryAlerts?.(),
        refetchDelayedWorkOrders?.(),
        refetchUpcomingCustomerOrders?.(),
        refetchCustomerOrderTrend?.(),
        refetchActiveRisks?.(),
        refetchRiskStatistics?.(),
        refetchTopAffectedSuppliers?.(),
      ]);
    } finally {
      setIsRefreshing(false);
      setLastRefresh(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }
  }, [
    refetchPOExecutionRate, refetchInventoryHealthRate, refetchWOOnTimeDeliveryRate, 
    refetchMonthlyCustomerOrderAmount, refetchActiveRiskCount, refetchHighRiskSupplierCount,
    refetchMetricTree,
    refetchDelayedPurchaseOrders, refetchSupplierPerformance, refetchLowInventoryAlerts,
    refetchDelayedWorkOrders, refetchUpcomingCustomerOrders, refetchCustomerOrderTrend,
    refetchActiveRisks, refetchRiskStatistics, refetchTopAffectedSuppliers
  ]);

  // 根据 layout 中的 h 计算实际像素高度
  const getItemPx = useCallback((id) => {
    const item = layout.find(l => l.i === id);
    return item ? item.h * ROW_HEIGHT + (item.h - 1) * GRID_MARGIN[1] : 300;
  }, [layout]);

  // 使用容器宽度，不额外减去padding（padding已在容器上设置）
  const gridWidth = Math.max(containerWidth, 800);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column',
      background: 'linear-gradient(180deg, #e8f4fc 0%, #d6ebf7 50%, #c8e3f3 100%)', fontFamily: "'Noto Sans SC', sans-serif", overflow: 'hidden', width: '100%' }}>
      {/* 顶部导航 */}
      {!hideHeader && (
      <header
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          height: '64px',
          padding: '0 24px',
          background: 'linear-gradient(90deg, #ffffff 0%, #f0f7ff 100%)',
          borderBottom: '1px solid rgba(24,144,255,0.2)',
          boxShadow: '0 2px 16px rgba(0,0,0,0.08)',
          flexShrink: 0 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '0 0 auto' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)' }}>
            <Factory size={18} style={{ color: '#fff' }} />
          </div>
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: 'bold', color: '#1a3a5c',
              lineHeight: '1.2', letterSpacing: '-0.02em', margin: 0 }}>供应链控制塔</h1>
            <p style={{ fontSize: '10px', color: '#7a9ab8', margin: '2px 0 0' }}>
              Supply Chain Control Tower · 半导体制造</p>
          </div>
        </div>

        <nav style={{ display: 'flex', alignItems: 'center', gap: '4px', flex: '0 1 auto', justifyContent: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px',
            padding: '8px 16px', borderRadius: '6px',
            fontSize: '13px', fontWeight: 500,
            background: 'rgba(24,144,255,0.12)', color: '#1890ff',
            border: '1px solid rgba(24,144,255,0.3)' }}>
            <LayoutDashboard size={14} />
            供应链运营监控看板
          </div>
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '0 0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px',
            fontSize: '12px', color: '#7a9ab8' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%',
              background: '#52c41a', animation: 'pulse 2s ease-out infinite' }} />
            <span>实时更新 {lastRefresh}</span>
          </div>
          <button style={{ width: '32px', height: '32px', borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#7a9ab8', cursor: 'pointer',
            background: 'transparent', border: 'none', transition: 'all 0.2s',
            animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }}
            onClick={handleRefresh}
            onMouseOver={e => e.currentTarget.style.color = '#4a6fa5'}
            onMouseOut={e => e.currentTarget.style.color = '#7a9ab8'}
            title="刷新数据"
          >
            <RefreshCw size={14} />
          </button>
          <button style={{ width: '32px', height: '32px', borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#7a9ab8', cursor: 'pointer',
            background: 'transparent', border: 'none', transition: 'all 0.2s' }}
            onMouseOver={e => e.currentTarget.style.color = '#4a6fa5'}
            onMouseOut={e => e.currentTarget.style.color = '#7a9ab8'}
          >
            <Settings size={14} />
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px', borderRadius: '8px',
            background: 'rgba(24,144,255,0.04)', border: '1px solid rgba(24,144,255,0.12)' }}>
            <div style={{ width: '24px', height: '24px', borderRadius: '50%',
              background: '#1890ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <User size={12} style={{ color: '#fff' }} />
            </div>
            <span style={{ fontSize: '12px', color: '#4a6fa5' }}>供应链管理员</span>
            <ChevronDown size={12} style={{ color: '#7a9ab8' }} />
          </div>
        </div>
      </header>
      )}

      {/* 主内容区 */}
      <main style={{ flex: 1, overflow: 'auto', width: '100%', display: 'flex', flexDirection: 'column', paddingTop: '14px' }}>

        {/* ==================== 供应链运营监控看板 ==================== */}
        <div ref={containerRef} style={{ width: '100%', flex: 1, display: 'flex', flexDirection: 'column' }}>
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
              <div key="metricTree">
                <Widget
                  title="订单交付指标树"
                  headerRight={(
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#16a34a', fontSize: 10, fontWeight: 700 }}>
                        <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#16a34a' }} />正常
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#dc2626', fontSize: 10, fontWeight: 700 }}>
                        <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#dc2626' }} />异常
                      </span>
                    </div>
                  )}
                >
                  <MetricTree
                    metricsData={metricTreeData || {}}
                    loading={metricTreeLoading}
                  />
                </Widget>
              </div>

              {/* ── 外部供应链风险列表 ── */}
              <div key="riskList">
                <Widget title="外部供应链风险">
                  <RiskList refreshTrigger={refreshTrigger} />
                </Widget>
              </div>

              {/* ── 采购执行监控 ── */}
              <div key="purchaseMonitoring">
                <Widget title="采购执行监控">
                  <PurchaseMonitoring refreshTrigger={refreshTrigger} />
                </Widget>
              </div>

              {/* ── 风险统计分析 ── */}
              <div key="riskCharts">
                <Widget title="风险统计分析">
                  <RiskCharts refreshTrigger={refreshTrigger} />
                </Widget>
              </div>

              {/* ── 库存健康监控 ── */}
              <div key="inventoryHealth">
                <Widget title="库存健康监控">
                  <InventoryHealth refreshTrigger={refreshTrigger} />
                </Widget>
              </div>

              {/* ── 生产交付跟踪 ── */}
              <div key="productionTracking">
                <Widget title="生产交付跟踪">
                  <ProductionTracking refreshTrigger={refreshTrigger} />
                </Widget>
              </div>

              {/* ── 客户订单交付趋势 ── */}
              <div key="customerOrderTrend">
                <Widget title="客户订单交付趋势">
                  <CustomerOrderTrend refreshTrigger={refreshTrigger} />
                </Widget>
              </div>

              {/* ── 生产排产甘特图 ── */}
              <div key="productionGantt">
                <Widget title="生产排产甘特图">
                  <ProductionGantt refreshTrigger={refreshTrigger} />
                </Widget>
              </div>

              {/* ── 销售订单概览 ── */}
              <div key="salesOverview">
                <Widget title="销售订单概览">
                  <SalesOverview refreshTrigger={refreshTrigger} />
                </Widget>
              </div>
            </GridLayout>
        </div>
      </main>
    </div>
  );
}