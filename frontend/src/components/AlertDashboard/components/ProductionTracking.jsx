import { useEffect } from 'react';
import { useDelayedWorkOrders } from '../hooks/useOperationData';
import { formatDate } from '../lib/operationUtils';

export default function ProductionTracking({ refreshTrigger }) {
  const { data: delayedOrders, loading, error, refetch } = useDelayedWorkOrders();
  
  useEffect(() => {
    if (refreshTrigger > 0) {
      refetch();
    }
  }, [refreshTrigger, refetch]);

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
    return <div style={{ padding: '16px', color: '#ef4444', fontSize: '12px' }}>加载失败: {error}</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: '8px', fontSize: '11px', color: '#64748b' }}>
        共 {delayedOrders.length} 个工单延期
      </div>
      
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(239,68,68,0.15)' }}>
              <th style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>工单号</th>
              <th style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>产品</th>
              <th style={{ padding: '6px', textAlign: 'right', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>数量</th>
              <th style={{ padding: '6px', textAlign: 'center', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>延期</th>
              <th style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>状态</th>
            </tr>
          </thead>
          <tbody>
            {delayedOrders.map(order => (
              <tr key={order.work_order_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '6px', color: '#60a5fa', fontSize: '10px' }}>{order.work_order_id}</td>
                <td style={{ padding: '6px', color: '#e2e8f0' }}>
                  <div style={{ fontSize: '11px' }}>{order.product_name}</div>
                  <div style={{ fontSize: '9px', color: '#64748b' }}>{order.product_id}</div>
                </td>
                <td style={{ padding: '6px', textAlign: 'right', color: '#cbd5e1' }}>
                  {order.planned_quantity.toFixed(0)}
                </td>
                <td style={{ padding: '6px', textAlign: 'center' }}>
                  <span style={{
                    padding: '2px 6px', borderRadius: '4px', fontSize: '10px',
                    background: 'rgba(239,68,68,0.15)', color: '#ef4444'
                  }}>
                    {order.delay_days}天
                  </span>
                </td>
                <td style={{ padding: '6px' }}>
                  <span style={{
                    padding: '2px 6px', borderRadius: '4px', fontSize: '10px',
                    background: 'rgba(245,158,11,0.15)', color: '#f59e0b'
                  }}>
                    {order.status}
                  </span>
                </td>
              </tr>
            ))}
            
            {delayedOrders.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                  ✓ 所有工单按时进行中
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
