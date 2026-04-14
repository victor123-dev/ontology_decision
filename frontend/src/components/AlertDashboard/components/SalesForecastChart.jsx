// 供应链控制塔 - 销售预测 vs 实际订单 vs 采购量图表
// 支持：① 数据筛选（产品/时间范围）② 下钻（点击月份查看明细）
import { useState, useMemo } from "react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Cell } from "recharts";
import { ChevronLeft, X } from "lucide-react";
import { chartData } from "../lib/data";

// 下钻明细数据（模拟按产品拆解）
const drillDownData = { '2025-01': [
    { product: 'MOSFET晶体管', forecast: 2800, order: 2650, purchase: 3100 },
    { product: 'MCU微控制器', forecast: 1900, order: 1820, purchase: 2200 },
    { product: 'NAND Flash', forecast: 1500, order: 1450, purchase: 1800 },
    { product: 'LPDDR4内存', forecast: 1200, order: 1150, purchase: 1400 },
    { product: '电源管理IC', forecast: 800, order: 780, purchase: 600 },
  ],
  '2025-02': [
    { product: 'MOSFET晶体管', forecast: 2600, order: 2400, purchase: 2900 },
    { product: 'MCU微控制器', forecast: 1800, order: 1700, purchase: 2000 },
    { product: 'NAND Flash', forecast: 1400, order: 1320, purchase: 1600 },
    { product: 'LPDDR4内存', forecast: 1100, order: 1050, purchase: 1300 },
    { product: '电源管理IC', forecast: 700, order: 730, purchase: 600 },
  ] };
// 补充其余月份
['2025-03','2025-04','2025-05','2025-06','2025-07','2025-08','2025-09','2025-10','2025-11','2025-12'].forEach((m, i) => { const base = 9000 + i * 600;
  drillDownData[m] = [
    { product: 'MOSFET晶体管', forecast: Math.round(base * 0.34), order: Math.round(base * 0.33), purchase: Math.round(base * 0.37) },
    { product: 'MCU微控制器', forecast: Math.round(base * 0.22), order: Math.round(base * 0.21), purchase: Math.round(base * 0.25) },
    { product: 'NAND Flash', forecast: Math.round(base * 0.18), order: Math.round(base * 0.17), purchase: Math.round(base * 0.20) },
    { product: 'LPDDR4内存', forecast: Math.round(base * 0.14), order: Math.round(base * 0.13), purchase: Math.round(base * 0.15) },
    { product: '电源管理IC', forecast: Math.round(base * 0.12), order: Math.round(base * 0.12), purchase: Math.round(base * 0.03) },
  ]; });

const SERIES = [
  { key: 'salesForecast', label: '销售预测', color: '#3b82f6' },
  { key: 'salesOrder', label: '实际订单', color: '#22c55e' },
  { key: 'purchaseQty', label: '采购量', color: '#f59e0b' },
];

const CustomTooltip = ({ active, payload, label }) => { if (!active || !payload?.length) return null;
  return (
    <div style={{ padding: '8px 12px', borderRadius: '8px', fontSize: '12px',
      background: '#0f1d35', border: '1px solid rgba(59,130,246,0.3)' }}>
      <p style={{ color: '#94a3b8', marginBottom: '6px', fontWeight: 500 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ marginBottom: '2px', color: p.color }}>
          {p.name}: <span style={{ fontFamily: 'monospace' }}>{p.value?.toLocaleString()}</span>
        </p>
      ))}
    </div>
  ); };

const DrillTooltip = ({ active, payload, label }) => { if (!active || !payload?.length) return null;
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
  ); };

export default function SalesForecastChart({ height = 220 }) { const [activeSeries, setActiveSeries] = useState(new Set(['salesForecast', 'salesOrder', 'purchaseQty']));
  const [timeRange, setTimeRange] = useState('all');
  const [drillMonth, setDrillMonth] = useState(null);

  const filteredData = useMemo(() => { if (timeRange === 'H1') return chartData.filter(d => parseInt(d.month.slice(5)) <= 6);
    if (timeRange === 'H2') return chartData.filter(d => parseInt(d.month.slice(5)) >= 7);
    return chartData; }, [timeRange]);

  const toggleSeries = (key) => { setActiveSeries(prev => { const next = new Set(prev);
      if (next.has(key)) { if (next.size > 1) next.delete(key); }
      else next.add(key);
      return next; }); };

  const drillData = drillMonth ? drillDownData[drillMonth] || [] : [];

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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0' }}>
            {(['all', 'H1', 'H2']).map((r, idx) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                style={{ fontSize: '12px', padding: '4px 12px',
                  transition: 'all 0.2s', cursor: 'pointer',
                  background: 'transparent',
                  border: 'none',
                  borderRadius: idx === 0 ? '4px 0 0 4px' : idx === 2 ? '0 4px 4px 0' : '0',
                  ...(timeRange === r
                    ? { background: 'rgba(59,130,246,0.2)', color: '#60a5fa',
                        border: '1px solid rgba(59,130,246,0.4)' }
                    : { color: '#94a3b8' }) }}
                onMouseOver={e => {
                  if (timeRange !== r) {
                    e.currentTarget.style.color = '#e2e8f0';
                  }
                }}
                onMouseOut={e => {
                  if (timeRange !== r) {
                    e.currentTarget.style.color = '#94a3b8';
                  }
                }}
              >
                {r === 'all' ? '全年' : r === 'H1' ? '上半年' : '下半年'}
              </button>
            ))}
          </div>
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
          点击柱/线可下钻查看月度产品明细
        </p>
      )}

      {/* 图表区 */}
      <div style={{ flex: 1, minHeight: 0, height }}>
        {drillMonth ? (
          // 下钻柱状图
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={drillData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="product" tick={{ fill: '#64748b', fontSize: 9 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip content={<DrillTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
              <Bar dataKey="forecast" name="销售预测" fill="#3b82f6" radius={[3,3,0,0]} />
              <Bar dataKey="order" name="实际订单" fill="#22c55e" radius={[3,3,0,0]} />
              <Bar dataKey="purchase" name="采购量" fill="#f59e0b" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          // 总览面积图
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={filteredData}
              margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
              onClick={(data) => { if (data?.activeLabel) setDrillMonth(data.activeLabel); }}
              style={{ cursor: 'pointer' }}
            >
              <defs>
                {SERIES.map(s => (
                  <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={s.color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={s.color} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip content={<CustomTooltip />} />
              {SERIES.filter(s => activeSeries.has(s.key)).map(s => (
                <Area
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.label}
                  stroke={s.color}
                  fill={`url(#grad-${s.key})`}
                  strokeWidth={2}
                  dot={{ r: 3, fill: s.color, strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  ); }
