<template>
  <section class="role-auth" aria-label="角色登录注册">
    <div class="role-label">请选择身份</div>
    <el-radio-group v-model="role" class="role-options" size="large">
      <el-radio-button label="user" value="user">普通用户</el-radio-button>
      <el-radio-button label="doctor" value="doctor">医生</el-radio-button>
      <el-radio-button label="admin" value="admin">管理员</el-radio-button>
    </el-radio-group>

    <el-tabs v-model="mode" stretch class="mode-tabs">
      <el-tab-pane label="登录" name="login" />
      <el-tab-pane label="注册" name="register" />
    </el-tabs>
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="账号">
        <el-input v-model.trim="username" autocomplete="username" placeholder="输入账号" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="password" type="password" show-password
                  :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
                  placeholder="输入密码" />
      </el-form-item>
      <el-alert v-if="role !== 'user' && mode === 'register'" type="warning"
                :closable="false" show-icon
                title="开发演示账号：医生与管理员身份尚未经过资质审核，不得部署到公网。" />
      <el-button type="primary" native-type="submit" :loading="loading" class="submit-btn">
        {{ mode === 'login' ? '登录' : '注册' }}{{ roleName }}
      </el-button>
    </el-form>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { resetRoleCache, homeForRole } from '@/router'
import { ElMessage } from 'element-plus'
import { auth } from '../api/index.js'

const router = useRouter()
const role = ref('user')
const mode = ref('login')
const username = ref('')
const password = ref('')
const loading = ref(false)
const roleName = computed(() => ({ user: '普通用户', doctor: '医生', admin: '管理员' })[role.value])

async function submit() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    let data
    if (mode.value === 'register') {
      await auth.register(username.value, password.value, role.value)
      // 即使注册端已经返回 token，也重新走带角色校验的登录接口。
    }
    data = await auth.login(username.value, password.value, role.value)
    const token = data?.access_token
    if (!token) throw new Error('登录接口没有返回 access_token')
    localStorage.setItem('ha_token', token)

    // 权限以服务端数据库为准，不能仅依赖角色按钮或本地存储。
    const profile = await auth.profile()
    const serverRole = profile?.role ?? profile?.profile?.role
    if (serverRole !== role.value) {
      localStorage.removeItem('ha_token')
      throw new Error('所选身份与账号角色不匹配，请核对角色')
    }
    localStorage.setItem('ha_user', username.value)
    localStorage.setItem('ha_role', serverRole)
    resetRoleCache()
    ElMessage.success('登录成功')
    await router.replace(homeForRole(serverRole))
  } catch (error) {
    ElMessage.error(error?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.role-auth { width: 100%; }
.role-label { margin: 10px 0 8px; font-weight: 600; font-size: 13px; }
.role-options { display: flex; width: 100%; }
.role-options :deep(.el-radio-button) { flex: 1; }
.role-options :deep(.el-radio-button__inner) { width: 100%; padding-left: 4px; padding-right: 4px; }
.mode-tabs { margin-top: 14px; }
.submit-btn { width: 100%; margin-top: 14px; }
</style>
