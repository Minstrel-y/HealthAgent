from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse

import db
from auth import create_token, current_user
from config import (
    AVATAR_DIR,
    WECHAT_APPID,
    WECHAT_ENABLED,
    WECHAT_REDIRECT_URI,
    WECHAT_SECRET,
)
from schemas import LoginIn, ProfileIn, RegisterIn, TokenOut, WechatConfirmIn

router = APIRouter(prefix="/api/auth", tags=["auth"])

AVATAR_MAX_BYTES = 3 * 1024 * 1024  # 头像最多 3MB
ALLOWED_IMG = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn):
    username = (body.username or "").strip()
    if not username or len(body.password or "") < 6:
        raise HTTPException(400, "用户名不能为空，密码至少 6 位")
    if not db.create_user(username, body.password):
        raise HTTPException(400, "用户名已存在")
    return TokenOut(access_token=create_token(username), username=username)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn):
    username = (body.username or "").strip()
    if not db.verify_user(username, body.password):
        raise HTTPException(401, "账号或密码错误")
    return TokenOut(access_token=create_token(username), username=username)


@router.get("/me")
def me(username: str = Depends(current_user)):
    return {"username": username, **db.get_profile(username)}


# ------------------------------------------------------------- 个人资料
@router.get("/profile")
def get_profile(username: str = Depends(current_user)):
    return db.get_profile(username)


@router.put("/profile")
def update_profile(body: ProfileIn, username: str = Depends(current_user)):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if "sex" in patch and patch["sex"] not in ("male", "female", "unknown"):
        raise HTTPException(400, "性别只能是 male / female / unknown")
    if "font_scale" in patch:
        patch["font_scale"] = max(0.85, min(1.4, float(patch["font_scale"])))
    return db.update_profile(username, patch)


@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), username: str = Depends(current_user)):
    """上传头像，返回可访问 URL。"""
    if file.content_type not in ALLOWED_IMG:
        raise HTTPException(400, "仅支持 png / jpg / webp / gif 图片")
    data = await file.read()
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(400, "图片不能超过 3MB")

    ext = (file.filename or "avatar.png").rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        ext = "png"
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    name = f"{username}_{stamp}.{ext}"
    (AVATAR_DIR / name).write_bytes(data)
    url = f"/uploads/avatars/{name}"
    db.update_profile(username, {"avatar": url})
    return {"avatar": url}


# --------------------------------------------------------------- 微信登录
@router.get("/wechat/qr")
def wechat_qr():
    """返回二维码内容与票据。

    真实模式（已配置微信开放平台密钥）：返回 OAuth 授权页地址，扫码后微信
    重定向到回调接口，由回调写入 openid 并签发 token；
    演示模式：返回一个本地确认地址（或用 /wechat/mock-scan 直接确认），
    前端交互完全一致。
    """
    ticket = db.create_wechat_session()
    if WECHAT_ENABLED:
        from urllib.parse import quote
        url = (
            "https://open.weixin.qq.com/connect/qrconnect"
            f"?appid={WECHAT_APPID}"
            f"&redirect_uri={quote(WECHAT_REDIRECT_URI, safe='')}"
            "&response_type=code&scope=snsapi_login"
            f"&state={ticket}#wechat_redirect"
        )
        return {"mode": "wechat", "ticket": ticket, "url": url}
    # 演示模式：二维码内容是本地确认链接（手机扫码后打开浏览器确认，或直接点「模拟确认」）
    return {
        "mode": "demo",
        "ticket": ticket,
        "url": f"/wechat-mock?ticket={ticket}",
        "hint": "未配置微信开放平台密钥，当前为演示模式：扫码或点击「模拟扫码」即可完成登录",
    }


@router.get("/wechat/poll")
def wechat_poll(ticket: str):
    """前端轮询票据状态：pending -> confirmed / expired。"""
    s = db.get_wechat_session(ticket)
    if not s:
        raise HTTPException(404, "二维码不存在")
    if s["status"] != "confirmed":
        return {"status": s["status"]}
    return {
        "status": "confirmed",
        "access_token": create_token(s["username"]),
        "token_type": "bearer",
        "username": s["username"],
    }


@router.post("/wechat/confirm", response_model=TokenOut)
def wechat_confirm(body: WechatConfirmIn):
    """确认扫码：真实模式由回调携带 openid 调用；演示模式直接用票据换取身份。"""
    s = db.get_wechat_session(body.ticket)
    if not s or s["status"] != "pending":
        raise HTTPException(400, "二维码已失效，请刷新重试")

    if body.openid:
        username = db.ensure_openid_user(body.openid, body.nickname or "", body.avatar or "")
    else:
        # 演示模式：为该票据生成一个演示身份（同一票据内保持一致）
        username = "wx_demo_" + str(abs(hash(body.ticket)) % 100000)
        if not db.get_user_row(username):
            db.create_user(username, "wechat-demo-" + body.ticket[-8:])
            db.update_profile(username, {"nickname": "微信用户", "avatar": ""})
    if not username:
        raise HTTPException(500, "登录失败，请重试")
    db.confirm_wechat_session(body.ticket, username, body.openid or "")
    return TokenOut(access_token=create_token(username), username=username)


@router.get("/wechat/callback")
def wechat_callback(code: str = "", state: str = ""):
    """微信开放平台回调：用 code 换取 access_token，拿到 openid 后完成登录。"""
    if not WECHAT_ENABLED:
        raise HTTPException(400, "未启用真实微信登录")
    if not code or not state:
        raise HTTPException(400, "缺少授权参数")

    import httpx
    try:
        r = httpx.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": WECHAT_APPID,
                "secret": WECHAT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        info = r.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"微信授权失败：{e}")

    openid = info.get("openid")
    if not openid:
        raise HTTPException(400, f"微信授权失败：{info.get('errmsg', '未知错误')}")

    username = db.ensure_openid_user(openid)
    db.confirm_wechat_session(state, username, openid)
    # 回调发生在浏览器端，跳回前端由轮询拿 token
    return RedirectResponse(url="/login?wx=" + state)
