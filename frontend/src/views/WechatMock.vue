<!--
  演示模式专用：手机扫码后打开的确认页。
  真实模式下这一步由微信 App 完成，不会用到本页面。
-->
<template>
  <div class="mock-wrap">
    <div class="mock-card">
      <div class="wx-logo">💬</div>
      <div class="mock-title">康鉴智航·网页版</div>
      <div class="mock-sub">请在手机上确认是否登录</div>

      <el-button type="primary" size="large" style="width:100%;margin-top:18px;"
                 :loading="loading" :disabled="!ticket" @click="confirm">
        确认登录
      </el-button>
      <el-button size="large" style="width:100%;margin:10px 0 0;" @click="cancel">取消</el-button>

      <p class="faint" style="margin-top:16px;text-align:center;">
        这是演示模式的模拟确认环节。<br />
        配置真实微信密钥后，此步骤由微信客户端完成。
      </p>
      <p v-if="msg" :class="ok ? 'ok-text' : 'faint'" style="text-align:center;margin-top:10px;">{{ msg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { auth } from '@/api'

const route = useRoute()
const ticket = route.query.ticket || ''
const loading = ref(false)
const msg = ref('')
const ok = ref(false)

const confirm = async () => {
  loading.value = true
  try {
    await auth.wechatConfirm(ticket)
    ok.value = true
    msg.value = '已确认，回到电脑端即可自动登录'
  } catch {
    ok.value = false
    msg.value = '二维码已失效，请在电脑上刷新后重新扫码'
  } finally {
    loading.value = false
  }
}

const cancel = () => {
  msg.value = '已取消，可以关闭此页面'
}
</script>

<style scoped>
.mock-wrap { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: var(--canvas); }
.mock-card {
  width: 340px; max-width: 100%;
  background: #fff; border: 1px solid var(--line); border-radius: var(--r-xl);
  padding: 32px 24px 24px; text-align: center; box-shadow: var(--sh-lg);
}
.wx-logo {
  width: 56px; height: 56px; margin: 0 auto 14px; border-radius: 16px;
  display: grid; place-items: center; font-size: 26px;
  background: linear-gradient(140deg, #07c160, #06ad56); color: #fff;
}
.mock-title { font-size: 17px; font-weight: 700; color: var(--ink); }
.mock-sub { font-size: 13px; color: var(--sub); margin-top: 6px; }
.ok-text { color: var(--ok); font-size: 13px; }
</style>
