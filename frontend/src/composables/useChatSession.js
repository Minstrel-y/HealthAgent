import { ref, watch } from 'vue'

/**
 * ChatBox 共享会话：灵宝面板、AI 问答页、报告概览页三处复用同一个 ChatBox 组件，
 * 通过这个模块级单例共用同一份消息数组，实现「实时同步 + 不互相覆盖」。
 * 按用户名隔离到各自的 localStorage 键，刷新后恢复；不同账号互不串台。
 */
const storageKey = () => `ha_chat_${localStorage.getItem('ha_user') || 'guest'}`

// 模块级单例：所有 ChatBox 实例共享同一个数组引用
const messages = ref([])
let loadedUser = null
let saveTimer = null

function read() {
  const u = localStorage.getItem('ha_user') || 'guest'
  if (u !== loadedUser) {
    loadedUser = u
    try {
      const arr = JSON.parse(localStorage.getItem(storageKey()) || '[]')
      messages.value = (Array.isArray(arr) ? arr : [])
        .filter((m) => m && (m.role === 'user' || m.role === 'ai') && typeof m.content === 'string')
        .map((m) => ({ role: m.role, content: m.content }))
    } catch {
      messages.value = []
    }
  }
  return messages
}

function persist() {
  try {
    // 打字机过程中用 m.full 存完整内容，避免刷新后只剩半句
    localStorage.setItem(
      storageKey(),
      JSON.stringify(messages.value.map((m) => ({ role: m.role, content: m.full || m.content })))
    )
  } catch { /* 隐私模式 / 配额满等异常时静默忽略 */ }
}

let bound = false
export function useChatSession() {
  read()
  if (!bound) {
    bound = true
    // 内容变化后（防抖）落盘
    watch(messages, () => {
      clearTimeout(saveTimer)
      saveTimer = setTimeout(persist, 300)
    }, { deep: true })
    // 页面隐藏/关闭时立即落盘
    window.addEventListener('pagehide', () => { clearTimeout(saveTimer); persist() })
  }
  return { messages, persist }
}
