// 供应链运营数据工具函数

// 采购订单状态映射
export const PO_STATUS_MAP = {
  '已下单': { label: '已下单', color: '#3b82f6' },
  '生产中': { label: '生产中', color: '#f59e0b' },
  '已发货': { label: '已发货', color: '#8b5cf6' },
  '已交付': { label: '已交付', color: '#10b981' },
  '延迟': { label: '延迟', color: '#ef4444' }
};

// 工单状态映射
export const WO_STATUS_MAP = {
  '未开始': { label: '未开始', color: '#6b7280' },
  '生产中': { label: '生产中', color: '#f59e0b' },
  '已完成': { label: '已完成', color: '#10b981' },
  '已延迟': { label: '已延迟', color: '#ef4444' }
};

// 客户订单状态映射
export const CO_STATUS_MAP = {
  '待确认': { label: '待确认', color: '#6b7280' },
  '生产中': { label: '生产中', color: '#f59e0b' },
  '已发货': { label: '已发货', color: '#8b5cf6' },
  '已完成': { label: '已完成', color: '#10b981' }
};

// 格式化日期
export function formatDate(dateStr) {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit' 
    });
  } catch {
    return dateStr;
  }
}

// 格式化日期时间
export function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

// 判断是否延迟
export function isDelayed(expectedDate, status) {
  if (status === '已交付' || status === '已完成') return false;
  if (!expectedDate) return false;
  
  try {
    const expected = new Date(expectedDate);
    const now = new Date();
    return expected < now;
  } catch {
    return false;
  }
}

// 判断是否即将到期
export function isUpcoming(requiredDate, days = 7) {
  if (!requiredDate) return false;
  
  try {
    const required = new Date(requiredDate);
    const now = new Date();
    const deadline = new Date();
    deadline.setDate(deadline.getDate() + days);
    
    return now <= required && required <= deadline;
  } catch {
    return false;
  }
}

// 计算剩余天数
export function getDaysRemaining(dateStr) {
  if (!dateStr) return 999;
  
  try {
    const target = new Date(dateStr);
    const now = new Date();
    const diff = target - now;
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  } catch {
    return 999;
  }
}

// 计算库存健康度
export function calculateInventoryHealth(available, safety) {
  if (!safety || safety === 0) return 100;
  return Math.round((available / safety) * 100 * 100) / 100;
}

// 获取库存健康度颜色
export function getInventoryHealthColor(ratio) {
  if (ratio >= 100) return '#10b981'; // 绿色
  if (ratio >= 70) return '#f59e0b';  // 橙色
  if (ratio >= 50) return '#f97316';  // 深橙
  return '#ef4444';                    // 红色
}

// 格式化金额
export function formatCurrency(amount, unit = '元') {
  if (!amount && amount !== 0) return '-';
  return `${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${unit}`;
}

// 格式化大数字
export function formatLargeNumber(num) {
  if (!num && num !== 0) return '-';
  if (num >= 100000000) {
    return `${(num / 100000000).toFixed(2)}亿`;
  }
  if (num >= 10000) {
    return `${(num / 10000).toFixed(2)}万`;
  }
  return num.toLocaleString('zh-CN');
}

// 获取状态样式
export function getStatusStyle(status, type = 'po') {
  const map = type === 'po' ? PO_STATUS_MAP : type === 'wo' ? WO_STATUS_MAP : CO_STATUS_MAP;
  const config = map[status] || { label: status, color: '#6b7280' };
  
  return {
    color: config.color,
    background: `${config.color}15`,
    border: `1px solid ${config.color}40`
  };
}
