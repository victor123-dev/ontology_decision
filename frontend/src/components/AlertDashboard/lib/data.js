// 供应链控制塔 - API 服务层
import axios from 'axios';

const API_BASE_URL = '/api/v1/alert-dashboard';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 预警看板数据接口
export const alertDashboardApi = {
  // KPI 数据 - 单个指标API
  getPurchaseOnTimeRate: () => api.get('/kpi/purchase-on-time-rate'),
  getMonthlySales: () => api.get('/kpi/monthly-sales'),
  getAlertCount: () => api.get('/kpi/alert-count'),
  getAlertExecCount: () => api.get('/kpi/alert-exec-count'),

  // KPI 数据 - 整体API（保留以兼容）
  getKpiData: () => api.get('/kpi'),

  // 图表数据
  getChartData: () => api.get('/chart'),

  // 物流动态数据
  getLogisticsData: () => api.get('/logistics'),

  // 需求预测数据
  getForecastData: () => api.get('/forecast'),

  // 地图数据
  getMapData: () => api.get('/map'),

  // 预警消息数据
  getAlertMessages: () => api.get('/alerts'),
};

// ==================== 工具函数 ====================

export function getRiskColor(level) {
  switch (level) {
    case '最高风险': return 'sct-badge-critical';
    case '高风险': return 'sct-badge-high';
    case '中风险': return 'sct-badge-medium';
    case '低风险': return 'sct-badge-low';
    default: return 'sct-badge-low';
  }
}

export function getRiskTextColor(level) {
  switch (level) {
    case '最高风险': return '#ff4d4d';
    case '高风险': return '#ff7043';
    case '中风险': return '#ffa726';
    case '低风险': return '#66bb6a';
    default: return '#66bb6a';
  }
}

export function getStatusColor(status) {
  switch (status) {
    case '未处理': return '#ef4444';
    case '处理中': return '#f59e0b';
    case '已处理': return '#22c55e';
    default: return '#94a3b8';
  }
}

export function getLogisticsStatusColor(status) {
  switch (status) {
    case '在途': return '#3b82f6';
    case '已到达': return '#22c55e';
    case '延误': return '#ef4444';
    case '清关中': return '#f59e0b';
    default: return '#94a3b8';
  }
}
