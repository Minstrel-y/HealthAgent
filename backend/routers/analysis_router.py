"""AI 分析类接口：趋势三段分析、健康问答。"""
from fastapi import APIRouter, Depends, HTTPException

import db
import llm
from auth import current_user
from parser import build_history_text
from schemas import QuestionIn

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/trend/analysis")
def trend_analysis(username: str = Depends(current_user)):
    records = db.get_records(username)
    if len(records) < 1:
        raise HTTPException(400, "暂无体检记录")
    try:
        data = llm.trend_summary(build_history_text(records, max_records=8))
        return {"data": data}
    except Exception as e:
        raise HTTPException(500, f"趋势分析生成失败：{e}")


@router.post("/chat")
def chat(body: QuestionIn, username: str = Depends(current_user)):
    records = db.get_records(username)
    latest = records[-1] if records else None
    context = ""
    if body.record_id:
        r = db.get_record(username, body.record_id)
        if r:
            latest = r
    if latest:
        rep = latest.get("report") or {}
        context = rep.get("summary", "") or json.dumps(latest.get("parsed_data", {}), ensure_ascii=False)
    try:
        answer = llm.ask_question(body.question, context, build_history_text(records))
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(500, f"问答失败：{e}")


import json  # noqa: E402  放在这里因为仅本函数使用
