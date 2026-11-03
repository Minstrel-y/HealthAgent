<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        <span class="brand-mark">🩺</span>
        <span class="brand-text">
          <b>康鉴智航</b>
          <span>健康干预 AI 智能体</span>
        </span>
      </div>

      <div class="user-chip">
        <router-link to="/settings" class="user-link" title="个人设置">
          <span class="user-avatar">
            <img v-if="profile.avatar && profile.avatar.startsWith('/uploads')" :src="profile.avatar" alt="头像" />
            <span v-else-if="profile.avatar">{{ profile.avatar }}</span>
            <span v-else>{{ initial }}</span>
          </span>
          <span style="line-height:1.2;">
            <span style="display:block;font-size:13px;font-weight:600;color:var(--ink);">{{ displayName }}</span>
            <span class="faint">个人设置</span>
          </span>
        </router-link>
        <el-button text bg size="small" @click="logout">退出</el-button>
      </div>
    </header>

    <div class="app-body">
      <nav class="app-nav" :class="{ collapsed }">
        <router-link
          v-for="item in menus"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
          :title="item.title"
        >
          <span class="nav-ico">{{ item.icon }}</span>
          <span class="nav-txt">{{ item.title }}</span>
        </router-link>
        <button class="nav-toggle" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="toggleNav">
          {{ collapsed ? '»' : '«' }}
        </button>
      </nav>

      <main class="app-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth } from '@/api'

const route = useRoute()
const router = useRouter()
const username = localStorage.getItem('ha_user') || ''
const profile = ref({ avatar: '', nickname: '', font_scale: 1 })

const initial = computed(() => (profile.value.nickname || username || 'U').slice(0, 1).toUpperCase())
const displayName = computed(() => profile.value.nickname || username)

const menus = [
  { path: '/overview', title: '报告总览', icon: '◲' },
  { path: '/entry', title: '录入体检', icon: '✎' },
  { path: '/trend', title: '指标趋势', icon: '◹' },
  { path: '/history', title: '历史档案', icon: '▤' },
  { path: '/chat', title: 'AI 问答', icon: '◍' },
  { path: '/settings', title: '个人设置', icon: '⚙' }
]

// 字号偏好：本地缓存先生效（避免刷新时闪一下），再向服务端取最新
const applyFont = (scale) => {
  document.documentElement.style.setProperty('--font-scale', String(scale || 1))
}

const loadProfile = async () => {
  // 未登录（在登录/注册页）时不要发请求：否则 401 会触发跳转逻辑
  if (!localStorage.getItem('ha_token')) return
  const cached = Number(localStorage.getItem('ha_font_scale'))
  if (cached) applyFont(cached)
  try {
    const p = await auth.profile()
    profile.value = p
    applyFont(p.font_scale)
    localStorage.setItem('ha_font_scale', String(p.font_scale || 1))
  } catch {
    /* 未登录或接口异常时保持默认字号 */
  }
}

// 侧栏可收起：收起后只剩图标条，把宽度全部让给右侧内容区
const collapsed = ref(localStorage.getItem('ha_nav_collapsed') === '1')
const toggleNav = () => {
  collapsed.value = !collapsed.value
  localStorage.setItem('ha_nav_collapsed', collapsed.value ? '1' : '0')
}

const logout = () => {
  localStorage.removeItem('ha_token')
  localStorage.removeItem('ha_user')
  localStorage.removeItem('ha_font_scale')
  router.replace('/login')
}

onMounted(loadProfile)
</script>

<style scoped>
.user-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
  transition: background .16s ease;
}
.user-link:hover { background: var(--brand-soft); }

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--brand);
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 14px;
  overflow: hidden;
  flex: none;
}
.user-avatar img { width: 100%; height: 100%; object-fit: cover; }
</style>
