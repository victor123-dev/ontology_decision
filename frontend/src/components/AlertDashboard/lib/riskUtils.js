// 外部供应链风险数据工具函数

// 风险类别映射
export const RISK_CATEGORY_MAP = {
  natural_disaster: '自然灾害',
  geopolitical: '地缘政治',
  financial: '财务风险',
  quality: '质量风险',
  legal: '法律合规',
  operational: '运营风险'
};

// 风险等级映射
export const RISK_LEVEL_MAP = {
  critical: { label: '严重', color: '#ef4444' },
  high: { label: '高', color: '#f97316' },
  medium: { label: '中', color: '#eab308' },
  low: { label: '低', color: '#3b82f6' }
};

// 风险状态映射
export const RISK_STATUS_MAP = {
  new: { label: '新发现', color: '#ef4444' },
  analyzing: { label: '分析中', color: '#f59e0b' },
  mitigating: { label: '缓解中', color: '#3b82f6' },
  resolved: { label: '已解决', color: '#10b981' },
  ignored: { label: '已忽略', color: '#6b7280' }
};

// 影响范围映射
export const IMPACT_SCOPE_MAP = {
  global: '全球',
  regional: '区域',
  local: '局部'
};

// 关联类型映射
export const ASSOCIATION_TYPE_MAP = {
  direct: '直接影响',
  indirect: '间接影响',
  potential: '潜在影响'
};

// 格式化风险类别
export function formatRiskCategory(category) {
  return RISK_CATEGORY_MAP[category] || category;
}

// 获取风险等级样式
export function getRiskLevelStyle(level) {
  const config = RISK_LEVEL_MAP[level] || { label: level, color: '#6b7280' };
  return {
    color: config.color,
    background: `${config.color}15`,
    border: `1px solid ${config.color}40`
  };
}

// 获取风险等级颜色
export function getRiskLevelColor(level) {
  return RISK_LEVEL_MAP[level]?.color || '#6b7280';
}

// 格式化风险状态
export function formatRiskStatus(status) {
  return RISK_STATUS_MAP[status]?.label || status;
}

// 获取风险状态样式
export function getRiskStatusStyle(status) {
  const config = RISK_STATUS_MAP[status] || { label: status, color: '#6b7280' };
  return {
    color: config.color,
    background: `${config.color}15`,
    border: `1px solid ${config.color}40`
  };
}

// 格式化影响范围
export function formatImpactScope(scope) {
  return IMPACT_SCOPE_MAP[scope] || scope;
}

// 格式化关联类型
export function formatAssociationType(type) {
  return ASSOCIATION_TYPE_MAP[type] || type;
}

// 获取置信度颜色
export function getConfidenceColor(score) {
  if (score >= 0.8) return '#10b981';  // 绿色
  if (score >= 0.6) return '#f59e0b';  // 橙色
  return '#ef4444';                     // 红色
}
