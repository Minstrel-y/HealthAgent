"""路由注册所需的公共小工具。"""
from parser import parse_health_text  # noqa: F401  供子路由复用

__all__ = ["parse_health_text"]
