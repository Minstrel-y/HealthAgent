<template>
  <div class="lingbao">
    <!-- 提示气泡：云朵上方轮播 -->
    <transition name="bubble">
      <div v-if="bubbleVisible && !panelOpen" class="tip-bubble" @click="togglePanel">
        <span class="tip-text">{{ currentTip }}</span>
        <span class="tip-icon">问</span>
      </div>
    </transition>

    <!-- 问答面板：直接复用现成 ChatBox 组件，零重复代码 -->
    <transition name="panel">
      <div v-if="panelOpen" class="chat-panel">
        <header class="panel-head">
          <div class="panel-who">
            <LingbaoCloud :size="30" />
            <div>
              <b>灵宝</b>
              <span class="faint">你的健康小助手</span>
            </div>
          </div>
          <el-button text size="small" @click="panelOpen = false">收起</el-button>
        </header>

        <div class="panel-box">
          <ChatBox
            height="100%"
            placeholder="问灵宝，例如：我的尿酸升高要注意什么？"
            :quick="quickQuestions"
          />
        </div>

        <p class="panel-note faint">与「AI 问答」页共用对话 · 回答仅为科普参考</p>
      </div>
    </transition>

    <!-- 云朵本体 -->
    <button class="cloud-btn" :class="{ talking: bubbleVisible && !panelOpen }" @click="togglePanel">
      <LingbaoCloud :size="86" :glow="true" />
      <span v-if="!panelOpen && unread" class="badge">1</span>
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '@/api'
import LingbaoCloud from './LingbaoCloud.vue'
import ChatBox from './ChatBox.vue'

const panelOpen = ref(false)
const bubbleVisible = ref(false)
const tipIndex = ref(0)
const unread = ref(true)
const tips = ref([])

const quickQuestions = [
  '我这次体检有什么问题？',
  '尿酸高平时要注意什么？',
  '饮食上要注意什么？'
]

const currentTip = computed(() => {
  const list = tips.value
  if (!list.length) return '点我，聊聊你的体检报告'
  return list[tipIndex.value % list.length]
})

/** 通用提醒 + 按异常指标定制的提醒（用 insights 接口，比 overview 更可靠） */
async function buildTips() {
  const generic = [
    '久坐一小时了，起来走两步吧',
    '记得喝水，今天喝够 1500ml 了吗',
    '眼睛累了就望望远处，放松 20 秒',
    '该活动一下了，伸个懒腰也算',
    '晚上别熬太晚，睡眠也是治疗'
  ]
  try {
    const data = await api.insights()
    const keys = (data?.items || []).map((it) => it.key)
    const custom = []
    if (keys.includes('uric_acid')) custom.push('尿酸偏高，今天多喝两杯水帮助排出')
    if (keys.some((k) => ['tg', 'tc', 'ldl'].includes(k))) custom.push('血脂偏高，今天少吃点油炸和肥肉吧')
    if (keys.includes('fast_glucose')) custom.push('血糖偏高，含糖饮料今天就别喝了')
    if (keys.some((k) => ['alt', 'ast'].includes(k))) custom.push('转氨酶偏高，最近别喝酒、早点睡')
    if (keys.includes('bmi')) custom.push('体重超标一点点，每天走 6000 步就能改善')
    tips.value = custom.length ? [...custom, ...generic] : generic
  } catch {
    tips.value = generic
  }
}

let tipTimer = null
let showTimer = null
function startRotate() {
  showTimer = setTimeout(() => { bubbleVisible.value = true }, 2500)
  tipTimer = setInterval(() => {
    if (panelOpen.value) return
    tipIndex.value = (tipIndex.value + 1) % Math.max(1, tips.value.length)
    bubbleVisible.value = true
  }, 9000)
}

function togglePanel() {
  panelOpen.value = !panelOpen.value
  if (panelOpen.value) {
    bubbleVisible.value = false
    unread.value = false
  }
}

onMounted(async () => {
  await buildTips()
  startRotate()
})

onBeforeUnmount(() => {
  clearTimeout(showTimer)
  clearInterval(tipTimer)
})
</script>

<style scoped>
.lingbao {
  position: fixed;
  right: 26px;
  bottom: 26px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

/* ---------- 云朵按钮 ---------- */
.cloud-btn {
  position: relative;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  transition: transform 0.22s ease;
  filter: drop-shadow(0 12px 26px rgba(120, 160, 200, 0.28));
}
.cloud-btn:hover { transform: translateY(-4px) scale(1.03); }
.cloud-btn.talking { animation: bob 2.6s ease-in-out infinite; }
@keyframes bob {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}
.badge {
  position: absolute;
  top: 6px;
  right: 2px;
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  background: #f87171;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  border: 2px solid #fff;
}

/* ---------- 提示气泡 ---------- */
.tip-bubble {
  max-width: 232px;
  background: #fff;
  border: 1px solid #e6eef7;
  border-radius: 16px;
  padding: 11px 14px;
  box-shadow: 0 10px 28px rgba(120, 150, 190, 0.22);
  display: flex;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
  position: relative;
}
.tip-bubble::after {
  content: '';
  position: absolute;
  right: 30px;
  bottom: -7px;
  width: 12px;
  height: 12px;
  background: #fff;
  border-right: 1px solid #e6eef7;
  border-bottom: 1px solid #e6eef7;
  transform: rotate(45deg);
}
.tip-text { font-size: 13px; line-height: 1.7; color: #334155; }
.tip-icon {
  font-size: 11px;
  line-height: 1.7;
  background: var(--brand-soft);
  color: var(--brand);
  border-radius: 6px;
  padding: 0 6px;
  flex: none;
}

/* ---------- 问答面板 ---------- */
.chat-panel {
  width: 364px;
  height: 560px;
  background: #fff;
  border: 1px solid #e6eef7;
  border-radius: 20px;
  box-shadow: 0 22px 48px rgba(100, 130, 170, 0.24);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: linear-gradient(120deg, #f2f9ff, #f7fbff);
  border-bottom: 1px solid #eaf2fb;
}
.panel-who { display: flex; align-items: center; gap: 8px; }
.panel-who b { font-size: 13.5px; color: var(--ink); display: block; line-height: 1.2; }
.panel-who .faint { font-size: 10.5px; }
.panel-box { flex: 1; min-height: 0; }
.panel-note {
  margin: 0;
  padding: 8px 12px;
  font-size: 10.5px;
  text-align: center;
  color: var(--faint);
  border-top: 1px solid #f0f5fb;
}

/* ---------- 动画 ---------- */
.bubble-enter-active, .bubble-leave-active { transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1); }
.bubble-enter-from, .bubble-leave-to { opacity: 0; transform: translateY(8px) scale(0.94); }
.panel-enter-active, .panel-leave-active { transition: all 0.24s cubic-bezier(0.16, 1, 0.3, 1); }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(14px) scale(0.96); }

@media (max-width: 768px) {
  .lingbao { right: 14px; bottom: 14px; }
  .chat-panel { width: calc(100vw - 28px); height: 70vh; }
  .tip-bubble { max-width: 200px; }
}
</style>
