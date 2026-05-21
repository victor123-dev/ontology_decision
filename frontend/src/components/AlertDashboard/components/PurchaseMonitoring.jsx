import { useState, useEffect } from 'react';
import { useDelayedPurchaseOrders, useSupplierPerformance } from '../hooks/useOperationData';
import { formatDate, formatCurrency, getStatusStyle } from '../lib/operationUtils';

export default function PurchaseMonitoring({ refreshTrigger }) {
  const [activeTab, setActiveTab] = useState('delayed');
  const { data: delayedOrders, loading: loadingDelayed, refetch } = useDelayedPurchaseOrders();
  const { data: supplierPerf, loading: loadingPerf, refetch: refetchPerf } = useSupplierPerformance();
  
  // 监听刷新触发器
  useEffect(() => {
    if (refreshTrigger > 0) {
      refetch();
      refetchPerf();
    }
  }, [refreshTrigger, refetch, refetchPerf]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Tab切换 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexShrink: 0 }}>
        <button
          onClick={() => setActiveTab('delayed')}
          style={{
            padding: '4px 12px', fontSize: '11px', borderRadius: '4px',
            background: activeTab === 'delayed' ? 'rgba(239,68,68,0.1)' : 'rgba(24,144,255,0.04)',
            color: activeTab === 'delayed' ? '#ef4444' : '#4a6fa5',
            border: `1px solid ${activeTab === 'delayed' ? 'rgba(239,68,68,0.3)' : 'rgba(24,144,255,0.12)'}`
          }}
        >
          延迟订单 ({delayedOrders.length})
        </button>
        <button
          onClick={() => setActiveTab('performance')}
          style={{
            padding: '4px 12px', fontSize: '11px', borderRadius: '4px',
            background: activeTab === 'performance' ? 'rgba(59,130,246,0.1)' : 'rgba(24,144,255,0.04)',
            color: activeTab === 'performance' ? '#3b82f6' : '#4a6fa5',
            border: `1px solid ${activeTab === 'performance' ? 'rgba(59,130,246,0.3)' : 'rgba(24,144,255,0.12)'}`
          }}
        >
          供应商表现
        </button>
      </div>

      {/* 延迟订单列表 */}
      {activeTab === 'delayed' && (
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loadingDelayed ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '150px' }}>
              <div style={{
                width: '24px', height: '24px',
                border: '2px solid rgba(59,130,246,0.2)',
                borderTop: '2px solid #3b82f6',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite'
              }} />
            </div>
          ) : delayedOrders.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: '#8aa3c0', fontSize: '12px' }}>
              ✓ 所有采购订单均按时交付
            </div>
          ) : (
            <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(239,68,68,0.15)' }}>
                  <th style={{ padding: '6px', textAlign: 'left', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>PO号</th>
                  <th style={{ padding: '6px', textAlign: 'left', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>供应商</th>
                  <th style={{ padding: '6px', textAlign: 'right', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>金额</th>
                  <th style={{ padding: '6px', textAlign: 'center', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>延迟天数</th>
                  <th style={{ padding: '6px', textAlign: 'left', color: '#6b8cae', fontWeight: 500, position: 'sticky', top: 0, background: '#e8f4fc' }}>期望交付</th>
                </tr>
              </thead>
              <tbody>
                {delayedOrders.map(order => (
                  <tr key={order.po_id} style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                    <td style={{ padding: '6px', color: '#1890ff', fontSize: '10px' }}>{order.po_id}</td>
                    <td style={{ padding: '6px', color: '#2c5282' }}>{order.supplier_name}</td>
                    <td style={{ padding: '6px', color: '#1a3a5c', textAlign: 'right' }}>{formatCurrency(order.total_amount)}</td>
                    <td style={{ padding: '6px', textAlign: 'center' }}>
                      <span style={{
                        padding: '2px 6px', borderRadius: '4px', fontSize: '10px',
                        background: 'rgba(239,68,68,0.15)', color: '#ef4444'
                      }}>
                        {order.delay_days}天
                      </span>
                    </td>
                    <td style={{ padding: '6px', color: '#8aa3c0', fontSize: '10px' }}>{formatDate(order.expected_delivery_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* 供应商表现 */}
      {activeTab === 'performance' && (
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loadingPerf ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '150px' }}>
              <div style={{
                width: '24px', height: '24px',
                border: '2px solid rgba(59,130,246,0.2)',
                borderTop: '2px solid #3b82f6',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite'
              }} />
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {supplierPerf.map((supplier, idx) => (
                <div
                  key={supplier.supplier_id}
                  style={{
                    padding: '10px', borderRadius: '6px',
                    background: 'rgba(240,247,255,0.8)',
                    border: '1px solid rgba(24,144,255,0.12)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        width: '20px', height: '20px', borderRadius: '50%',
                        background: idx < 3 ? 'rgba(59,130,246,0.1)' : 'rgba(24,144,255,0.06)',
                        color: idx < 3 ? '#1890ff' : '#6b8cae',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '10px', fontWeight: 'bold'
                      }}>
                        {idx + 1}
                      </span>
                      <span style={{ color: '#1a3a5c', fontSize: '12px' }}>{supplier.supplier_name}</span>
                    </div>
                    <span style={{
                      padding: '2px 8px', borderRadius: '4px', fontSize: '11px',
                      background: supplier.on_time_rate >= 90 ? 'rgba(16,185,129,0.15)' : 
                                 supplier.on_time_rate >= 70 ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                      color: supplier.on_time_rate >= 90 ? '#10b981' : 
                             supplier.on_time_rate >= 70 ? '#f59e0b' : '#ef4444'
                    }}>
                      {supplier.on_time_rate}%
                    </span>
                  </div>
                  
                  {/* 进度条 */}
                  <div style={{ height: '4px', background: 'rgba(24,144,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${supplier.on_time_rate}%`,
                        background: supplier.on_time_rate >= 90 ? '#10b981' : 
                                   supplier.on_time_rate >= 70 ? '#f59e0b' : '#ef4444',
                        borderRadius: '2px',
                        transition: 'width 0.3s ease'
                      }}
                    />
                  </div>
                  
                  <div style={{ marginTop: '4px', fontSize: '10px', color: '#8aa3c0' }}>
                    总订单: {supplier.total_orders} | 准时: {supplier.on_time_count}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
