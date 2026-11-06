import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({ baseURL: '/api', timeout: 180000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('ha_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err?.response?.data?.detail || err.message || '请求失败'
    if (err?.response?.status === 401) {
      localStorage.removeItem('ha_token')
      localStorage.removeItem('ha_user')
      // 路由是 path 模式（createWebHistory），整页跳到 /login；
      // 已在 /login 时不再跳，避免反复整页刷新
      if (location.pathname !== '/login') location.href = '/login'
    }
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    return Promise.reject(err)
  }
)

export const auth = {
  register: (username, password) => http.post('/auth/register', { username, password }),
  login: (username, password) => http.post('/auth/login', { username, password }),
  profile: () => http.get('/auth/profile'),
  updateProfile: (patch) => http.put('/auth/profile', patch),
  uploadAvatar: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/auth/avatar', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  // 微信扫码登录
  wechatQr: () => http.get('/auth/wechat/qr'),
  wechatPoll: (ticket) => http.get('/auth/wechat/poll', { params: { ticket } }),
  wechatConfirm: (ticket) => http.post('/auth/wechat/confirm', { ticket })
}

export const api = {
  parseText: (text) => http.post('/parse/text', { text }),
  parseFile: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/parse/file', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  createRecord: (payload) => http.post('/records', payload),
  listRecords: () => http.get('/records'),
  getRecord: (id) => http.get(`/records/${id}`),
  genReport: (id) => http.post(`/records/${id}/report`),
  updateRecord: (id, payload) => http.put(`/records/${id}`, payload),
  deleteRecord: (id) => http.delete(`/records/${id}`),
  overview: () => http.get('/overview'),
  trend: () => http.get('/trend'),
  trendAnalysis: () => http.post('/trend/analysis'),
  chat: (question, recordId) => http.post('/chat', { question, record_id: recordId }),
  insights: (recordId) => http.get('/rules/insights/latest', { params: recordId ? { record_id: recordId } : {} }),
  metricRule: (key) => http.get(`/rules/${key}`),
  metricCatalog: () => http.get('/rules/metrics'),
  checkTypes: () => http.get('/check-types'),
  health: () => http.get('/health')
}

export default http
