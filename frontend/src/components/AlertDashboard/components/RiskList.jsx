import React, { useState, useEffect } from 'react';
import { useActiveRisks } from '../hooks/useRiskData';
import { 
  getRiskLevelStyle, 
  getRiskStatusStyle, 
  formatRiskCategory, 
  formatRiskStatus,
  formatImpactScope,
  getRiskLevelColor
} from '../lib/riskUtils';
import { formatDate } from '../lib/operationUtils';

export default function RiskList({ refreshTrigger }) {
  const { data: risks, loading, error, refetch } = useActiveRisks();
  
  useEffect(() => {
    if (refreshTrigger > 0) {
      refetch();
    }
  }, [refreshTrigger, refetch]);
  const [filterLevel, setFilterLevel] = useState('全部等级');
  const [filterCategory, setFilterCategory] = useState('全部类别');
  const [expandedRisk, setExpandedRisk] = useState(null);
  
  // 筛选
  const filteredRisks = risks.filter(risk => {
    const matchLevel = filterLevel === '全部等级' || risk.risk_level === filterLevel;
    const matchCategory = filterCategory === '全部类别' || risk.risk_category === filterCategory;
    return matchLevel && matchCategory;
  });

  if (loading) {
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

  if (error) {
    return (
      <div style={{ padding: '16px', color: '#ef4444', fontSize: '12px' }}>
        加载失败: {error}
        <button onClick={refetch} style={{ marginLeft: '8px', padding: '4px 8px', fontSize: '11px' }}>重试</button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 筛选栏 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexShrink: 0 }}>
        <select
          value={filterLevel}
          onChange={e => setFilterLevel(e.target.value)}
          style={{
            padding: '4px 8px', fontSize: '11px', borderRadius: '4px',
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
            color: '#cbd5e1'
          }}
        >
          <option value="全部等级">全部等级</option>
          <option value="严重">严重</option>
          <option value="高">高</option>
          <option value="中">中</option>
          <option value="低">低</option>
        </select>

        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          style={{
            padding: '4px 8px', fontSize: '11px', borderRadius: '4px',
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
            color: '#cbd5e1'
          }}
        >
          <option value="全部类别">全部类别</option>
          <option value="自然灾害">自然灾害</option>
          <option value="地缘政治">地缘政治</option>
          <option value="财务风险">财务风险</option>
          <option value="质量风险">质量风险</option>
          <option value="法律合规">法律合规</option>
          <option value="运营风险">运营风险</option>
        </select>

        <span style={{ marginLeft: 'auto', fontSize: '11px', color: '#64748b' }}>
          共 {filteredRisks.length} 条
        </span>
      </div>

      {/* 风险列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.15)' }}>
              <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>等级</th>
              <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>标题</th>
              <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>类别</th>
              <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>供应商</th>
              <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>状态</th>
              <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>检测时间</th>
              <th style={{ padding: '8px', textAlign: 'center', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredRisks.map(risk => (
              <React.Fragment key={risk.risk_id}>
                <tr
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer' }}
                  onClick={() => setExpandedRisk(expandedRisk === risk.risk_id ? null : risk.risk_id)}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(59,130,246,0.05)'}
                  onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '8px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '10px', fontSize: '10px',
                      ...getRiskLevelStyle(risk.risk_level)
                    }}>
                      {risk.risk_level.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: '8px', color: '#e2e8f0', maxWidth: '200px' }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={risk.title}>
                      {risk.title}
                    </div>
                  </td>
                  <td style={{ padding: '8px', color: '#cbd5e1' }}>
                    {formatRiskCategory(risk.risk_category)}
                  </td>
                  <td style={{ padding: '8px', color: '#cbd5e1' }}>
                    {risk.supplier_name || '-'}
                  </td>
                  <td style={{ padding: '8px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '10px', fontSize: '10px',
                      ...getRiskStatusStyle(risk.status)
                    }}>
                      {formatRiskStatus(risk.status)}
                    </span>
                  </td>
                  <td style={{ padding: '8px', color: '#94a3b8', fontSize: '10px' }}>
                    {formatDate(risk.detected_at)}
                  </td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>
                    <button
                      style={{
                        padding: '2px 8px', fontSize: '10px', borderRadius: '4px',
                        background: 'rgba(59,130,246,0.1)', color: '#60a5fa',
                        border: '1px solid rgba(59,130,246,0.3)'
                      }}
                      onClick={e => {
                        e.stopPropagation();
                        setExpandedRisk(expandedRisk === risk.risk_id ? null : risk.risk_id);
                      }}
                    >
                      {expandedRisk === risk.risk_id ? '收起' : '详情'}
                    </button>
                  </td>
                </tr>
                
                {/* 展开详情 */}
                {expandedRisk === risk.risk_id && (
                  <tr style={{ background: 'rgba(59,130,246,0.03)' }}>
                    <td colSpan={7} style={{ padding: '12px' }}>
                      <div style={{ fontSize: '11px', color: '#cbd5e1' }}>
                        <div style={{ marginBottom: '8px' }}>
                          <strong style={{ color: '#94a3b8' }}>描述:</strong>
                          <p style={{ margin: '4px 0 0 0', lineHeight: '1.6' }}>{risk.description}</p>
                        </div>
                        
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '8px' }}>
                          <div>
                            <strong style={{ color: '#94a3b8' }}>影响范围:</strong>
                            <span style={{ marginLeft: '4px' }}>{formatImpactScope(risk.impact_scope)}</span>
                          </div>
                          <div>
                            <strong style={{ color: '#94a3b8' }}>预估影响天数:</strong>
                            <span style={{ marginLeft: '4px' }}>{risk.estimated_impact_days} 天</span>
                          </div>
                          <div>
                            <strong style={{ color: '#94a3b8' }}>置信度:</strong>
                            <span style={{ marginLeft: '4px', color: risk.confidence_score >= 0.8 ? '#10b981' : risk.confidence_score >= 0.6 ? '#f59e0b' : '#ef4444' }}>
                              {(risk.confidence_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>

                        {risk.affected_suppliers && risk.affected_suppliers.length > 0 && (
                          <div>
                            <strong style={{ color: '#94a3b8' }}>关联供应商 ({risk.affected_suppliers.length}):</strong>
                            <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                              {risk.affected_suppliers.map((supplier, idx) => (
                                <span
                                  key={idx}
                                  style={{
                                    padding: '2px 8px', borderRadius: '4px', fontSize: '10px',
                                    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)'
                                  }}
                                >
                                  {supplier.supplier_name} 
                                  <span style={{ color: getRiskLevelColor(supplier.impact_level), marginLeft: '4px' }}>
                                    ({supplier.impact_level})
                                  </span>
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            
            {filteredRisks.length === 0 && (
              <tr>
                <td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                  暂无风险数据
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
