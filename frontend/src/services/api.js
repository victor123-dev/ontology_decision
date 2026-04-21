import axios from 'axios';

const API_BASE_URL = '/api/v1';

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
  createField: (modelId, fieldData) => api.post(`/business-models/${modelId}/fields`, fieldData),
  updateField: (modelId, fieldId, data) => api.put(`/business-models/${modelId}/fields/${fieldId}`, data),
  deleteField: (modelId, fieldId) => api.delete(`/business-models/${modelId}/fields/${fieldId}`),
};

// 业务模型关系管理
export const businessModelLinkApi = {
  create: (data) => api.post('/business-model-links', data),
  getAll: () => api.get('/business-model-links'),
  get: (id) => api.get(`/business-model-links/${id}`),
  update: (id, data) => api.put(`/business-model-links/${id}`, data),
  delete: (id) => api.delete(`/business-model-links/${id}`),
  getByModel: (modelId) => api.get(`/business-models/${modelId}/links`),
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
};

// 业务数据管理
export const businessDataApi = {
  getAll: (modelName, limit = 50, offset = 0) => api.post(`/business-data/${modelName}/query`, {
    limit: limit,
    offset: offset
  }),
  getCount: (modelName, filters = []) => api.post(`/business-data/${modelName}/count`, {
    filters: filters
  }),
  get: (modelName, id) => api.get(`/business-data/${modelName}/get`, { params: { id } }),
  create: (modelName, data) => api.post(`/business-data/${modelName}/create`, data),
  update: (modelName, id, data) => api.put(`/business-data/${modelName}/update`, { 
    params: { id }, 
    data: data
  }),
  delete: (modelName, id) => api.delete(`/business-data/${modelName}/delete`, { 
    params: { id }
  }),
};

// 行动管理
export const actionApi = {
  create: (data) => api.post('/actions', data),
  getAll: (modelId) => api.get('/actions', { params: modelId ? { model_id: modelId } : {} }),
  get: (id) => api.get(`/actions/${id}`),
  update: (id, data) => api.put(`/actions/${id}`, data),
  delete: (id) => api.delete(`/actions/${id}`),
  execute: (data) => api.post('/actions/execute', data),
};

// SDK生成
export const sdkApi = {
  generate: (data) => api.post('/sdk/generate', data),
  getInfo: () => api.get('/sdk/info'),
};

// 驱动日志管理
export const driveLogApi = {
  create: (data) => api.post('/drive-logs', data),
  getAll: (params) => api.get('/drive-logs', { params }),
  
  getTraceChain: (traceId) => api.get(`/drive-logs/trace/${traceId}`),
  
  getAllTraces: (params = {}) => {
    const queryParams = new URLSearchParams(params).toString();
    return api.get(`/drive-logs/traces${queryParams ? '?' + queryParams : ''}`);
  }
};

// 本体视图
export const ontologyViewApi = {
  getGraph: () => api.get('/ontology-view/graph'),
};

// 测试执行
export const testExecutionApi = {
  simulateEvent: (data) => api.post('/test-execution/simulate-event', data),
};

// 自然语言规则接口
export const nlRuleApi = {
  parseSensingConfig: (naturalLanguage) => {
    return api.post('/nl-rule-interface/parse-sensing-config', { natural_language: naturalLanguage });
  },
  
  parseDriveLogic: (naturalLanguage) => {
    return api.post('/nl-rule-interface/parse-drive-logic', { natural_language: naturalLanguage });
  },
};

export default api;