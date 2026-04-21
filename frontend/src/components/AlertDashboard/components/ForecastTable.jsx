// 供应链控制塔 - 需求预测表组件
// 支持：① 产品筛选 ② 下钻（点击产品查看月度明细+采购建议）
import { useState, useMemo } from "react";
import { ChevronLeft, Search, TrendingUp, TrendingDown, Minus } from "lucide-react";

export default function ForecastTable({ maxHeight = 260, forecastResult = { data: [], months: [] }, loading = false, drillProduct: externalDrillProduct, onDrillProductChange }) {
  const [internalDrillProduct, setInternalDrillProduct] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [sortField, setSortField] = useState('');
  const [sortAsc, setSortAsc] = useState(true);

  // 外部传入的 drillProduct 优先，否则使用内部状态
  const drillProduct = externalDrillProduct !== undefined ? externalDrillProduct : internalDrillProduct;
  const setDrillProduct = (product) => {
    if (onDrillProductChange !== undefined) {
      onDrillProductChange(product);
    } else {
      setInternalDrillProduct(product);
    }
  };

  const forecastData = forecastResult?.data || [];
  const forecastMonths = forecastResult?.months || [];

  // 下钻明细：每个产品的月度明细（含采购建议）
  const getDrillDetails = (row) => { return forecastMonths.map((m, i) => { const demand = row.months[m] || 0;
      const stock = Math.round(demand * (0.3 + Math.random() * 0.4));
      const inTransit = Math.round(demand * (0.1 + Math.random() * 0.2));
      const gap = demand - stock - inTransit;
      let suggestion = '';
      if (gap > 0) suggestion = `建议采购 ${gap.toLocaleString()} 件`;
      else if (gap > -demand * 0.1) suggestion = '库存充足';
      else suggestion = `库存过剩 ${Math.abs(gap).toLocaleString()} 件`;
      return { month: m, demand, stock, inTransit, gap, suggestion }; }); };

  const filteredData = useMemo(() => { let data = forecastData;
    if (searchText) { data = data.filter(d =>
        d.productName.includes(searchText) || d.productCode.includes(searchText)
      ); }
    if (sortField) { data = [...data].sort((a, b) => { const va = a.months[sortField] || 0;
        const vb = b.months[sortField] || 0;
        return sortAsc ? va - vb : vb - va; }); }
    return data; }, [searchText, sortField, sortAsc, forecastData]);

  const handleSort = (field) => { if (sortField === field) setSortAsc(v => !v);
    else { setSortField(field); setSortAsc(false); } };

  const drillDetails = drillProduct ? getDrillDetails(drillProduct) : [];

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
      padding: '0 12px 8px 12px' }}>
      {/* 控制栏 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px',
        padding: '6px 0', flexShrink: 0 }}>
        {drillProduct ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
            <button
              onClick={() => setDrillProduct(null)}
              style={{ display: 'flex', alignItems: 'center', gap: '4px',
                fontSize: '12px', color: '#60a5fa', cursor: 'pointer',
                background: 'transparent', border: 'none', transition: 'color 0.2s' }}
              onMouseOver={e => e.currentTarget.style.color = '#93c5fd'}
              onMouseOut={e => e.currentTarget.style.color = '#60a5fa'}
            >
              <ChevronLeft size={12} /> 返回列表
            </button>
            <span style={{ fontSize: '12px', color: '#64748b' }}>/</span>
            <span style={{ fontSize: '12px', color: '#cbd5e1', fontWeight: 500 }}>{drillProduct.productName}</span>
            <span style={{ fontSize: '12px', color: '#64748b' }}>({drillProduct.productCode})</span>
          </div>
        ) : (
          <>
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1,
                borderRadius: '8px', padding: '6px 10px',
                background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <Search size={11} style={{ color: '#64748b', flexShrink: 0 }} />
              <input
                type="text"
                placeholder="筛选产品..."
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                style={{ flex: 1, background: 'transparent', fontSize: '12px',
                  color: '#e2e8f0', outline: 'none', border: 'none' }}
              />
            </div>
            <span style={{ fontSize: '12px', color: '#64748b', flexShrink: 0 }}>单位：件 · 点击产品下钻</span>
          </>
        )}
      </div>

      {/* 表格区 */}
      <div style={{ flex: 1, overflow: 'auto', maxHeight,
        scrollbarWidth: 'thin', scrollbarColor: 'rgba(59,130,246,0.3) transparent' }}>
        {drillProduct ? (
          // 下钻视图：月度明细
          <table style={{ width: '100%', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.2)', background: 'rgba(59,130,246,0.05)' }}>
                {['月份', '需求量', '在库量', '在途量', '缺口', '采购建议'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '6px 10px',
                    color: '#94a3b8', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {drillDetails.map((row, idx) => (
                <tr
                  key={row.month}
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.04)',
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}
                >
                  <td style={{ padding: '6px 10px', color: '#cbd5e1', fontWeight: 500 }}>
                    {row.month.slice(5)}月
                  </td>
                  <td style={{ padding: '6px 10px', color: '#e2e8f0', fontFamily: 'monospace' }}>
                    {row.demand.toLocaleString()}
                  </td>
                  <td style={{ padding: '6px 10px', color: '#e2e8f0', fontFamily: 'monospace' }}>
                    {row.stock.toLocaleString()}
                  </td>
                  <td style={{ padding: '6px 10px', color: '#e2e8f0', fontFamily: 'monospace' }}>
                    {row.inTransit.toLocaleString()}
                  </td>
                  <td style={{ padding: '6px 10px' }}>
                    <span
                      style={{ fontFamily: 'monospace', fontWeight: 500,
                        color: row.gap > 0 ? '#ef4444' : row.gap < -row.demand * 0.1 ? '#f59e0b' : '#22c55e' }}
                    >
                      {row.gap > 0 ? `+${row.gap.toLocaleString()}` : row.gap.toLocaleString()}
                    </span>
                  </td>
                  <td style={{ padding: '6px 10px' }}>
                    <span
                      style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '9999px',
                        ...(row.gap > 0
                          ? { background: 'rgba(239,68,68,0.15)', color: '#f87171' }
                          : row.gap < -row.demand * 0.1
                          ? { background: 'rgba(245,158,11,0.15)', color: '#fbbf24' }
                          : { background: 'rgba(34,197,94,0.15)', color: '#4ade80' }) }}
                    >
                      {row.suggestion}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          // 总览视图
          <table style={{ width: '100%', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.2)', background: 'rgba(59,130,246,0.05)' }}>
                <th style={{ textAlign: 'left', padding: '6px 10px', color: '#94a3b8',
                  fontWeight: 500, position: 'sticky', left: 0,
                  background: 'rgba(22,35,64,0.98)', minWidth: '150px' }}>产品</th>
                {forecastMonths.map(m => (
                  <th
                    key={m}
                    style={{ textAlign: 'right', padding: '6px 6px', color: '#94a3b8',
                      fontWeight: 500, whiteSpace: 'nowrap', cursor: 'pointer',
                      minWidth: '72px', transition: 'color 0.2s' }}
                    onMouseOver={e => e.currentTarget.style.color = '#e2e8f0'}
                    onMouseOut={e => e.currentTarget.style.color = '#94a3b8'}
                    onClick={() => handleSort(m)}
                  >
                    {m.slice(5)}月
                    {sortField === m && (
                      <span style={{ marginLeft: '2px' }}>{sortAsc ? '↑' : '↓'}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredData.map((row, idx) => (
                <tr
                  key={row.productCode}
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.04)',
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                    cursor: 'pointer', transition: 'background 0.2s' }}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(59,130,246,0.08)'}
                  onMouseOut={e => e.currentTarget.style.background = idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)'}
                  onClick={() => setDrillProduct(row)}
                >
                  <td style={{ padding: '6px 10px', position: 'sticky', left: 0,
                    background: idx % 2 === 0 ? '#162340' : 'rgba(22,35,64,0.95)' }}>
                    <p style={{ color: '#e2e8f0', fontWeight: 500, fontSize: '13px',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      maxWidth: '145px', margin: 0 }}>{row.productName}</p>
                    <p style={{ color: '#64748b', fontSize: '10px', margin: '2px 0 0 0' }}>{row.productCode}</p>
                  </td>
                  {forecastMonths.map(m => { const val = row.months[m] || 0;
                    const maxVal = Math.max(...forecastMonths.map(mm => row.months[mm] || 0));
                    const pct = maxVal > 0 ? (val / maxVal) * 100 : 0;
                    // 环比趋势
                    const mIdx = forecastMonths.indexOf(m);
                    const prevVal = mIdx > 0 ? (row.months[forecastMonths[mIdx - 1]] || 0) : val;
                    const trend = val > prevVal * 1.05 ? 'up' : val < prevVal * 0.95 ? 'down' : 'flat';
                    return (
                      <td key={m} style={{ padding: '6px 6px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', flexDirection: 'column',
                          alignItems: 'flex-end', gap: '4px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            {trend === 'up' && <TrendingUp size={9} style={{ color: '#4ade80' }} />}
                            {trend === 'down' && <TrendingDown size={9} style={{ color: '#f87171' }} />}
                            {trend === 'flat' && <Minus size={9} style={{ color: '#64748b' }} />}
                            <span style={{ color: '#e2e8f0', fontFamily: 'monospace' }}>
                              {(val / 1000).toFixed(1)}K
                            </span>
                          </div>
                          <div style={{ width: '100%', height: '4px', borderRadius: '9999px',
                            overflow: 'hidden', background: 'rgba(59,130,246,0.1)' }}>
                            <div style={{ height: '100%', borderRadius: '9999px',
                              width: `${pct}%`,
                              background: 'linear-gradient(90deg, #3b82f6, #06b6d4)' }} />
                          </div>
                        </div>
                      </td>
                    ); })}
                </tr>
              ))}
              {filteredData.length === 0 && (
                <tr>
                  <td colSpan={forecastMonths.length + 1} style={{ padding: '32px',
                    textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
                    无匹配产品
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  ); }
