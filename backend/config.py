"""全局配置：密钥、模型、数据库路径都从这里读。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 手动加载 backend/.env（存在才生效），这样不用依赖启动方式
_env_file = BASE_DIR / "backend" / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# JWT
JWT_SECRET = os.environ.get("JWT_SECRET", "health-agent-dev-secret-change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_HOURS = 24 * 7

DB_PATH = BASE_DIR / "backend" / "health.db"

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# 头像等上传文件的存放目录（通过 /uploads 静态访问）
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"
AVATAR_DIR = UPLOAD_DIR / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 微信登录
# 真实微信扫码登录需要「微信开放平台 - 网站应用」：
#   企业认证主体（个人开发者无法申请）+ ICP 备案域名 + 回调域名白名单。
# 未配置 AppID 时自动降级为「演示模式」：二维码仍可扫（或点模拟确认），
# 走本地确认流程，交互完全一致；日后拿到资质只需补齐这三个环境变量。
WECHAT_APPID = os.environ.get("WECHAT_APPID", "")
WECHAT_SECRET = os.environ.get("WECHAT_SECRET", "")
WECHAT_REDIRECT_URI = os.environ.get("WECHAT_REDIRECT_URI", "")
WECHAT_DEMO = os.environ.get("WECHAT_DEMO", "")  # 强制演示模式填 1
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8124")

WECHAT_ENABLED = bool(WECHAT_APPID and WECHAT_SECRET and WECHAT_REDIRECT_URI) and WECHAT_DEMO != "1"

# 文本模型候选（按优先级）：实测同一 Key 下 qwen-turbo 常被限流，qwen-plus 更稳
MODEL_CANDIDATES = ["qwen-plus", "qwen-turbo", "qwen-max"]

# 视觉模型（按可用顺序尝试）
VL_MODELS = ["qwen3-vl-plus", "qwen-vl-max-latest", "qwen2.5-vl-72b-instruct"]

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
