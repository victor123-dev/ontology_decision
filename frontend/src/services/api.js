import axios from 'axios';

const API_BASE_URL = 'http://localhost:8081/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 数据源管理
export const dataSourceApi = {
  create: (data) => api.post('/data-sources', data),
  getAll: () => api.get('/data-sources'),
  get: (id) => api.get(`/data-sources/${id}`),
  update: (id, data) => api.put(`/data-sources/${id}`, data),
  delete: (id) => api.delete(`/data-sources/${id}`),
  testConnection: (id) => api.post(`/data-sources/${id}/test-connection`),
  getTables: (id) => api.get(`/data-sources/${id}/tables`),
};

// 业务模型管理
export const businessModelApi = {
  create: (data) => api.post('/business-models', data),
  getAll: () => api.get('/business-models'),
  get: (id) => api.get(`/business-models/${id}`),
  update: (id, data) => api.put(`/business-models/${id}`, data),
  delete: (id) => api.delete(`/business-models/${id}`),
  import: (data) => api.post('/business-models/import', data),
  updateField: (modelId, fieldId, data) => api.put(`/business-models/${modelId}/fields/${fieldId}`, data),
};

// 数据感知配置
export const dataSensingApi = {
  create: (data) => api.post('/data-sensing-configs', data),
  getAll: () => api.get('/data-sensing-configs'),
  get: (id) => api.get(`/data-sensing-configs/${id}`),
  update: (id, data) => api.put(`/data-sensing-configs/${id}`, data),
  delete: (id) => api.delete(`/data-sensing-configs/${id}`),
};

// 驱动逻辑配置
export const driveLogicApi = {
  create: (data) => api.post('/drive-logics', data),
  getAll: () => api.get('/drive-logics'),
  get: (id) => api.get(`/drive-logics/${id}`),
  update: (id, data) => api.put(`/drive-logics/${id}`, data),
  delete: (id) => api.delete(`/drive-logics/${id}`),
  createTask: (data) => api.post('/tasks', data),
  getAllTasks: () => api.get('/tasks'),
  updateTask: (id, data) => api.put(`/tasks/${id}`, data),
  deleteTask: (id) => api.delete(`/tasks/${id}`),
  getAllTaskInstances: () => api.get('/task-instances'),
  getTaskInstancesByTask: (taskId) => api.get(`/tasks/${taskId}/instances`),
};

// Agent管理
export const agentApi = {
  create: (data) => api.post('/agents', data),
  getAll: () => api.get('/agents'),
  get: (id) => api.get(`/agents/${id}`),
  update: (id, data) => api.put(`/agents/${id}`, data),
  delete: (id) => api.delete(`/agents/${id}`),
  createCapability: (data) => api.post('/capabilities', data),
  getAllCapabilities: () => api.get('/capabilities'),
  updateCapability: (id, data) => api.put(`/capabilities/${id}`, data),
  deleteCapability: (id) => api.delete(`/capabilities/${id}`),
};

// 测试数据管理
export const testDataApi = {
  get: (dataSourceId, tableName, limit = 50) => api.get(`/test-data/${dataSourceId}/${tableName}?limit=${limit}`),
  insert: (dataSourceId, tableName, data) => api.post(`/test-data/${dataSourceId}/${tableName}`, data),
  delete: (dataSourceId, tableName, data) => api.delete(`/test-data/${dataSourceId}/${tableName}`, { data }),
  update: (dataSourceId, tableName, data) => api.put(`/test-data/${dataSourceId}/${tableName}`, data),
};

// 驱动日志管理
export const driveLogApi = {
  create: (data) => api.post('/drive-logs', data),
  getAll: (params) => api.get('/drive-logs', { params }),
  get: (id) => api.get(`/drive-logs/${id}`),
};

// 测试执行
export const testExecutionApi = {
  simulateEvent: (data) => api.post('/test-execution/simulate-event', data),
};

export default api;
