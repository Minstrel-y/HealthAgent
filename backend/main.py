"""康鉴智航 FastAPI 入口：提供 REST API，并在生产模式下同时托管前端构建产物。"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import db
from config import DASHSCOPE_API_KEY, FRONTEND_DIST, UPLOAD_DIR
from routers.analysis_router import router as analysis_router
from routers.auth_router import router as auth_router
from routers.insight_router import router as insight_router
from routers.records_router import router as records_router

db.init_db()

app = FastAPI(title="康鉴智航 API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(records_router)
app.include_router(analysis_router)
app.include_router(insight_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "api_key_configured": bool(DASHSCOPE_API_KEY),
        "frontend_built": FRONTEND_DIST.exists(),
    }


# ---- 静态托管前端（构建后才生效，未构建时仍可纯 API 调试）----
# 头像等上传目录始终挂载，需在 SPA catch-all 之前注册
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        target = FRONTEND_DIST / full_path
        if full_path and target.exists() and target.is_file():
            return FileResponse(str(target))
        # 首页必须禁用缓存：否则重新打包后浏览器仍加载旧的 index.html
        return FileResponse(
            str(FRONTEND_DIST / "index.html"),
            headers={"Cache-Control": "no-store, must-revalidate"},
        )
else:
    @app.get("/")
    def root():
        return JSONResponse({"message": "康鉴智航 API 已启动；前端尚未构建，请先在 frontend/ 执行 npm run build。"})
