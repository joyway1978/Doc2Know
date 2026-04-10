/**
 * API 客户端
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// 文档 API
export const documentsApi = {
  // 上传文档
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 上传文档并流式返回进度
  uploadStream: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch('/api/documents/upload/stream', {
      method: 'POST',
      body: formData,
    });
  },

  // 获取文档列表
  list: (params?: { page?: number; page_size?: number; status?: string }) => {
    return apiClient.get('/documents', { params });
  },

  // 获取文档详情
  get: (id: string) => {
    return apiClient.get(`/documents/${id}`);
  },

  // 获取文档进度
  getProgress: (id: string) => {
    return new EventSource(`/api/documents/${id}/progress`);
  },

  // 删除文档
  delete: (id: string) => {
    return apiClient.delete(`/documents/${id}`);
  },

  // 重试处理
  retry: (id: string) => {
    return apiClient.post(`/documents/${id}/retry`);
  },
};

// 知识库 API
export const knowledgeApi = {
  // 获取知识库列表
  list: (params?: { search?: string; tag?: string; page?: number; page_size?: number }) => {
    return apiClient.get('/knowledge', { params });
  },

  // 获取知识库详情
  get: (id: string) => {
    return apiClient.get(`/knowledge/${id}`);
  },

  // 获取内容
  getContent: (id: string) => {
    return apiClient.get(`/knowledge/${id}/content`);
  },

  // 获取标签列表
  getTags: () => {
    return apiClient.get('/knowledge/tags');
  },

  // 获取相关内容
  getRelated: (id: string, limit?: number) => {
    return apiClient.get(`/knowledge/${id}/related`, { params: { limit } });
  },

  // 重建索引
  rebuildIndex: () => {
    return apiClient.post('/knowledge/rebuild-index');
  },
};

// 配置 API
export const configApi = {
  // 获取配置
  get: () => {
    return apiClient.get('/config');
  },

  // 获取统计信息
  getStats: () => {
    return apiClient.get('/config/stats');
  },

  // 健康检查
  health: () => {
    return apiClient.get('/config/health');
  },

  // 更新配置
  update: (data: any) => {
    return apiClient.post('/config/update', data);
  },

  // 获取环境信息
  getEnvironment: () => {
    return apiClient.get('/config/environment');
  },
};

export default apiClient;
