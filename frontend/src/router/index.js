import { createRouter, createWebHistory } from 'vue-router'
import { auth } from '@/api'
import Login from '@/views/Login.vue'
import Overview from '@/views/Overview.vue'
import Entry from '@/views/Entry.vue'
import Trend from '@/views/Trend.vue'
import History from '@/views/History.vue'
import Chat from '@/views/Chat.vue'
import Settings from '@/views/Settings.vue'
import WechatMock from '@/views/WechatMock.vue'
import StaffWorkspace from '@/views/StaffWorkspace.vue'

export const homeForRole = (role) => role === 'admin' ? '/admin/dashboard' : role === 'doctor' ? '/doctor/dashboard' : '/overview'
const userRoutes = [
  ['/overview', '报告总览', Overview], ['/entry', '录入体检', Entry],
  ['/trend', '指标趋势', Trend], ['/history', '历史档案', History], ['/chat', 'AI 问答', Chat]
].map(([path, title, component]) => ({ path, component, meta: { title, roles: ['user'] } }))
const roleRoutes = (role, sections) => sections.map(([section, title]) => ({
  path: `/${role}/${section}`, component: StaffWorkspace,
  meta: { title, roles: [role], section }
}))
const routes = [
  { path: '/login', component: Login, meta: { public: true } },
  { path: '/wechat-mock', component: WechatMock, meta: { public: true } },
  { path: '/', redirect: '/overview' },
  ...userRoutes,
  ...roleRoutes('doctor', [['dashboard','医生工作台'],['reports','体检报告'],['trends','健康趋势']]),
  ...roleRoutes('admin', [['dashboard','数据维护'],['users','用户管理'],['audit','操作日志']]),
  { path: '/staff', redirect: '/doctor/dashboard' }, // 兼容旧链接，守卫会转到本人工作台
  { path: '/settings', component: Settings, meta: { title: '个人设置', roles: ['user','doctor','admin'] } },
  { path: '/:pathMatch(.*)*', redirect: '/overview' }
]
const router = createRouter({ history: createWebHistory(), routes })
export function resetRoleCache() {}
router.beforeEach(async (to) => {
  const token = localStorage.getItem('ha_token')
  if (to.meta.public) return token && to.path === '/login' ? homeForRole(await getRole(token)) : true
  if (!token) return '/login'
  try {
    const role = await getRole(token)
    if (to.path === '/staff') return homeForRole(role)
    if (to.meta.roles && !to.meta.roles.includes(role)) return homeForRole(role)
    return true
  } catch {
    resetRoleCache()
    localStorage.removeItem('ha_token')
    localStorage.removeItem('ha_user')
    localStorage.removeItem('ha_role')
    return '/login'
  }
})
async function getRole(token) {
  // 每次导航从后端重新确认角色，管理员改角色后下次导航立即生效。
  const profile = await auth.profile()
  return profile.role || 'user'
}
export default router
