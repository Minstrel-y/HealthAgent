"""医生/管理员工作台 API。

医生：只读患者体检原始记录 + 追加独立诊断。
管理员：读全部账号/记录 + 原始记录增删改；不可填写医生诊断。
普通用户：不能访问 staff/admin API；可通过 /api/diagnoses/mine 查看自己的诊断。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Literal

import db
import rules
from rbac import Actor, current_actor, require_roles
from schemas import DiagnosisIn, RecordIn, RecordUpdateIn
from routers.records_router import attach_metadata, clean_custom_metrics, clean_metrics

staff = APIRouter(prefix="/api/staff", tags=["staff"])
admin = APIRouter(prefix="/api/admin", tags=["admin"])
patient = APIRouter(prefix="/api", tags=["diagnoses"])


def _allowed_staff_record(record_id: int, actor: Actor) -> dict:
    record = db.get_record_global(record_id)
    if not record:
        raise HTTPException(404, "体检记录不存在")
    if actor.role == "doctor":
        row = db.get_user_row(record["username"])
        if not row or row["role"] != "user":
            raise HTTPException(404, "体检记录不存在")
    return record


@staff.get("/patients")
def list_patients(q: str = Query(default="", max_length=80),
                  actor: Actor = Depends(require_roles("doctor", "admin"))):
    return {"patients": db.list_staff_patients(role=actor.role, q=q)}


@staff.get("/patients/{username}/records")
def list_patient_records(username: str, actor: Actor = Depends(require_roles("doctor", "admin"))):
    target = db.get_user_row(username)
    if not target or (actor.role == "doctor" and target["role"] != "user"):
        raise HTTPException(404, "患者不存在")
    return {"username": username, "records": db.get_records(username)}


@staff.get("/records/{record_id}")
def staff_record(record_id: int, actor: Actor = Depends(require_roles("doctor", "admin"))):
    return _allowed_staff_record(record_id, actor)


@staff.get("/records/{record_id}/insights")
def staff_insights(record_id: int, actor: Actor = Depends(require_roles("doctor", "admin"))):
    record = _allowed_staff_record(record_id, actor)
    return rules.build_insights(record["parsed_data"])


@staff.get("/records/{record_id}/diagnoses")
def staff_diagnoses(record_id: int, actor: Actor = Depends(require_roles("doctor", "admin"))):
    _allowed_staff_record(record_id, actor)
    return {"diagnoses": db.list_diagnoses_for_record(record_id)}


@staff.post("/records/{record_id}/diagnoses", status_code=201)
def staff_add_diagnosis(record_id: int, body: DiagnosisIn,
                        actor: Actor = Depends(require_roles("doctor"))):
    record = _allowed_staff_record(record_id, actor)
    diagnosis_id = db.add_diagnosis(record_id, actor.username, body.model_dump())
    db.audit_events(actor.username, "doctor.add_diagnosis", record["username"], record_id)
    return {"id": diagnosis_id, "record_id": record_id, "doctor_username": actor.username}


@patient.get("/diagnoses/mine")
def my_diagnoses(actor: Actor = Depends(current_actor)):
    return {"diagnoses": db.list_my_diagnoses(actor.username)}


@admin.get("/users")
def admin_users(q: str = Query(default="", max_length=80),
                actor: Actor = Depends(require_roles("admin"))):
    return {"users": db.list_staff_patients(role="admin", q=q)}


class ChangeRole(BaseModel):
    role: Literal["user", "doctor", "admin"]


@admin.put("/users/{username}/role")
def admin_change_role(username: str, body: ChangeRole,
                      actor: Actor = Depends(require_roles("admin"))):
    if not db.admin_set_role(actor.username, username, body.role):
        raise HTTPException(400, "操作失败：不能更改自身角色，或用户不存在")
    return {"username": username, "role": body.role}


@admin.post("/patients/{username}/records", status_code=201)
def admin_add_record(username: str, body: RecordIn,
                     actor: Actor = Depends(require_roles("admin"))):
    metrics = clean_metrics((body.metrics or {}).model_dump())
    custom = clean_custom_metrics(body.custom_metrics)
    if not metrics and not custom and not body.extra_text.strip():
        raise HTTPException(400, "请至少填写一项有效检查信息")
    data = attach_metadata(metrics, body.check_type, custom, body.lab_system)
    raw = body.raw_text.strip() or body.extra_text.strip() or "（管理员补充录入）"
    try:
        record_id = db.admin_create_record(actor.username, username, raw, data)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"record_id": record_id, "needs_report": True}


@admin.put("/records/{record_id}")
def admin_edit_record(record_id: int, body: RecordUpdateIn,
                      actor: Actor = Depends(require_roles("admin"))):
    old = _allowed_staff_record(record_id, actor)
    metrics = clean_metrics(body.metrics)
    data = attach_metadata(
        metrics,
        body.check_type or old["parsed_data"].get("_check_type", "general"),
        body.custom_metrics if body.custom_metrics is not None else old["parsed_data"].get("_custom_metrics", []),
        body.lab_system if body.lab_system is not None else old["parsed_data"].get("_lab_system"),
    )
    if not metrics and not data["_custom_metrics"]:
        raise HTTPException(400, "至少保留一项有效体检指标")
    raw = body.raw_text.strip() or old["raw_text"]
    db.admin_update_record(actor.username, record_id, raw, data)
    # 旧 AI 解读已经失效，因此清除；避免给患者展示与新数据不匹配的报告。
    return {"ok": True, "record_id": record_id, "needs_report": True}


@admin.delete("/records/{record_id}")
def admin_remove_record(record_id: int, actor: Actor = Depends(require_roles("admin"))):
    if not db.admin_delete_record(actor.username, record_id):
        raise HTTPException(404, "体检记录不存在")
    return {"ok": True}


@admin.post("/records/{record_id}/report")
def admin_regen_report(record_id: int, actor: Actor = Depends(require_roles("admin"))):
    """手动触发再生成，避免管理员每次保存都阻塞等待模型。"""
    from parser import build_history_text
    import llm
    record = _allowed_staff_record(record_id, actor)
    report = llm.generate_report(record["parsed_data"],
                                 build_history_text(db.get_records(record["username"])))
    db.update_report(record_id, report)
    db.audit_events(actor.username, "admin.generate_report", record["username"], record_id)
    return {"report": report}


@admin.get("/audit-logs")
def admin_audit_logs(limit: int = Query(default=100, ge=1, le=200),
                     actor: Actor = Depends(require_roles("admin"))):
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, actor_username, action, target_username, record_id, created_at "
            "FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return {"items": [dict(row) for row in rows]}
    finally:
        conn.close()
