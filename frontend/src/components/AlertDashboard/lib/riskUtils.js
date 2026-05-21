// 外部供应链风险数据工具函数

// 风险类别映射
export const RISK_CATEGORY_MAP = {
  自然灾害: '自然灾害',
  物流延期: '物流延期',
  原材料供应短缺: '原材料供应短缺',
  原材料价格波动: '原材料价格波动',
  地缘政治: '地缘政治',
  财务风险: '财务风险',
  质量风险: '质量风险',
  法律合规: '法律合规',
  运营风险: '运营风险'
};

// 风险等级映射
export const RISK_LEVEL_MAP = {
  严重: { label: '严重', color: '#ef4444' },
  高: { label: '高', color: '#f97316' },
  中: { label: '中', color: '#eab308' },
  低: { label: '低', color: '#3b82f6' }
};

// 风险状态映射
export const RISK_STATUS_MAP = {
  新发现: { label: '新发现', color: '#ef4444' },
  待处理: { label: '待处理', color: '#ef4444' },
  分析中: { label: '分析中', color: '#f59e0b' },
  缓解中: { label: '缓解中', color: '#3b82f6' },
  已解决: { label: '已解决', color: '#10b981' },
  已忽略: { label: '已忽略', color: '#6b7280' }
};

// 影响范围映射
export const IMPACT_SCOPE_MAP = {
  全球: '全球',
  区域: '区域',
  局部: '局部'
};

// 关联类型映射
export const ASSOCIATION_TYPE_MAP = {
  直接影响: '直接影响',
  间接影响: '间接影响',
  潜在影响: '潜在影响'
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
