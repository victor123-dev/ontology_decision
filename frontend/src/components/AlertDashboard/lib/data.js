// 供应链运营监控看板 - API 服务层
import axios from 'axios';

const API_BASE_URL = '/api/v1/alert-dashboard';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 看板数据接口
export const alertDashboardApi = {
  // ==================== 供应链运营KPI ====================
  getPOExecutionRate: () => api.get('/kpi/po-execution-rate'),
  getInventoryHealthRate: () => api.get('/kpi/inventory-health-rate'),
  getWOOnTimeDeliveryRate: () => api.get('/kpi/wo-on-time-delivery-rate'),
  getMonthlyCustomerOrderAmount: () => api.get('/kpi/monthly-customer-order-amount'),
  getActiveRiskCount: () => api.get('/kpi/active-risk-count'),
  getHighRiskSupplierCount: () => api.get('/kpi/high-risk-supplier-count'),

  // ==================== 采购执行 API ====================
  getDelayedPurchaseOrders: () => api.get('/purchase/delayed-orders'),
  getSupplierPerformance: () => api.get('/purchase/supplier-performance'),

  // ==================== 库存健康 API ====================
  getLowInventoryAlerts: () => api.get('/inventory/alerts'),

  // ==================== 工单跟踪 API ====================
  getDelayedWorkOrders: () => api.get('/work-order/delayed'),

  // ==================== 销售订单 API ====================
  getUpcomingCustomerOrders: () => api.get('/customer-order/upcoming'),
  getCustomerOrderTrend: () => api.get('/customer-order/trend'),

  // ==================== 风险监控 API ====================
  getActiveRisks: () => api.get('/risks/active'),
  getRiskStatistics: () => api.get('/risks/statistics'),
  getRiskTrend: (days = 30) => api.get(`/risks/trend?days=${days}`),
  getTopAffectedSuppliers: () => api.get('/risks/top-suppliers'),
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
