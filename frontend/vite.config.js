import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] })
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') }
  },
  // three 不走依赖预构建：本机安全策略会拦截 esbuild 打包时的临时文件操作，
  // 直接以原生 ESM 加载 three.module.js 更稳。正常环境可删掉这段以获得更快冷启动。
  optimizeDeps: {
    exclude: ['three']
  },
  // minify: false —— 本机的安全策略会拦截 esbuild 压缩阶段产生的临时文件，
  // 关掉压缩不影响功能；若在正常环境，可改成 'esbuild' 以获得更小体积。
  build: {
    minify: false,
    cssMinify: false,
    // esnext：现代浏览器直接跑，vite 会跳过 esbuild 转译步骤，
    // 从而不再产生/删除临时文件（本机安全策略会拦截 unlink 导致 build 失败）。
    target: 'esnext',
    // 本机安全策略会拦截清空 dist 的删除/复制操作导致 build 失败：
    // - emptyOutDir: false → 直接覆盖写 index.html 与 assets（旧哈希文件残留无妨）
    // - copyPublicDir: false → public/（models 等大文件）不重复拷贝，dist 里已有
    emptyOutDir: false,
    copyPublicDir: false,
    chunkSizeWarningLimit: 1500
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // 后端端口不固定时：VITE_API_TARGET=http://127.0.0.1:8123 npm run dev
      '/api': { target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})
