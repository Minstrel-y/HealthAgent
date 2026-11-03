import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './styles/main.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')

// Safari 的 bfcache 会在前进/后退时恢复冻结的页面，常表现为"点开就白屏"。
// 检测到从缓存恢复的页面时强制刷新一次，保证 JS 状态与路由一致。
window.addEventListener('pageshow', (e) => {
  if (e.persisted) location.reload()
})

// 全局错误兜底：组件渲染出错时至少把错误打到控制台并提示，而不是整块视图悄悄消失
app.config.errorHandler = (err, _inst, info) => {
  console.error('[GlobalError]', info, err)
}
