"""鉴权：JWT 签发与校验，供路由依赖注入。"""
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import JWT_ALG, JWT_EXPIRE_HOURS, JWT_SECRET

bearer = HTTPBearer(auto_error=True)


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALG])
        user = payload.get("sub")
        if not user:
            raise ValueError("no sub")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的身份凭证")
