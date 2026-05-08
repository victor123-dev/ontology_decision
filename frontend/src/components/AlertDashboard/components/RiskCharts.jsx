import { useEffect } from 'react';
import { useRiskStatistics, useTopAffectedSuppliers } from '../hooks/useRiskData';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { formatRiskCategory, getRiskLevelColor } from '../lib/riskUtils';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#3b82f6', '#8b5cf6', '#10b981'];

export default function RiskCharts({ refreshTrigger }) {
  const { data: stats, loading: loadingStats, refetch: refetchStats } = useRiskStatistics();
  const { data: topSuppliers, loading: loadingSuppliers, refetch: refetchSuppliers } = useTopAffectedSuppliers();
  
  useEffect(() => {
    if (refreshTrigger > 0) {
      refetchStats();
      refetchSuppliers();
    }
  }, [refreshTrigger, refetchStats, refetchSuppliers]);

  if (loadingStats || loadingSuppliers) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
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

  // 准备风险等级数据
  const levelData = stats?.by_level ? Object.entries(stats.by_level).map(([name, value]) => ({
    name: name.toUpperCase(),
    value
  })) : [];

  // 准备风险类别数据
  const categoryData = stats?.by_category ? Object.entries(stats.by_category).map(([name, value]) => ({
    name: formatRiskCategory(name),
    value
  })) : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>
      {/* 风险等级分布 */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px' }}>风险等级分布</div>
        {levelData.length > 0 ? (
          <ResponsiveContainer width="100%" height={120}>
            <PieChart>
              <Pie
                data={levelData}
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={50}
                paddingAngle={5}
                dataKey="value"
              >
                {levelData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getRiskLevelColor(entry.name.toLowerCase())} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#1e293b',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '4px',
                  fontSize: '11px',
                  color: '#e2e8f0'
                }}
                itemStyle={{ color: '#e2e8f0' }}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ textAlign: 'center', color: '#64748b', fontSize: '11px', padding: '20px' }}>
            暂无数据
          </div>
        )}
      </div>

      {/* 风险类别统计 */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px' }}>风险类别统计</div>
        {categoryData.length > 0 ? (
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={categoryData}>
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: 9, fill: '#94a3b8' }}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
              />
              <YAxis 
                tick={{ fontSize: 9, fill: '#94a3b8' }}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
              />
              <Tooltip
                contentStyle={{
                  background: '#1e293b',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '4px',
                  fontSize: '11px',
                  color: '#e2e8f0'
                }}
                itemStyle={{ color: '#e2e8f0' }}
              />
              <Bar dataKey="value" fill="#3b82f6" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ textAlign: 'center', color: '#64748b', fontSize: '11px', padding: '20px' }}>
            暂无数据
          </div>
        )}
      </div>

      {/* 受影响供应商TOP5 */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px' }}>受影响供应商TOP5</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {topSuppliers.map((supplier, idx) => (
            <div
              key={supplier.supplier_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 8px',
                borderRadius: '4px',
                background: 'rgba(255,255,255,0.03)'
              }}
            >
              <span style={{
                width: '18px', height: '18px', borderRadius: '50%',
                background: idx < 3 ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.05)',
                color: idx < 3 ? '#ef4444' : '#94a3b8',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '9px', fontWeight: 'bold'
              }}>
                {idx + 1}
              </span>
              <span style={{ flex: 1, color: '#e2e8f0', fontSize: '11px' }}>{supplier.supplier_name}</span>
              <span style={{
                padding: '2px 6px', borderRadius: '4px', fontSize: '10px',
                background: 'rgba(239,68,68,0.15)', color: '#ef4444'
              }}>
                {supplier.risk_count}个风险
              </span>
            </div>
          ))}
          
          {topSuppliers.length === 0 && (
            <div style={{ textAlign: 'center', color: '#64748b', fontSize: '11px', padding: '20px' }}>
              暂无数据
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
