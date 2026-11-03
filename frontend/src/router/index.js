import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/Login.vue'
import Overview from '@/views/Overview.vue'
import Entry from '@/views/Entry.vue'
import Trend from '@/views/Trend.vue'
import History from '@/views/History.vue'
import Chat from '@/views/Chat.vue'
import Settings from '@/views/Settings.vue'
import WechatMock from '@/views/WechatMock.vue'

const routes = [
  { path: '/login', name: 'login', component: Login },
  { path: '/wechat-mock', name: 'wechat-mock', component: WechatMock }, // 演示模式扫码确认页，无需登录
  { path: '/', redirect: '/overview' },
  { path: '/overview', name: 'overview', component: Overview, meta: { title: '报告总览', icon: '📊' } },
  { path: '/entry', name: 'entry', component: Entry, meta: { title: '录入体检', icon: '📝' } },
  { path: '/trend', name: 'trend', component: Trend, meta: { title: '指标趋势', icon: '📈' } },
  { path: '/history', name: 'history', component: History, meta: { title: '历史档案', icon: '🗂' } },
  { path: '/chat', name: 'chat', component: Chat, meta: { title: 'AI 问答', icon: '💬' } },
  { path: '/settings', name: 'settings', component: Settings, meta: { title: '个人设置', icon: '⚙' } },
  // 兜底：任何未知路径（比如带了残留 hash 的混合地址）都回报告总览，避免白屏
  { path: '/:pathMatch(.*)*', redirect: '/overview' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const token = localStorage.getItem('ha_token')
  // 登录页与扫码确认页不需要登录态
  if (!token && to.path !== '/login' && to.path !== '/wechat-mock') return '/login'
  if (token && to.path === '/login') return '/overview'
})

export default router
