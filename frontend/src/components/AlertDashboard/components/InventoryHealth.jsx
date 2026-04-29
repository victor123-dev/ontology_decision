import { useLowInventoryAlerts } from '../hooks/useOperationData';
import { calculateInventoryHealth, getInventoryHealthColor } from '../lib/operationUtils';

export default function InventoryHealth() {
  const { data: alerts, loading, error } = useLowInventoryAlerts();

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
        共 {alerts.length} 个物料低于安全库存
      </div>
      
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.15)' }}>
              <th style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>物料</th>
              <th style={{ padding: '6px', textAlign: 'right', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>可用</th>
              <th style={{ padding: '6px', textAlign: 'right', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>安全</th>
              <th style={{ padding: '6px', textAlign: 'center', color: '#94a3b8', fontWeight: 500, position: 'sticky', top: 0, background: '#0f172a' }}>健康度</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(item => {
              const healthRatio = calculateInventoryHealth(item.available_quantity, item.safety_stock_level);
              const healthColor = getInventoryHealthColor(healthRatio);
              
              return (
                <tr key={item.inventory_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '6px' }}>
                    <div style={{ color: '#e2e8f0', fontSize: '11px' }}>{item.material_name}</div>
                    <div style={{ color: '#64748b', fontSize: '9px' }}>{item.material_id}</div>
                  </td>
                  <td style={{ padding: '6px', textAlign: 'right', color: healthColor, fontWeight: 'bold' }}>
                    {item.available_quantity.toFixed(0)}
                  </td>
                  <td style={{ padding: '6px', textAlign: 'right', color: '#94a3b8' }}>
                    {item.safety_stock_level.toFixed(0)}
                  </td>
                  <td style={{ padding: '6px', textAlign: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center' }}>
                      <div style={{ width: '40px', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${Math.min(healthRatio, 100)}%`,
                            background: healthColor,
                            borderRadius: '2px'
                          }}
                        />
                      </div>
                      <span style={{ color: healthColor, fontSize: '10px', minWidth: '35px' }}>
                        {healthRatio}%
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
            
            {alerts.length === 0 && (
              <tr>
                <td colSpan={4} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                  ✓ 所有物料库存充足
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
