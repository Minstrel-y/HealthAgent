"""规则库接口：单指标详情、本次记录的诱因推断。

全部为本地静态规则计算，不调用大模型，响应毫秒级、结果可复现。
"""

from fastapi import APIRouter, Depends

import db
import refs
import rules
from auth import current_user

router = APIRouter(prefix="/api/rules", tags=["rules"])


def _latest_parsed(username: str, record_id: int = None):
    if record_id:
        r = db.get_record(username, record_id)
        return r, (r or {}).get("parsed_data") or {}
    rows = db.get_records(username)
    if not rows:
        return None, {}
    latest = rows[-1]
    return latest, latest.get("parsed_data") or {}


@router.get("/metrics")
def list_metrics(_: str = Depends(current_user)):
    """列出指标库支持的所有指标（名称、单位、参考区间），录入表单据此动态生成字段。"""
    return {
        "keys": list(rules.RULES.keys()),
        "metrics": [
            {
                "key": k,
                "name": m["name"],
                "unit": m.get("unit", ""),
                "low": m.get("low"),
                "high": m.get("high"),
                "has_rule": k in rules.RULES,
            }
            for k, m in refs.METRICS.items()
        ],
    }


@router.get("/{key}")
def metric_detail(key: str, username: str = Depends(current_user)):
    """某个指标的完整规则：诱因、关联疾病、进一步检查、生活干预。"""
    _, parsed = _latest_parsed(username)
    data = rules.metric_rule(key, parsed)
    if not data:
        return {"detail": "该指标暂无规则数据"}
    return data


@router.get("/insights/latest")
def insights(record_id: int = None, username: str = Depends(current_user)):
    """基于最近（或指定）体检记录，给出异常指标的诱因推断与交叉组合结论。"""
    latest, parsed = _latest_parsed(username, record_id)
    if not latest:
        return {"items": [], "cross": [], "disclaimer": rules.DISCLAIMER}
    result = rules.build_insights(parsed)
    result["record_id"] = latest.get("id")
    result["record_time"] = latest.get("record_time")
    return result
