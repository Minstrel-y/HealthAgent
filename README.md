# 康鉴智航 HealthAgent｜Vue3 + FastAPI 版

从 Streamlit 单体重构为前后端分离：前端 Vue3 + Element Plus + ECharts，后端 FastAPI + SQLite + DashScope。
所有体检指标判读与健康得分由后端本地计算，大模型只负责"解读和建议"。

## 目录结构

```
HealthAgent/
├── backend/
│   ├── main.py             FastAPI 入口（同时托管前端构建产物）
│   ├── config.py           配置：密钥、模型候选、路径
│   ├── db.py               SQLite：用户、体检记录
│   ├── auth.py             JWT 签发与校验
│   ├── schemas.py          请求体模型
│   ├── refs.py             参考区间判定 + 综合健康得分（本地算）
│   ├── parser.py           体检文本本地解析（降级用）
│   ├── llm.py              大模型层：抽取 / OCR / 报告 / 问答 / 趋势
│   ├── routers/
│   │   ├── auth_router.py       注册、登录
│   │   ├── records_router.py    解析、记录、总览、趋势数据
│   │   └── analysis_router.py   趋势三段分析、健康问答
│   ├── requirements.txt
│   ├── .env                 DASHSCOPE_API_KEY / JWT_SECRET（勿提交）
│   └── health.db            运行后自动生成
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── main.js  App.vue
        ├── api/index.js     axios 封装 + 拦截器（自动带 token）
        ├── router/index.js  路由 + 登录守卫
        ├── styles/main.css
        └── views/  Login / Overview / Entry / Trend / History / Chat
```

## 一、启动后端

```bash
cd ~/Desktop/HealthAgent/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

接口文档：http://127.0.0.1:8000/docs

`.env` 里两行必须填：

```env
DASHSCOPE_API_KEY = "你的阿里云百炼Key"
JWT_SECRET = "随便一串随机字符串"
```

## 二、启动前端（开发模式）

```bash
cd ~/Desktop/HealthAgent/frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`，前后端分开跑时不用管跨域。

## 三、生产模式（单端口，推荐部署用）

```bash
cd ~/Desktop/HealthAgent/frontend
npm run build        # 产出 frontend/dist
cd ../backend
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

构建产物存在时，FastAPI 会直接托管 SPA，`http://<地址>/` 就是完整应用，不再需要 Vite。

### 一键启动（推荐）

```bash
cd ~/Desktop/HealthAgent
./start_dev.sh                 # 后端 8000 + 前端 5173
BACKEND_PORT=8123 ./start_dev.sh   # 8000 被占用时换个端口，前端代理会自动跟着改
```

## 四、接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册并返回 token |
| POST | `/api/auth/login` | 登录并返回 token |
| GET | `/api/auth/me` | 当前用户 |
| POST | `/api/parse/text` | 粘贴体检原文 → 指标（模型优先，限流降级本地正则） |
| POST | `/api/parse/file` | 上传图片 / PDF → 指标（视觉模型 OCR） |
| POST | `/api/records` | 保存记录并生成 AI 报告 |
| GET | `/api/records` | 记录列表（含得分） |
| GET | `/api/records/{id}` | 单条记录详情 |
| POST | `/api/records/{id}/report` | 给指定记录补生成 AI 解读 |
| GET | `/api/overview` | 总览：指标 + 判读 + 得分 + 报告 |
| GET | `/api/trend` | 得分与各指标序列（纯本地，不调模型） |
| POST | `/api/trend/analysis` | 趋势三段分析（走模型） |
| POST | `/api/chat` | 健康问答 |
| GET | `/api/health` | 健康检查 |

## 五、常见启动问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 前端页面打不开 / 502 | Vite 依赖缓存损坏，或依赖优化中断 | `rm -rf frontend/node_modules/.vite` 后重启 `npm run dev` |
| 页面空白，控制台报 three 加载失败 | `three` 未被正确预构建 | `vite.config.js` 里已用 `optimizeDeps.exclude: ['three']` 走原生 ESM，正常环境可删掉这行 |
| 后端启动报 `disk I/O error` | 数据库目录不可写（沙箱/权限限制） | 确认 `backend/` 有写权限，或用管理员权限运行 |
| `npm run build` 报 `operation not permitted` | 本机安全策略拦截 esbuild 临时文件 | 换到普通终端执行；`vite.config.js` 已关闭 minify 作为兜底 |
| 8000 端口被占用 | 机器上已有其他服务 | `BACKEND_PORT=8123 ./start_dev.sh` |

## 六、相较 Streamlit 版的改动

- 前后端分离，页面改动不再需要重启 Python 服务
- 认证改为 JWT，前端由路由守卫统一拦截
- 健康得分、指标判读仍在后端本地计算，模型不参与判读，杜绝编造数值
- `llm.py` 内置多模型回退（qwen-plus → qwen-turbo → qwen-max）与限流退避重试
- 图表改为 ECharts，趋势页支持得分总览 + 各指标分图

> ⚠️ 部署上线时 `.env` 会随包上传，公开前请确认 Key 已替换为专用子账号密钥。
