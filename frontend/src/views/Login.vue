<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-title">康鉴智航</div>
      <div class="login-sub">健康干预 AI 智能体 · 登录</div>

      <el-tabs v-model="tab" stretch @tab-change="onTabChange">
        <!-- 账号密码：角色选择、登录与注册统一交给 RoleLoginPanel -->
        <el-tab-pane label="账号登录" name="account">
          <RoleLoginPanel />
        </el-tab-pane>

        <!-- 微信扫码 -->
        <el-tab-pane label="微信登录" name="wechat">
          <div class="wx-area">
            <div class="qr-box">
              <img v-if="qrImg" :src="qrImg" class="qr-img" alt="微信登录二维码" />
              <el-skeleton v-else animated style="width:160px;height:160px;" />

              <div v-if="qrState === 'expired'" class="qr-mask" @click="refreshQr">
                <span>二维码已过期</span>
                <b>点击刷新</b>
              </div>
              <div v-else-if="qrState === 'scanning'" class="qr-mask soft">
                <span>扫码成功</span>
                <b>正在确认…</b>
              </div>
            </div>

            <div class="wx-tip">
              <template v-if="qrMode === 'wechat'">
                请使用<b> 微信 App </b>扫描二维码登录
              </template>
              <template v-else>
                演示模式：同一 WiFi 下用手机扫二维码会打开确认页；<br />
                在电脑上可直接点下方按钮完成登录
              </template>
            </div>

            <el-button size="small" @click="mockScan" :loading="confirming">模拟扫码确认</el-button>
            <el-button size="small" text @click="refreshQr">刷新二维码</el-button>

            <p class="faint" style="margin-top:10px;">
              真实微信登录需配置微信开放平台密钥（企业认证 + 备案域名），<br />
              未配置时自动切换到演示模式，交互流程完全一致。
            </p>
          </div>
        </el-tab-pane>
      </el-tabs>

      <p style="text-align:center;color:#8a8f98;font-size:12px;margin-top:18px;line-height:1.7;">
        本系统输出仅为健康科普参考<br />不能替代执业医师诊断
      </p>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { resetRoleCache } from '@/router'
import QRCode from 'qrcode'
import { auth } from '@/api'
import { ElMessage } from 'element-plus'
import RoleLoginPanel from '@/components/RoleLoginPanel.vue'

const router = useRouter()
const tab = ref('account')

// ---- 二维码状态 ----
const qrImg = ref('')
const qrMode = ref('')
const qrState = ref('pending')
const qrTicket = ref('')
const confirming = ref(false)
let timer = null

// ------------------------------------------------------------ 微信扫码
const stopPoll = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const refreshQr = async () => {
  stopPoll()
  qrImg.value = ''
  qrState.value = 'pending'
  try {
    const res = await auth.wechatQr()
    qrMode.value = res.mode
    qrTicket.value = res.ticket
    // 二维码内容：演示模式拼成本地确认页地址，真实模式直接用微信授权页
    const content = res.url.startsWith('http')
      ? res.url
      : `${location.origin}${res.url}`
    qrImg.value = await QRCode.toDataURL(content, {
      width: 190,
      margin: 1,
      color: { dark: '#0e7490', light: '#ffffff' }
    })
    startPoll()
  } catch {
    ElMessage.error('二维码获取失败，请检查后端服务')
  }
}

const mockScan = async () => {
  confirming.value = true
  try {
    await auth.wechatConfirm(qrTicket.value)
    qrState.value = 'scanning'
  } catch {
    ElMessage.error('确认失败，请刷新二维码后重试')
  } finally {
    confirming.value = false
  }
}

const startPoll = () => {
  stopPoll()
  timer = setInterval(async () => {
    if (!qrTicket.value) return
    try {
      const s = await auth.wechatPoll(qrTicket.value)
      if (s.status === 'confirmed') {
        stopPoll()
        ElMessage.success('登录成功')
        localStorage.setItem('ha_token', s.access_token)
        localStorage.setItem('ha_user', s.username)
        localStorage.setItem('ha_role', 'user')
        resetRoleCache()
        router.replace('/overview')
      } else if (s.status === 'expired') {
        stopPoll()
        qrState.value = 'expired'
      }
    } catch {
      /* 轮询失败静默重试 */
    }
  }, 1800)
}

const onTabChange = (name) => {
  stopPoll()
  if (name === 'wechat') refreshQr()
}

onBeforeUnmount(stopPoll)
</script>

<style scoped>
.wx-area { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 6px 0 2px; }

.qr-box { position: relative; width: 210px; height: 210px; display: grid; place-items: center;
          background: #fff; border: 1px solid var(--line); border-radius: var(--r-lg); box-shadow: var(--sh-xs); }
.qr-img { width: 190px; height: 190px; display: block; }
.qr-mask {
  position: absolute; inset: 0; display: flex; flex-direction: column; gap: 4px;
  align-items: center; justify-content: center; cursor: pointer;
  background: rgba(255, 255, 255, .94); color: var(--ink); font-size: 13px; border-radius: var(--r-lg);
}
.qr-mask b { color: var(--brand); font-size: 14px; }
.qr-mask.soft { background: rgba(255, 255, 255, .82); }

.wx-tip { font-size: 12.5px; color: var(--sub); text-align: center; line-height: 1.7; }
.wx-tip b { color: var(--ok); }
</style>
