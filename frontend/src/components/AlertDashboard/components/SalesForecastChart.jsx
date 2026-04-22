// 供应链控制塔 - 销售预测 vs 实际订单图表
// 支持：① 数据筛选（产品/时间范围）② 下钻（点击月份查看明细）
import { useState, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, BarChart, Bar } from "recharts";
import { ChevronLeft } from "lucide-react";

const SERIES = [
  { key: 'salesForecast', label: '销售预测', color: '#3b82f6' },
  { key: 'salesOrder', label: '实际订单', color: '#22c55e' },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ padding: '8px 12px', borderRadius: '8px', fontSize: '12px',
      background: '#0f1d35', border: '1px solid rgba(59,130,246,0.3)' }}>
      <p style={{ color: '#94a3b8', marginBottom: '6px', fontWeight: 500 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ marginBottom: '2px', color: p.color }}>
          {p.name}: <span style={{ fontFamily: 'monospace' }}>
            {p.value !== null && p.value !== undefined ? p.value.toLocaleString() : '-'}
          </span>
        </p>
      ))}
    </div>
  );
};

const DrillTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ padding: '8px 12px', borderRadius: '8px', fontSize: '12px',
      background: '#0f1d35', border: '1px solid rgba(59,130,246,0.3)' }}>
      <p style={{ color: '#94a3b8', marginBottom: '6px', fontWeight: 500 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ marginBottom: '2px', color: p.fill || p.color }}>
          {p.name}: <span style={{ fontFamily: 'monospace' }}>{p.value?.toLocaleString()}</span>
        </p>
      ))}
    </div>
  );
};

// 生成最近12个月的月份列表（备用）
const getLast12Months = () => {
  const months = [];
  const today = new Date();
  for (let i = 11; i >= 0; i--) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
    const year = d.getFullYear();
    const month = d.getMonth() + 1;
    months.push(`${year}-${String(month).padStart(2, '0')}`);
  }
  return months;
};

export default function SalesForecastChart({ height = 220, chartData = [], chartMonths = [], loading = false, drillMonth: externalDrillMonth, onDrillMonthChange }) {
  const [activeSeries, setActiveSeries] = useState(new Set(['salesForecast', 'salesOrder']));
  const [internalDrillMonth, setInternalDrillMonth] = useState(null);

  // 外部传入的 drillMonth 优先，否则使用内部状态
  const drillMonth = externalDrillMonth !== undefined ? externalDrillMonth : internalDrillMonth;
  const setDrillMonth = (month) => {
    if (onDrillMonthChange !== undefined) {
      onDrillMonthChange(month);
    } else {
      setInternalDrillMonth(month);
    }
  };

  // 将按品号+月份的数据转换为按月合并的数据（用于折线图），补全12个月
  const monthlyData = useMemo(() => {
    // 优先使用后端返回的月份列表，否则使用本地计算的
    const monthList = chartMonths.length > 0 ? chartMonths : getLast12Months();
    // 初始化12个月的数据，值都为null（无数据时）
    const monthMap = {};
    monthList.forEach(month => {
      monthMap[month] = { month, salesForecast: null, salesOrder: null };
    });

    // 用chartData填充
    if (chartData && Array.isArray(chartData)) {
      chartData.forEach(item => {
        const month = item.month;
        if (monthMap[month]) {
          // 累加数据，null值时直接赋值（保持null表示无数据）
          if (item.salesForecast !== null && item.salesForecast !== undefined) {
            const currentForecast = monthMap[month].salesForecast;
            monthMap[month].salesForecast = currentForecast === null 
              ? item.salesForecast 
              : currentForecast + item.salesForecast;
          }
          if (item.salesOrder !== null && item.salesOrder !== undefined) {
            const currentOrder = monthMap[month].salesOrder;
            monthMap[month].salesOrder = currentOrder === null 
              ? item.salesOrder 
              : currentOrder + item.salesOrder;
          }
        }
      });
    }

    return Object.values(monthMap);
  }, [chartData, chartMonths]);

  const toggleSeries = (key) => {
    setActiveSeries(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // 下钻明细数据（按品号分组）
  const drillData = useMemo(() => {
    if (!drillMonth || !chartData || !Array.isArray(chartData)) return [];
    return chartData.filter(item => item.month === drillMonth);
  }, [drillMonth, chartData]);

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%',
      padding: '0 16px 12px 16px' }}>
      {/* 控制栏 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 0', flexShrink: 0 }}>
        {/* 下钻面包屑 */}
        {drillMonth ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setDrillMonth(null)}
              style={{ display: 'flex', alignItems: 'center', gap: '4px',
                fontSize: '12px', color: '#60a5fa', cursor: 'pointer',
                background: 'transparent', border: 'none', transition: 'color 0.2s' }}
              onMouseOver={e => e.currentTarget.style.color = '#93c5fd'}
              onMouseOut={e => e.currentTarget.style.color = '#60a5fa'}
            >
              <ChevronLeft size={12} /> 返回总览
            </button>
            <span style={{ fontSize: '12px', color: '#64748b' }}>/</span>
            <span style={{ fontSize: '12px', color: '#cbd5e1', fontWeight: 500 }}>{drillMonth} 月度明细</span>
          </div>
        ) : (
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>总览</span>
        )}

        {/* 系列筛选（仅总览时显示） */}
        {!drillMonth && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {SERIES.map(s => (
              <button
                key={s.key}
                onClick={() => toggleSeries(s.key)}
                style={{ display: 'flex', alignItems: 'center', gap: '6px',
                  fontSize: '12px', padding: '4px 8px', borderRadius: '4px',
                  transition: 'all 0.2s', cursor: 'pointer',
                  ...(activeSeries.has(s.key)
                    ? { background: `${s.color}20`, color: s.color,
                        border: `1px solid ${s.color}50` }
                    : { color: '#475569', border: '1px solid rgba(255,255,255,0.08)',
                        textDecoration: 'line-through' }) }}
              >
                <div style={{ width: '8px', height: '8px', borderRadius: '50%',
                  flexShrink: 0, background: activeSeries.has(s.key) ? s.color : '#475569' }} />
                {s.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 提示文字 */}
      {!drillMonth && (
        <p style={{ fontSize: '10px', color: '#475569', marginBottom: '4px', flexShrink: 0 }}>
          {/*点击折线可下钻查看该月的产品明细*/}
        </p>
      )}

      {/* 图表区 */}
      <div style={{ flex: 1, minHeight: 0, height }}>
        {drillMonth ? (
          // 下钻柱状图（按品号显示明细）
          drillData.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <span style={{ fontSize: '13px', color: '#64748b' }}>该月份暂无明细数据</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={drillData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="product" tick={{ fill: '#64748b', fontSize: 9 }}
                  angle={-45} textAnchor="end" height={60} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                <Tooltip content={<DrillTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
                <Bar dataKey="salesForecast" name="销售预测" fill="#3b82f6" radius={[3,3,0,0]} />
                <Bar dataKey="salesOrder" name="实际订单" fill="#22c55e" radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          )
        ) : (
          // 总览折线图（按月合并数据）
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={monthlyData}
              margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
              onClick={(data) => { if (data?.activeLabel) setDrillMonth(data.activeLabel); }}
              style={{ cursor: 'pointer' }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 10 }}
                tickFormatter={v => v ? v.replace('-', '年') + '月' : ''} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
              {SERIES.filter(s => activeSeries.has(s.key)).map(s => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.label}
                  stroke={s.color}
                  strokeWidth={2}
                  dot={{ r: 3, fill: s.color, strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                  connectNulls={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
