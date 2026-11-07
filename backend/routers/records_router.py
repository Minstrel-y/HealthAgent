"""录入、解析、记录读写、总览。

设计原则：上传文件 / 粘贴原文 / 手动填写 三源平级，都产出同一套 metrics，
命中任一即可出报告，没做的项目不许强填。
"""
import base64
import json
import math

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

import db
import llm
from auth import current_user
from parser import build_history_text, parse_health_text
from refs import METRICS, CHECK_TYPES, TSH_SYSTEM_RANGES, build_departments, count_abnormal, health_score, score_label, scorable_count
from schemas import RecordIn, RecordUpdateIn

router = APIRouter(prefix="/api", tags=["records"])

# 跟随指标库自动扩展：refs.METRICS 新增一项，录入/解析/判读链路立刻认它
METRIC_KEYS = ["height", "weight"] + list(METRICS)


def clean_metrics(d: dict) -> dict:
    """去掉 None / 空值，补算 BMI，只保留有效数值。"""
    out = {}
    for k in ("sex", "age"):
        if d.get(k) not in (None, ""):
            if k == "sex" and d[k] in ("male", "female", "unknown"):
                out[k] = d[k]
            elif k == "age" and isinstance(d[k], (int, float)) and 0 < d[k] < 130:
                out[k] = int(d[k])
    for k in METRIC_KEYS:
        v = d.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
            out[k] = round(float(v), 4)
    h, w = out.get("height"), out.get("weight")
    if h and w and not out.get("bmi"):
        out["bmi"] = round(w / (h / 100) ** 2, 2)
    return out


def clean_custom_metrics(items):
    """保留未收录的自定义指标，仅作展示，不参与评分或医学规则。"""
    cleaned = []
    for item in (items or [])[:100]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()[:100]
        value = item.get("value")
        if not name or value is None or isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(number):
            continue
        cleaned.append({"name": name, "value": number,
                        "unit": str(item.get("unit") or "")[:40],
                        "reference": str(item.get("reference") or "")[:100]})
    return cleaned


def attach_metadata(metrics, check_type, custom_metrics, lab_system=None):
    result = dict(metrics)
    result["_check_type"] = check_type if check_type in CHECK_TYPES else "other"
    # 与本次甲状腺报告匹配的检测系统，未选择时不进行 TSH 数值判读。
    if lab_system in TSH_SYSTEM_RANGES:
        result["_lab_system"] = lab_system
    result["_custom_metrics"] = clean_custom_metrics(custom_metrics)
    return result


def score_or_none(data):
    """只有存在可按明确参考区间判读的指标才计算评分。"""
    return health_score(data) if scorable_count(data) else None


def score_name(score):
    return score_label(score) if score is not None else "未评分"


def record_metadata(parsed):
    key = parsed.get("_check_type", "general")
    return {"check_type": key, "check_type_name": CHECK_TYPES.get(key, CHECK_TYPES["other"])["name"],
            "lab_system": parsed.get("_lab_system"),
            "custom_metrics": parsed.get("_custom_metrics") or []}


def clean_parsed_result(parsed):
    """解析结果分为预设指标与非标准自定义指标，供用户核对。"""
    return {"metrics": clean_metrics(parsed),
            "custom_metrics": clean_custom_metrics(parsed.get("_custom_metrics"))}


@router.get("/check-types")
def check_types(username: str = Depends(current_user)):
    return {"types": [{"key": k, **v} for k, v in CHECK_TYPES.items()]}


# ---------------- 解析：三种输入源 ----------------
@router.post("/parse/text")
def parse_text(payload: dict, username: str = Depends(current_user)):
    """粘贴体检原文 -> 指标。优先走模型，限流时自动降级本地正则。"""
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "请先粘贴体检文本")
    try:
        parsed = clean_parsed_result(llm.extract_metrics_from_text(text))
        source = "llm"
    except Exception as e:
        parsed = clean_parsed_result(parse_health_text(text))
        source = f"local（AI 抽取暂不可用：{str(e)[:60]}）"
    return {**parsed, "source": source}


@router.post("/parse/file")
async def parse_file(file: UploadFile = File(...), username: str = Depends(current_user)):
    """上传图片 / PDF -> 指标。PDF 取前 2 页渲染成图后交给视觉模型。"""
    name = (file.filename or "").lower()
    if not name.endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(400, "仅支持 PDF、PNG、JPG、JPEG 文件")
    data = await file.read(15 * 1024 * 1024 + 1)
    if not data or len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "文件为空或超过 15 MB")
    try:
        if name.endswith(".pdf"):
            metrics, custom = {}, []
            page_errors = []
            for img in llm.pdf_to_png_bytes(data, max_pages=2):
                try:
                    parsed = clean_parsed_result(llm.ocr_image_base64(base64.b64encode(img).decode()))
                except Exception as exc:
                    # 单页无内容或识别失败，不丢弃其他页已获得的结果。
                    page_errors.append(str(exc))
                    continue
                # 不再因为每页识别不足 6 项而丢弃结果：合并前两页的检查项。
                for key, value in parsed["metrics"].items():
                    metrics.setdefault(key, value)
                custom.extend(parsed["custom_metrics"])
            if not metrics and not custom and page_errors:
                raise HTTPException(422, "报告前两页未能识别到数值项目，请尝试更清晰的图片")
            seen = set()
            unique_custom = []
            for item in custom:
                name_unit = (item["name"].lower(), item["unit"])
                if name_unit not in seen:
                    seen.add(name_unit)
                    unique_custom.append(item)
            return {"metrics": metrics, "custom_metrics": unique_custom, "source": "vision"}
        mime = "image/png" if name.endswith(".png") else "image/jpeg"
        parsed = clean_parsed_result(llm.ocr_image_base64(base64.b64encode(data).decode(), mime))
        return {**parsed, "source": "vision"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"识别失败：{e}")


# ---------------- 记录 ----------------
@router.post("/records")
def create_record(body: RecordIn, username: str = Depends(current_user)):
    """保存一条体检记录并生成 AI 报告。报告生成失败也保留记录，方便事后补。"""
    metrics = clean_metrics((body.metrics or {}).model_dump() if body.metrics else {})
    has_metric = any(k in metrics for k in METRIC_KEYS)
    if not has_metric and not body.extra_text.strip() and not clean_custom_metrics(body.custom_metrics):
        raise HTTPException(400, "没有可用指标。请上传报告、粘贴原文或填写至少一项。")

    raw = body.raw_text.strip()
    if not raw:
        raw = body.extra_text.strip() or "（手动填写录入）"
    elif body.extra_text.strip():
        raw += f"\n其他检查项目：{body.extra_text.strip()}"

    stored = attach_metadata(metrics, body.check_type, body.custom_metrics, body.lab_system)
    record_id = db.insert_record(username, raw, stored)
    records = db.get_records(username)

    report = None
    error = None
    try:
        report = llm.generate_report(stored, build_history_text(records), extra_text=body.extra_text.strip())
        db.update_report(record_id, report)
    except Exception as e:
        error = str(e)

    return {"record_id": record_id, "metrics": stored, "report": report, "report_error": error}


@router.get("/records")
def list_records(username: str = Depends(current_user)):
    records = db.get_records(username)
    return [{
        "id": r["id"],
        "record_time": r["record_time"],
        "metrics": r["parsed_data"],
        **record_metadata(r["parsed_data"]),
        "score": score_or_none(r["parsed_data"]),
        "score_label": score_name(score_or_none(r["parsed_data"])),
        "has_report": r["report"] is not None,
        "risk_level": (r["report"] or {}).get("risk_level"),
    } for r in records]


@router.get("/records/{record_id}")
def get_record(record_id: int, username: str = Depends(current_user)):
    r = db.get_record(username, record_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    return r


@router.post("/records/{record_id}/report")
def gen_report(record_id: int, username: str = Depends(current_user)):
    """给某条记录补生成 AI 解读。"""
    r = db.get_record(username, record_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    try:
        report = llm.generate_report(r["parsed_data"], build_history_text(db.get_records(username)))
        db.update_report(record_id, report)
        return {"report": report}
    except Exception as e:
        raise HTTPException(500, f"生成失败：{e}")


@router.put("/records/{record_id}")
def update_record(record_id: int, body: RecordUpdateIn, username: str = Depends(current_user)):
    """修改记录指标并重新生成 AI 解读。指标会被清理后整体覆盖。"""
    r = db.get_record(username, record_id)
    if not r:
        raise HTTPException(404, "记录不存在")

    metrics = clean_metrics(body.metrics)
    stored = attach_metadata(metrics, body.check_type or r["parsed_data"].get("_check_type", "general"),
                             body.custom_metrics if body.custom_metrics is not None else r["parsed_data"].get("_custom_metrics", []),
                             body.lab_system if body.lab_system is not None else r["parsed_data"].get("_lab_system"))
    if not metrics and not stored["_custom_metrics"]:
        raise HTTPException(400, "没有可用指标，请至少保留一项")

    raw = (body.raw_text or "").strip() or r["raw_text"]
    if not db.update_record(username, record_id, raw, stored):
        raise HTTPException(404, "记录不存在")

    # 指标变了，旧解读不再匹配：先清掉，成功则覆盖，失败则保持「未生成」供用户补生成
    db.update_report(record_id, None)
    report = None
    error = None
    try:
        report = llm.generate_report(stored, build_history_text(db.get_records(username)))
        db.update_report(record_id, report)
    except Exception as e:
        error = str(e)

    return {"metrics": stored, "report": report, "report_error": error}


@router.delete("/records/{record_id}")
def delete_record(record_id: int, username: str = Depends(current_user)):
    """删除一条体检记录。"""
    if not db.delete_record(username, record_id):
        raise HTTPException(404, "记录不存在")
    return {"ok": True}


# ---------------- 总览 ----------------
@router.get("/overview")
def overview(username: str = Depends(current_user)):
    """最新一条记录 + 本地判读 + AI 报告 + 对比上一次。"""
    records = db.get_records(username)
    if not records:
        return {"empty": True}

    latest = records[-1]
    parsed = dict(latest["parsed_data"])
    # 用户在「个人设置」里填的性别参与判读：肌酐、尿酸的参考区间男女不同。
    # 记录里已带 sex 时以记录为准（体检报告通常更权威）。
    if not parsed.get("sex"):
        row = db.get_user_row(username)
        profile_sex = (row["sex"] if row and row["sex"] else "unknown")
        if profile_sex in ("male", "female"):
            parsed["sex"] = profile_sex
    score = score_or_none(parsed)

    prev_score = None
    if len(records) >= 2:
        prev_score = score_or_none(records[-2]["parsed_data"])

    prev_bmi = None
    for r in reversed(records[:-1]):
        if r["parsed_data"].get("bmi") is not None:
            prev_bmi = r["parsed_data"]["bmi"]
            break

    return {
        "empty": False,
        "record_id": latest["id"],
        "record_time": latest["record_time"],
        "metrics": parsed,
        **record_metadata(parsed),
        "scorable_count": scorable_count(parsed),
        "departments": build_departments(parsed),
        "abnormal_count": count_abnormal(parsed),
        "score": score,
        "score_label": score_name(score),
        "score_delta": None if prev_score is None or score is None else score - prev_score,
        "bmi_delta": None if (prev_bmi is None or parsed.get("bmi") is None)
                     else round(parsed["bmi"] - prev_bmi, 1),
        "report": latest["report"],
        "raw_text": latest["raw_text"],
    }


# ---------------- 趋势（纯本地，不烧 token） ----------------
@router.get("/trend")
def trend(username: str = Depends(current_user)):
    records = db.get_records(username)
    points = [{"record_time": r["record_time"], "score": score_or_none(r["parsed_data"])} for r in records]
    series = {}
    for key in METRIC_KEYS:
        vals = [{"t": r["record_time"], "v": r["parsed_data"].get(key)}
                for r in records if isinstance(r["parsed_data"].get(key), (int, float))]
        if vals:
            series[key] = vals
    return {"points": points, "series": series}
