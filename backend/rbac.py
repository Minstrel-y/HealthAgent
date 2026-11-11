"""基于已有 JWT current_user 的数据库实时 RBAC。

安全边界：前端选中的角色不是权限，后端每个请求都根据数据库查询角色。
"""
import os
from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException

import db
from auth import current_user

ROLES = ("user", "doctor", "admin")


@dataclass(frozen=True)
class Actor:
    username: str
    role: str


def current_actor(username: str = Depends(current_user)) -> Actor:
    row = db.get_user_row(username)
    if row is None:
        raise HTTPException(status_code=401, detail="账号不存在或登录已失效")
    role = row["role"] or "user"
    if role not in ROLES:
        raise HTTPException(status_code=403, detail="无效账号角色")
    return Actor(username=username, role=role)


def require_roles(*allowed_roles: str) -> Callable:
    def _guard(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="当前角色无权操作")
        return actor
    return _guard


def validate_registration_role(role: str) -> str:
    if role not in ROLES:
        raise HTTPException(422, "无效角色")
    # 只供本机开发演示时显式开启；上线必须改为管理员审批／邀请制。
    if role != "user" and os.getenv("ALLOW_PRIVILEGED_SELF_REGISTER") != "1":
        raise HTTPException(403, "医生和管理员暂未开放自主注册")
    return role


def verify_login_role(username: str, selected_role: str) -> str:
    """密码校验成功后、签发 JWT 之前调用。"""
    row = db.get_user_row(username)
    if row is None or selected_role not in ROLES or (row["role"] or "user") != selected_role:
        # 不暴露用户是否存在/属于哪种角色
        raise HTTPException(401, "账号、密码或角色不匹配")
    return row["role"]
