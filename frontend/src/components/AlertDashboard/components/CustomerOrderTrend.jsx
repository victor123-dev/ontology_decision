import { useEffect } from 'react';
import { useCustomerOrderTrend } from '../hooks/useOperationData';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function CustomerOrderTrend({ refreshTrigger }) {
  const { data: trendData, loading, error, refetch } = useCustomerOrderTrend();
  
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

  if (!trendData || trendData.length === 0) {
    return (
      <div style={{ textAlign: 'center', color: '#64748b', fontSize: '11px', padding: '40px' }}>
        暂无订单数据
      </div>
    );
  }

  // 过滤掉全为0的日期,只显示有订单的日期
  const filteredData = trendData.filter(d => 
    d.completed > 0 || d.shipping > 0 || d.producing > 0 || d.delayed > 0
  );

  // 如果数据点太多,进行采样(最多显示15个点)
  const displayData = filteredData.length > 15 
    ? filteredData.filter((_, i) => i % Math.ceil(filteredData.length / 15) === 0)
    : filteredData;

  // 格式化日期显示
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 图例说明 */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '8px', flexShrink: 0, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: '#94a3b8' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
          <span>已完成</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: '#94a3b8' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#3b82f6' }} />
          <span>发货中</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: '#94a3b8' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} />
          <span>生产中</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: '#94a3b8' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444' }} />
          <span>延期</span>
        </div>
      </div>

      {/* 面积图 */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={displayData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
            <defs>
              <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorShipping" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorProducing" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorDelayed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
            <XAxis 
              dataKey="date" 
              tickFormatter={formatDate}
              tick={{ fontSize: 10, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(148,163,184,0.2)' }}
            />
            <YAxis 
              tick={{ fontSize: 10, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(148,163,184,0.2)' }}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: '#1e293b',
                border: '1px solid rgba(59,130,246,0.3)',
                borderRadius: '6px',
                fontSize: '11px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
              }}
              labelFormatter={(label) => `日期: ${label}`}
              formatter={(value, name) => {
                const nameMap = {
                  completed: '已完成',
                  shipping: '发货中',
                  producing: '生产中',
                  delayed: '延期'
                };
                return [value, nameMap[name] || name];
              }}
            />
            <Area 
              type="monotone" 
              dataKey="completed" 
              stackId="1"
              stroke="#10b981" 
              fill="url(#colorCompleted)" 
              name="completed"
            />
            <Area 
              type="monotone" 
              dataKey="shipping" 
              stackId="1"
              stroke="#3b82f6" 
              fill="url(#colorShipping)" 
              name="shipping"
            />
            <Area 
              type="monotone" 
              dataKey="producing" 
              stackId="1"
              stroke="#f59e0b" 
              fill="url(#colorProducing)" 
              name="producing"
            />
            <Area 
              type="monotone" 
              dataKey="delayed" 
              stackId="1"
              stroke="#ef4444" 
              fill="url(#colorDelayed)" 
              name="delayed"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
