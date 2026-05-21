/**
 * API服务 - 与后端通信
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 401 未认证：清除token并跳转登录
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    console.error('API Error:', error.response?.data || error.message)
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

// 聊天相关API
export const chatApi = {
  sendMessage: (data: { session_id?: string; user_id: string; message: string }) =>
    api.post('/chat/message', data),

  submitFeedback: (data: { session_id: string; log_id: string; feedback: string }) =>
    api.post('/chat/feedback', data),

  executeAction: (sessionId: string, actionId: string, params?: Record<string, any>) =>
    api.post(`/chat/action?session_id=${sessionId}&action_id=${actionId}`, params || {}),
}

// 知识库相关API
export const knowledgeApi = {
  list: (params?: { page?: number; page_size?: number; type?: string; status?: string; keyword?: string }) =>
    api.get('/knowledge/list', { params }),

  get: (knowledgeId: string) =>
    api.get(`/knowledge/${knowledgeId}`),

  create: (data: any) =>
    api.post('/knowledge/create', data),

  update: (knowledgeId: string, data: any) =>
    api.put(`/knowledge/${knowledgeId}`, data),

  publish: (knowledgeId: string) =>
    api.post(`/knowledge/${knowledgeId}/publish`),

  offline: (knowledgeId: string) =>
    api.post(`/knowledge/${knowledgeId}/offline`),

  stats: () =>
    api.get('/knowledge/stats/overview'),
}

// 会话相关API
export const sessionApi = {
  list: (params?: { user_id?: string; status?: string; page?: number }) =>
    api.get('/sessions/list', { params }),

  get: (sessionId: string) =>
    api.get(`/sessions/${sessionId}`),

  history: (sessionId: string) =>
    api.get(`/sessions/${sessionId}/history`),

  handoff: (data: { session_id: string; reason?: string }) =>
    api.post('/sessions/handoff', data),

  close: (sessionId: string) =>
    api.post(`/sessions/${sessionId}/close`),
}

// 认证相关API
export const authApi = {
  login: (username: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },

  register: (username: string, password: string, email?: string) =>
    api.post('/auth/register', { username, password, email }),

  me: () => api.get('/auth/me'),
}

// 管理后台API
export const adminApi = {
  dashboard: () =>
    api.get('/admin/dashboard'),

  metrics: (days?: number) =>
    api.get('/admin/metrics', { params: { days } }),

  conversationLogs: (params?: { session_id?: string; intent?: string; page?: number }) =>
    api.get('/admin/logs/conversations', { params }),

  ruleLogs: (params?: { session_id?: string; page?: number }) =>
    api.get('/admin/logs/rules', { params }),

  toolLogs: (params?: { session_id?: string; tool_name?: string; page?: number }) =>
    api.get('/admin/logs/tools', { params }),
}

export default api
