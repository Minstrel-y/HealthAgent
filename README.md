# 康鉴智航 HealthAgent｜Vue3 + FastAPI 版

面向个人的体检报告 AI 智能体：上传体检报告 / 粘贴原文 / 手动填写，自动解析指标、本地判读、生成健康得分与 AI 解读，并提供趋势跟踪、诱因与关联疾病分析、健康问答。

**核心原则：数值判读全部本地计算，大模型只负责"解读与建议"。** 参考区间、异常判定、健康得分、诱因/关联疾病推断都由确定性规则本地得出，模型不参与判读，杜绝编造数值。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Pinia + vue-router + axios |
| 后端 | FastAPI + Uvicorn + SQLite + PyJWT |
| 大模型 | 阿里云百炼 DashScope（`qwen-plus → qwen-turbo → qwen-max` 回退；视觉 `qwen3-vl-plus` 等） |

## 目录结构

```
HealthAgent/
├── start_dev.sh              一键启动（后端 8000 + 前端 5173）
├── docs/                     截图与测试产物
├── backend/
│   ├── main.py               FastAPI 入口（同时托管前端构建产物）
│   ├── config.py             配置：密钥、模型候选、路径、微信登录
│   ├── db.py                 SQLite 数据层（用户 / 记录 / 微信会话）
│   ├── auth.py               JWT 签发与校验
│   ├── schemas.py            Pydantic 请求 / 响应模型
│   ├── refs.py               参考区间 + 健康得分（本地算）
│   ├── rules.py              诱因 / 关联疾病规则库（本地算）
│   ├── parser.py             体检文本本地解析（降级用）
│   ├── llm.py                大模型层（所有 DashScope 调用集中在此）
│   ├── routers/
│   │   ├── auth_router.py        注册 / 登录 / 微信扫码 / 个人资料 / 头像
│   │   ├── records_router.py     解析 / 记录读写 / 总览 / 趋势
│   │   ├── analysis_router.py    趋势三段分析 / 健康问答
│   │   └── insight_router.py     规则库查询 / 诱因推断
│   ├── requirements.txt
│   ├── .env                 DASHSCOPE_API_KEY / JWT_SECRET（勿提交）
│   ├── health.db            SQLite 数据库（运行后自动生成）
│   └── uploads/avatars/     用户头像（通过 /uploads 访问）
└── frontend/
    ├── index.html
    ├── vite.config.js       /api 代理、构建策略（详见文件注释）
    ├── package.json
    ├── public/models/       2D 人体图 body_render.png、3D 模型 xbot.glb
    └── src/
        ├── main.js  App.vue        应用入口 + 全局外壳（侧栏 / 头像 / 字号）
        ├── api/index.js            axios 封装 + 拦截器（自动带 token）
        ├── router/index.js         路由 + 登录守卫
        ├── styles/main.css         设计系统（CSS 变量、深色主题）
        ├── components/
        │   ├── BodyMap2D.vue       2D 全息人体图（百分比坐标光点）
        │   ├── BodyModel.vue       3D 人体模型（THREE.js，可选）
        │   ├── ChatBox.vue         AI 问答对话组件
        │   └── InsightPanel.vue    诱因 / 关联疾病分析面板
        └── views/
            ├── Login.vue           登录（账号密码 + 微信扫码）
            ├── WechatMock.vue      微信演示模式扫码确认页
            ├── Overview.vue        报告总览（人体图 + 指标 + AI 报告）
            ├── Entry.vue           录入体检（上传 / 粘贴 / 手动）
            ├── Trend.vue           指标趋势 + 三段分析
            ├── History.vue         历史档案（列表 + 详情）
            ├── Chat.vue            AI 问答页
            └── Settings.vue        个人设置（头像 / 字号 / 性别生日）
```

## 设计原则

- **判读与规则本地算，模型只解读。** `refs.py`（34 项指标参考区间、健康得分、异常统计）与 `rules.py`（21 项指标的诱因、关联疾病、复查建议、生活干预）全部是静态确定性逻辑，响应毫秒级、结果可复现，不烧 token。
- **三源平级录入。** 上传文件 / 粘贴原文 / 手动填写产出同一套 `metrics`，命中任一即可出报告，没做的项目不强填。
- **模型降级兜底。** 文本抽取走模型失败时自动降级本地正则（`parser.py`）；报告生成失败仍保留记录，可事后补生成。
- **指标库驱动。** 录入表单、解析、判读链路跟随 `refs.METRICS` / `rules.RULES` 自动扩展，新增指标无需改前端表单结构。

## 快速开始

### 一键启动（推荐）

```bash
./start_dev.sh                 # 后端 127.0.0.1:8000 + 前端 127.0.0.1:5173
BACKEND_PORT=8123 ./start_dev.sh   # 8000 被占用时换端口，前端代理自动跟随
```

脚本会优先使用项目自带 `backend/.venv`，自动处理 Vite 依赖缓存（本机安全策略会拦截删除操作，改为改名移走）。

### 手动启动后端

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

接口文档：http://127.0.0.1:8000/docs

`backend/.env` 需配置：

```env
DASHSCOPE_API_KEY = "你的阿里云百炼 Key"
JWT_SECRET = "随便一串随机字符串"
```

### 手动启动前端（开发模式）

```bash
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

Vite 已把 `/api` 代理到 `http://127.0.0.1:8000`，前后端分开跑时无需处理跨域。

### 生产模式（单端口）

```bash
cd frontend && npm run build        # 产出 frontend/dist
cd ../backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

构建产物存在时 FastAPI 直接托管 SPA，`http://<地址>/` 即完整应用，不再需要 Vite（首页强制 `no-store` 禁止缓存）。

## 微信扫码登录

默认运行在**演示模式**：未配置微信开放平台密钥时，扫码后打开本地确认页（或直接点「模拟扫码」）即可完成登录，交互与真实模式一致。

接入真实微信扫码需在 `backend/.env` 补充（需微信开放平台「网站应用」企业资质）：

```env
WECHAT_APPID = "..."
WECHAT_SECRET = "..."
WECHAT_REDIRECT_URI = "..."      # 需与开放平台回调域名白名单一致
WECHAT_DEMO = ""                 # 填 1 强制演示模式
PUBLIC_BASE_URL = "http://127.0.0.1:8124"
```

流程：`GET /auth/wechat/qr` 出二维码 → 前端 `GET /auth/wechat/poll` 轮询票据 → 扫码后回调 `GET /auth/wechat/callback` 换 openid 建号 → 前端拿到 token。

## 接口一览

### 认证 / 用户（`/api/auth`）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册并返回 token |
| POST | `/auth/login` | 登录并返回 token |
| GET | `/auth/me` | 当前用户（含资料） |
| GET | `/auth/profile` | 个人资料 |
| PUT | `/auth/profile` | 更新资料（昵称 / 性别 / 生日 / 字号） |
| POST | `/auth/avatar` | 上传头像（≤3MB 图片） |
| GET | `/auth/wechat/qr` | 微信扫码二维码 + 票据 |
| GET | `/auth/wechat/poll` | 轮询扫码状态，确认后返回 token |
| POST | `/auth/wechat/confirm` | 确认扫码（演示 / 回调） |
| GET | `/auth/wechat/callback` | 微信开放平台回调 |

### 记录 / 解析 / 总览（`/api`）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/parse/text` | 粘贴体检原文 → 指标（模型优先，降级本地正则） |
| POST | `/parse/file` | 上传图片 / PDF → 指标（视觉模型 OCR） |
| POST | `/records` | 保存记录并生成 AI 报告 |
| GET | `/records` | 记录列表（含得分 / 风险等级） |
| GET | `/records/{id}` | 单条记录详情 |
| POST | `/records/{id}/report` | 补生成 AI 解读 |
| PUT | `/records/{id}` | 修改指标并重新生成解读 |
| DELETE | `/records/{id}` | 删除记录 |
| GET | `/overview` | 总览：指标 + 判读 + 得分 + 报告 + 对比上次 |
| GET | `/trend` | 得分与各指标序列（纯本地） |

### 分析 / 规则（`/api`）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/trend/analysis` | 趋势三段分析（走模型） |
| POST | `/chat` | 健康问答（结合最近报告，可指定记录） |
| GET | `/rules/metrics` | 指标库清单（名称 / 单位 / 参考区间） |
| GET | `/rules/{key}` | 某指标完整规则（诱因 / 关联疾病 / 复查 / 干预） |
| GET | `/rules/insights/latest` | 最近记录的诱因推断与交叉结论（纯本地） |

### 系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查（返回 key 配置 / 前端构建状态） |

## 常见启动问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 前端页面打不开 / 502 | Vite 依赖缓存损坏 | 重启 `npm run dev`（`start_dev.sh` 已自动改名移走旧缓存） |
| 页面空白，控制台报 three 加载失败 | `three` 预构建异常 | `vite.config.js` 已 `optimizeDeps.exclude: ['three']` 走原生 ESM |
| 后端启动报 `disk I/O error` | 数据库目录不可写 | 确认 `backend/` 有写权限 |
| `npm run build` 报 `operation not permitted` | 本机安全策略拦截 esbuild 临时文件 | `vite.config.js` 已关 minify、`emptyOutDir: false` 兜底 |
| 8000 端口被占用 | 已有服务 | `BACKEND_PORT=8123 ./start_dev.sh` |
| 扫码登录停在演示模式 | 未配置微信开放平台密钥 | 见「微信扫码登录」小节 |

> ⚠️ 部署上线时 `.env` 会随包上传，公开前请确认 Key 已替换为专用子账号密钥。
