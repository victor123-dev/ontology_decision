// 供应链控制塔 - KPI指标卡片组件
// 深蓝科技风格：数字跳动动画 + 渐变边框 + 趋势指示
import { useEffect, useRef, useState } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

function useCountUp(target, duration = 1500, delay = 0) { const [current, setCurrent] = useState(0);
  const startTime = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => { const timeout = setTimeout(() => { const animate = (timestamp) => { if (!startTime.current) startTime.current = timestamp;
        const elapsed = timestamp - startTime.current;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        setCurrent(target * eased);
        if (progress < 1) { rafRef.current = requestAnimationFrame(animate); } };
      rafRef.current = requestAnimationFrame(animate); }, delay);

    return () => { clearTimeout(timeout);
      if (rafRef.current) cancelAnimationFrame(rafRef.current); }; }, [target, duration, delay]);

  return current; }

export default function KpiCard({ title, value, unit, format = 'number', trend = 'flat', trendValue, icon, color = '#3b82f6', delay = 0, loading = false }) { 
  const animatedValue = useCountUp(value || 0, 1500, delay);

  // 加载状态：显示旋转动画
  if (loading) {
    return (
      <div
        style={{
          background: '#0f1d35',
          borderRadius: '8px',
          border: '1px solid rgba(59,130,246,0.12)',
          padding: '8px 12px',
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
          height: '100%',
          borderTop: `2px solid ${color}`,
          boxShadow: '0 0 20px rgba(59,130,246,0.15), 0 4px 16px rgba(0,0,0,0.4)'
        }}
      >
        {/* 顶部：标题 + 图标 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
          <span style={{ fontSize: '11px', fontWeight: 500, color: '#94a3b8', letterSpacing: '0.05em', lineHeight: '1.2' }}>{title}</span>
          <div
            style={{ width: '24px', height: '24px', borderRadius: '6px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, background: `${color}20`, color }}
          >
            {icon}
          </div>
        </div>

        {/* 加载中动画 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '40px' }}>
          <div style={{
            width: '24px',
            height: '24px',
            border: `2px solid ${color}30`,
            borderTop: `2px solid ${color}`,
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite'
          }} />
        </div>

        {/* 趋势占位 */}
        <div style={{ height: '17px' }} />
      </div>
    );
  }

  const formatValue = (v) => { 
    if (v === undefined || v === null || isNaN(v)) return '--';
    switch (format) { 
      case 'percent': return v.toFixed(1) + '%';
      case 'currency': return v.toFixed(2);
      case 'integer': return Math.round(v).toString();
      default: return v.toFixed(1); 
    } 
  };

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? '#22c55e' : trend === 'down' ? '#ef4444' : '#94a3b8';

  return (
    <div
      style={{
        background: '#0f1d35',
        borderRadius: '8px',
        border: '1px solid rgba(59,130,246,0.12)',
        padding: '8px 12px',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        height: '100%',
        borderTop: `2px solid ${color}`,
        boxShadow: '0 0 20px rgba(59,130,246,0.15), 0 4px 16px rgba(0,0,0,0.4)',
        transition: 'transform 0.2s',
        cursor: 'pointer'
      }}
      onMouseOver={e => e.currentTarget.style.transform = 'scale(1.02)'}
      onMouseOut={e => e.currentTarget.style.transform = 'scale(1)'}
    >
      {/* 顶部：标题 + 图标 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
        <span style={{ fontSize: '11px', fontWeight: 500, color: '#94a3b8', letterSpacing: '0.05em', lineHeight: '1.2' }}>{title}</span>
        <div
          style={{ width: '24px', height: '24px', borderRadius: '6px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, background: `${color}20`, color }}
        >
          {icon}
        </div>
      </div>

      {/* 数值 */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span
          style={{ color, fontSize: '20px', fontWeight: 'bold',
            fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
            letterSpacing: '-0.02em',
            animation: 'countUp 0.6s ease-out forwards' }}
        >
          {formatValue(animatedValue)}
        </span>
        {unit && (
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>{unit}</span>
        )}
      </div>

      {/* 趋势 */}
      {trendValue && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
          <TrendIcon size={11} style={{ color: trendColor }} />
          <span style={{ fontSize: '11px', color: trendColor }}>{trendValue}</span>
          <span style={{ fontSize: '11px', color: '#64748b' }}>较上月</span>
        </div>
      )}
    </div>
  ); 
}
