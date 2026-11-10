<template>
  <div class="chatbox" :style="{ height: height }">
    <!-- 顶部小标题栏 -->
    <div class="chat-head">
      <span class="avatar ai">AI</span>
      <div style="line-height:1.25;">
        <b style="font-size:14px;color:var(--ink);">康鉴智航 · 健康助手</b>
        <div class="faint" style="font-size:11.5px;">
          {{ recordId ? '已结合你最近一次体检报告' : '通用健康科普模式' }}
        </div>
      </div>
      <div style="margin-left:auto;display:flex;gap:6px;">
        <el-button size="small" text :disabled="!messages.length || busy" @click="clearAll">清空</el-button>
      </div>
    </div>

    <!-- 消息滚动区 -->
    <div ref="boxRef" class="chat-body">
      <!-- 空态 -->
      <div v-if="!messages.length && !busy" class="chat-empty">
        <div class="empty-icon">💬</div>
        <b style="color:var(--ink);font-size:15px;">有什么健康问题想问？</b>
        <div class="muted" style="margin-top:6px;">可以直接输入，也可以点下面的快捷问题</div>
        <div class="quick-wrap">
          <button v-for="q in quick" :key="q" class="quick" @click="send(q)">{{ q }}</button>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
        <span class="avatar" :class="m.role === 'user' ? 'me' : 'ai'">{{ m.role === 'user' ? '我' : 'AI' }}</span>
        <div class="bubble-wrap">
          <div class="bubble">
            <div class="md" v-html="renderMarkdown(m.content)"></div><span v-if="m.typing" class="caret"></span>
          </div>
          <div class="bubble-ops">
            <span class="faint">{{ m.role === 'user' ? '我' : 'AI 助手' }}</span>
            <el-button v-if="m.role === 'ai' && !m.typing" size="small" text @click="copy(m.content)">复制</el-button>
          </div>
        </div>
      </div>

      <!-- 思考中 -->
      <div v-if="busy && !messages.some((m) => m.typing)" class="msg-row ai">
        <span class="avatar ai">AI</span>
        <div class="bubble-wrap">
          <div class="bubble thinking">
            正在分析你的问题
            <span class="dots"><i></i><i></i><i></i></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-foot">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        :autosize="{ minRows: 2, maxRows: 5 }"
        resize="none"
        maxlength="500"
        show-word-limit
        :placeholder="placeholder"
        @keydown.enter.exact.prevent="send()"
      />
      <div class="foot-row">
        <span class="faint">Enter 发送 · Shift + Enter 换行</span>
        <div style="display:flex;gap:8px;align-items:center;">
          <el-button size="small" text :disabled="busy || !input.trim()" @click="input = ''">清空输入</el-button>
          <el-button size="small" type="primary" :loading="busy" :disabled="!input.trim()" @click="send()">
            发送
          </el-button>
        </div>
      </div>
      <p class="faint" style="margin:8px 0 0;">回答仅为健康科普参考，不能替代执业医师诊断；如有明显异常请及时就医。</p>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { api } from '@/api'
import { useChatSession } from '@/composables/useChatSession'

const props = defineProps({
  recordId: { type: [Number, String], default: null },
  height: { type: String, default: '560px' },
  placeholder: { type: String, default: '例如：我的尿酸升高是什么原因？' },
  quick: {
    type: Array,
    default: () => ['我的异常指标怎么改善？', '这些异常严重吗？', '饮食上要注意什么？', '多久后复查合适？']
  }
})

// 共享会话：所有 ChatBox 实例（灵宝面板 / AI 问答页 / 报告概览页）共用同一份消息，实时同步
const { messages, persist } = useChatSession()

const input = ref('')
const busy = ref(false)
const boxRef = ref(null)
let timer = null

// 恢复历史后直接滚到最新一条
onMounted(() => {
  if (messages.value.length) scrollBottom()
})

// Markdown 渲染：把模型返回的 Markdown 转成 HTML，再经 DOMPurify 消毒防止 XSS
const renderMarkdown = (s) => DOMPurify.sanitize(marked.parse(s || '', { gfm: true, breaks: true }))

const scrollBottom = async () => {
  await nextTick()
  const el = boxRef.value
  if (el) el.scrollTop = el.scrollHeight
}

// 打字机效果：后端是整段返回，前端逐字渲染出"模型输出"的观感
const typeOut = (msg, full) => {
  clearInterval(timer)
  let i = 0
  const step = Math.max(1, Math.ceil(full.length / 320)) // 长短回答耗时一致，约 3 秒内打完
  timer = setInterval(() => {
    i += step
    if (i >= full.length) {
      msg.content = full
      msg.typing = false
      clearInterval(timer)
      timer = null
      busy.value = false
    } else {
      msg.content = full.slice(0, i)
    }
    const el = boxRef.value
    if (el) el.scrollTop = el.scrollHeight
  }, 16)
}

const finishTyping = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
    const m = messages.value.find((x) => x.typing)
    if (m) { m.typing = false; m.content = m.full || m.content }
    busy.value = false
  }
}

const send = async (q) => {
  const text = (typeof q === 'string' ? q : input.value).trim()
  if (!text) return
  finishTyping()

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  busy.value = true
  await scrollBottom()

  const ai = { role: 'ai', content: '', typing: true, full: '' }
  messages.value.push(ai)
  await scrollBottom()

  try {
    const res = await api.chat(text, props.recordId)
    ai.full = res.answer || '（暂无回答）'
    typeOut(ai, ai.full)
  } catch {
    // 失败时移除用户那条与占位气泡，并给出提示
    const idx = messages.value.findIndex((x) => x === ai)
    if (idx > -1) messages.value.splice(idx, 1)
    messages.value.pop()
    busy.value = false
    ElMessage.error('提问失败，通常是额度限流，稍等约 1 分钟再试一次')
  }
}

const copy = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制回答')
  } catch {
    ElMessage.warning('当前浏览器不支持一键复制，请手动选择文本')
  }
}

const clearAll = () => {
  finishTyping()
  messages.value = []
}

onBeforeUnmount(() => {
  clearInterval(timer)
  persist()
})

defineExpose({ send })
</script>

<style scoped>
.chatbox {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  overflow: hidden;
  box-shadow: var(--sh-xs);
}

/* 顶部 */
.chat-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, #fbfdfe, #fff);
}

.avatar {
  width: 30px;
  height: 30px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
}
.avatar.ai { background: linear-gradient(140deg, var(--brand), var(--accent)); color: #fff; }
.avatar.me { background: #eef2f7; color: var(--sub); }

/* 消息区 */
.chat-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 18px 16px 8px;
  background:
    radial-gradient(600px 200px at 100% 0%, rgba(14, 116, 144, .05), transparent 60%),
    #fbfdfe;
  scroll-behavior: smooth;
}

.chat-empty { text-align: center; padding: 28px 10px; }
.empty-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 22px;
  background: var(--brand-soft);
}
.quick-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
}
.quick {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--text);
  font: inherit;
  font-size: 13px;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all .16s ease;
}
.quick:hover { border-color: var(--brand); color: var(--brand); background: var(--brand-soft); }

.msg-row { display: flex; gap: 10px; margin-bottom: 16px; }
.msg-row.user { flex-direction: row-reverse; }

.bubble-wrap { min-width: 0; max-width: 78%; }
.msg-row.user .bubble-wrap { display: flex; flex-direction: column; align-items: flex-end; }

.bubble {
  word-break: break-word;
  line-height: 1.75;
  font-size: 14px;
  padding: 10px 14px;
  border-radius: 14px;
}
.msg-row.user .bubble {
  white-space: pre-wrap;
  background: linear-gradient(140deg, var(--brand), #0b5d75);
  color: #fff;
  border-top-right-radius: 6px;
}
.msg-row.ai .bubble {
  background: #fff;
  border: 1px solid var(--line);
  border-top-left-radius: 6px;
  color: var(--text);
  box-shadow: var(--sh-xs);
}

.bubble-ops {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 11.5px;
  color: var(--faint);
  height: 20px;
}

/* Markdown 内容样式（v-html 注入的内容不会被 scoped 标记，需用 :deep） */
.bubble :deep(.md) { white-space: normal; }
.bubble :deep(.md > :first-child) { margin-top: 0; }
.bubble :deep(.md > :last-child) { margin-bottom: 0; }
.bubble :deep(.md p) { margin: 0 0 8px; }
.bubble :deep(.md h1),
.bubble :deep(.md h2),
.bubble :deep(.md h3),
.bubble :deep(.md h4) {
  margin: 14px 0 6px;
  line-height: 1.4;
  font-weight: 700;
  color: var(--ink);
}
.bubble :deep(.md h1) { font-size: 18px; }
.bubble :deep(.md h2) { font-size: 16px; }
.bubble :deep(.md h3) { font-size: 15px; }
.bubble :deep(.md h4) { font-size: 14px; }
.bubble :deep(.md ul),
.bubble :deep(.md ol) {
  margin: 6px 0;
  padding-left: 20px;
}
.bubble :deep(.md li) { margin: 3px 0; }
.bubble :deep(.md strong) { font-weight: 700; color: var(--ink); }
.bubble :deep(.md em) { font-style: italic; }
.bubble :deep(.md a) { color: var(--brand); text-decoration: none; }
.bubble :deep(.md a:hover) { text-decoration: underline; }
.bubble :deep(.md code) {
  background: #f0f4f8;
  color: #0f172a;
  padding: 2px 5px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
}
.bubble :deep(.md pre) {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  line-height: 1.5;
}
.bubble :deep(.md pre code) { background: transparent; color: inherit; padding: 0; font-size: 13px; }
.bubble :deep(.md blockquote) {
  border-left: 3px solid var(--brand);
  padding-left: 10px;
  margin: 8px 0;
  color: var(--sub);
}
.bubble :deep(.md hr) { border: none; border-top: 1px solid var(--line); margin: 10px 0; }
.bubble :deep(.md table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
  font-size: 13px;
}
.bubble :deep(.md th),
.bubble :deep(.md td) {
  border: 1px solid var(--line);
  padding: 6px 8px;
  text-align: left;
}
.bubble :deep(.md th) { background: #f6f8fa; font-weight: 700; }

/* 打字光标 */
.caret {
  display: inline-block;
  width: 2px;
  height: 15px;
  margin-left: 2px;
  vertical-align: -2px;
  background: var(--brand);
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

.thinking { color: var(--sub); }
.dots { display: inline-flex; gap: 3px; margin-left: 4px; }
.dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--brand);
  animation: jump 1.2s infinite;
}
.dots i:nth-child(2) { animation-delay: .2s; }
.dots i:nth-child(3) { animation-delay: .4s; }
@keyframes jump {
  0%, 60%, 100% { transform: translateY(0); opacity: .35; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* 输入区 */
.chat-foot {
  border-top: 1px solid var(--line);
  padding: 12px 16px;
  background: #fff;
}
.foot-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}

@media (max-width: 640px) {
  .bubble-wrap { max-width: 88%; }
}
</style>
