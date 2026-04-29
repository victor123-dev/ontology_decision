import { useUpcomingCustomerOrders } from '../hooks/useOperationData';
import { formatDate, formatCurrency, getDaysRemaining } from '../lib/operationUtils';

export default function SalesOverview() {
  const { data: upcomingOrders, loading, error } = useUpcomingCustomerOrders();

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '150px' }}>
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

  // 计算总金额
  const totalAmount = upcomingOrders.reduce((sum, order) => sum + order.total_amount, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 汇总信息 */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', flexShrink: 0 }}>
        <div style={{
          flex: 1, padding: '10px', borderRadius: '6px',
          background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)'
        }}>
          <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>即将到期订单</div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#60a5fa' }}>{upcomingOrders.length}</div>
        </div>
        <div style={{
          flex: 1, padding: '10px', borderRadius: '6px',
          background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)'
        }}>
          <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>总金额</div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#10b981' }}>{formatCurrency(totalAmount)}</div>
        </div>
      </div>

      {/* 订单列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.15)' }}>
              <th style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>订单号</th>
              <th style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>客户</th>
              <th style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>产品</th>
              <th style={{ padding: '6px', textAlign: 'right', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>金额</th>
              <th style={{ padding: '6px', textAlign: 'center', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>剩余天数</th>
              <th style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>要求交期</th>
            </tr>
          </thead>
          <tbody>
            {upcomingOrders.map(order => {
              const daysRemaining = getDaysRemaining(order.required_date);
              const urgencyColor = daysRemaining <= 2 ? '#ef4444' : daysRemaining <= 5 ? '#f59e0b' : '#3b82f6';
              
              return (
                <tr key={order.order_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '6px', color: '#60a5fa', fontSize: '10px' }}>{order.order_id}</td>
                  <td style={{ padding: '6px', color: '#cbd5e1' }}>
                    <div style={{ fontSize: '11px' }}>{order.customer_name}</div>
                    <div style={{ fontSize: '9px', color: '#64748b' }}>{order.customer_po_number}</div>
                  </td>
                  <td style={{ padding: '6px', color: '#e2e8f0', fontSize: '11px' }}>{order.product_name}</td>
                  <td style={{ padding: '6px', textAlign: 'right', color: '#10b981', fontWeight: 'bold' }}>
                    {formatCurrency(order.total_amount)}
                  </td>
                  <td style={{ padding: '6px', textAlign: 'center' }}>
                    <span style={{
                      padding: '2px 6px', borderRadius: '4px', fontSize: '10px',
                      background: `${urgencyColor}15`, color: urgencyColor
                    }}>
                      {daysRemaining}天
                    </span>
                  </td>
                  <td style={{ padding: '6px', color: '#94a3b8', fontSize: '10px' }}>
                    {formatDate(order.required_date)}
                  </td>
                </tr>
              );
            })}
            
            {upcomingOrders.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                  暂无即将到期的订单
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
