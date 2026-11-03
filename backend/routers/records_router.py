"""录入、解析、记录读写、总览。

设计原则：上传文件 / 粘贴原文 / 手动填写 三源平级，都产出同一套 metrics，
命中任一即可出报告，没做的项目不许强填。
"""
import base64
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

import db
import llm
from auth import current_user
from parser import build_history_text, parse_health_text
from refs import METRICS, build_departments, count_abnormal, health_score, score_label
from schemas import RecordIn, RecordUpdateIn

router = APIRouter(prefix="/api", tags=["records"])

# 跟随指标库自动扩展：refs.METRICS 新增一项，录入/解析/判读链路立刻认它
METRIC_KEYS = ["height", "weight"] + list(METRICS)


def clean_metrics(d: dict) -> dict:
    """去掉 None / 空值，补算 BMI，只保留有效数值。"""
    out = {}
    for k in ("sex", "age"):
        if d.get(k) not in (None, ""):
            out[k] = d[k]
    for k in METRIC_KEYS:
        v = d.get(k)
        if isinstance(v, (int, float)):
            out[k] = round(float(v), 2)
    h, w = out.get("height"), out.get("weight")
    if h and w and not out.get("bmi"):
        out["bmi"] = round(w / (h / 100) ** 2, 2)
    return out


# ---------------- 解析：三种输入源 ----------------
@router.post("/parse/text")
def parse_text(payload: dict, username: str = Depends(current_user)):
    """粘贴体检原文 -> 指标。优先走模型，限流时自动降级本地正则。"""
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "请先粘贴体检文本")
    try:
        metrics = clean_metrics(llm.extract_metrics_from_text(text))
        source = "llm"
    except Exception as e:
        metrics = clean_metrics(parse_health_text(text))
        source = f"local（AI 抽取暂不可用：{str(e)[:60]}）"
    return {"metrics": metrics, "source": source}


@router.post("/parse/file")
async def parse_file(file: UploadFile = File(...), username: str = Depends(current_user)):
    """上传图片 / PDF -> 指标。PDF 取前 2 页渲染成图后交给视觉模型。"""
    data = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".pdf"):
            b64 = None
            for img in llm.pdf_to_png_bytes(data):
                b64 = base64.b64encode(img).decode()
                metrics = clean_metrics(llm.ocr_image_base64(b64))
                if len(metrics) >= 6:
                    return {"metrics": metrics, "source": "vision"}
            return {"metrics": {}, "source": "vision"}
        mime = "image/png" if name.endswith(".png") else "image/jpeg"
        metrics = clean_metrics(llm.ocr_image_base64(base64.b64encode(data).decode(), mime))
        return {"metrics": metrics, "source": "vision"}
    except Exception as e:
        raise HTTPException(500, f"识别失败：{e}")


# ---------------- 记录 ----------------
@router.post("/records")
def create_record(body: RecordIn, username: str = Depends(current_user)):
    """保存一条体检记录并生成 AI 报告。报告生成失败也保留记录，方便事后补。"""
    metrics = clean_metrics((body.metrics or {}).model_dump() if body.metrics else {})
    has_metric = any(k in metrics for k in METRIC_KEYS)
    if not has_metric and not body.extra_text.strip():
        raise HTTPException(400, "没有可用指标。请上传报告、粘贴原文或填写至少一项。")

    raw = body.raw_text.strip()
    if not raw:
        raw = body.extra_text.strip() or "（手动填写录入）"
    elif body.extra_text.strip():
        raw += f"\n其他检查项目：{body.extra_text.strip()}"

    record_id = db.insert_record(username, raw, metrics)
    records = db.get_records(username)

    report = None
    error = None
    try:
        report = llm.generate_report(metrics, build_history_text(records), extra_text=body.extra_text.strip())
        db.update_report(record_id, report)
    except Exception as e:
        error = str(e)

    return {"record_id": record_id, "metrics": metrics, "report": report, "report_error": error}


@router.get("/records")
def list_records(username: str = Depends(current_user)):
    records = db.get_records(username)
    return [{
        "id": r["id"],
        "record_time": r["record_time"],
        "metrics": r["parsed_data"],
        "score": health_score(r["parsed_data"]),
        "score_label": score_label(health_score(r["parsed_data"])),
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
    if not metrics:
        raise HTTPException(400, "没有可用指标，请至少保留一项")

    raw = (body.raw_text or "").strip() or r["raw_text"]
    if not db.update_record(username, record_id, raw, metrics):
        raise HTTPException(404, "记录不存在")

    # 指标变了，旧解读不再匹配：先清掉，成功则覆盖，失败则保持「未生成」供用户补生成
    db.update_report(record_id, None)
    report = None
    error = None
    try:
        report = llm.generate_report(metrics, build_history_text(db.get_records(username)))
        db.update_report(record_id, report)
    except Exception as e:
        error = str(e)

    return {"metrics": metrics, "report": report, "report_error": error}


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
    score = health_score(parsed)

    prev_score = None
    if len(records) >= 2:
        prev_score = health_score(records[-2]["parsed_data"])

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
        "departments": build_departments(parsed),
        "abnormal_count": count_abnormal(parsed),
        "score": score,
        "score_label": score_label(score),
        "score_delta": None if prev_score is None else score - prev_score,
        "bmi_delta": None if (prev_bmi is None or parsed.get("bmi") is None)
                     else round(parsed["bmi"] - prev_bmi, 1),
        "report": latest["report"],
        "raw_text": latest["raw_text"],
    }


# ---------------- 趋势（纯本地，不烧 token） ----------------
@router.get("/trend")
def trend(username: str = Depends(current_user)):
    records = db.get_records(username)
    points = [{"record_time": r["record_time"], "score": health_score(r["parsed_data"])} for r in records]
    series = {}
    for key in METRIC_KEYS:
        vals = [{"t": r["record_time"], "v": r["parsed_data"].get(key)}
                for r in records if isinstance(r["parsed_data"].get(key), (int, float))]
        if vals:
            series[key] = vals
    return {"points": points, "series": series}
