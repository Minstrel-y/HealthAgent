"""数据层：SQLite。所有 SQL 参数化，避免注入。"""
import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import datetime

from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _add_column_if_missing(conn, table: str, column: str, decl: str):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            pwd_hash   TEXT NOT NULL,
            salt       TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL,
            raw_text    TEXT,
            parsed_json TEXT,
            report_json TEXT,
            record_time TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_records_user ON records(username, record_time)")

    # ---- 用户个人资料（头像、昵称、性别生日、字号偏好、微信身份）----
    _add_column_if_missing(conn, "users", "nickname", "TEXT")
    _add_column_if_missing(conn, "users", "avatar", "TEXT")
    _add_column_if_missing(conn, "users", "sex", "TEXT")
    _add_column_if_missing(conn, "users", "birthday", "TEXT")
    _add_column_if_missing(conn, "users", "font_scale", "REAL")
    _add_column_if_missing(conn, "users", "wechat_openid", "TEXT")
    # RBAC：旧账号默认普通用户；不会清空任何现有数据
    _add_column_if_missing(conn, "users", "role", "TEXT NOT NULL DEFAULT 'user'")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
            doctor_username TEXT NOT NULL,
            title TEXT NOT NULL,
            impression TEXT NOT NULL,
            advice TEXT NOT NULL,
            follow_up TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_diagnoses_record ON diagnoses(record_id, created_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_username TEXT NOT NULL,
            action TEXT NOT NULL,
            target_username TEXT,
            record_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)

    # ---- 微信扫码会话：二维码 -> 轮询 -> 登录 ----
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wechat_sessions (
            ticket     TEXT PRIMARY KEY,
            status     TEXT NOT NULL,
            username   TEXT,
            openid     TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ 个人资料
def get_user_row(username: str):
    conn = get_conn()
    try:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()


def get_profile(username: str) -> dict:
    row = get_user_row(username)
    return {
        "username": username,
        "role": (row["role"] if row and row["role"] else "user"),
        "nickname": (row["nickname"] if row and row["nickname"] else username),
        "avatar": (row["avatar"] if row and row["avatar"] else ""),
        "sex": (row["sex"] if row and row["sex"] else "unknown"),
        "birthday": (row["birthday"] if row and row["birthday"] else ""),
        "font_scale": (row["font_scale"] if row and row["font_scale"] else 1.0),
        "created_at": (row["created_at"] if row else ""),
    }


_PROFILE_FIELDS = ("nickname", "avatar", "sex", "birthday", "font_scale")


def update_profile(username: str, patch: dict) -> dict:
    sets, values = [], []
    for k in _PROFILE_FIELDS:
        if k in patch and patch[k] is not None:
            sets.append(f"{k} = ?")
            values.append(patch[k])
    if sets:
        values.append(username)
        conn = get_conn()
        try:
            conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE username = ?", values)
            conn.commit()
        finally:
            conn.close()
    return get_profile(username)


def get_user_by_openid(openid: str):
    if not openid:
        return None
    conn = get_conn()
    try:
        return conn.execute("SELECT * FROM users WHERE wechat_openid = ?", (openid,)).fetchone()
    finally:
        conn.close()


ITERATIONS = 200_000


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS).hex()


def create_user(username: str, password: str, openid: str = "", role: str = "user") -> bool:
    username = (username or "").strip()
    if not username or not password or role not in ("user", "doctor", "admin"):
        return False
    salt = secrets.token_hex(16)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, pwd_hash, salt, created_at, wechat_openid, role) VALUES (?, ?, ?, ?, ?, ?)",
            (username, hash_password(password, salt), salt,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), openid or None, role),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ------------------------------------------------------------ 微信扫码会话
TICKET_TTL_SECONDS = 300  # 二维码 5 分钟内有效


def create_wechat_session() -> str:
    ticket = secrets.token_urlsafe(16)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO wechat_sessions (ticket, status, created_at) VALUES (?, 'pending', ?)",
            (ticket, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    finally:
        conn.close()
    return ticket


def get_wechat_session(ticket: str):
    row = None
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM wechat_sessions WHERE ticket = ?", (ticket,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    age = (datetime.now() - created).total_seconds()
    d = {"ticket": row["ticket"], "status": row["status"], "username": row["username"], "age": age}
    if d["status"] == "pending" and age > TICKET_TTL_SECONDS:
        d["status"] = "expired"
    return d


def confirm_wechat_session(ticket: str, username: str, openid: str = "") -> bool:
    conn = get_conn()
    try:
        cur = conn.execute(
            "UPDATE wechat_sessions SET status='confirmed', username=?, openid=? WHERE ticket=? AND status='pending'",
            (username, openid or None, ticket),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def ensure_openid_user(openid: str, nickname: str = "", avatar: str = ""):
    """微信身份首次登录时创建账号（随机内部密码，无法用于密码登录）。"""
    row = get_user_by_openid(openid)
    if row:
        return row["username"]
    username = "wx_" + openid[-10:].lower()
    if get_user_row(username):
        username = "wx_" + secrets.token_hex(4)
    if not create_user(username, secrets.token_urlsafe(16), openid=openid):
        return None
    patch = {}
    if nickname:
        patch["nickname"] = nickname
    if avatar:
        patch["avatar"] = avatar
    if patch:
        update_profile(username, patch)
    return username


def verify_user(username: str, password: str) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT pwd_hash, salt FROM users WHERE username = ?", ((username or "").strip(),)
        ).fetchone()
        if row is None:
            return False
        return hmac.compare_digest(row["pwd_hash"], hash_password(password or "", row["salt"]))
    finally:
        conn.close()


def insert_record(username: str, raw_text: str, parsed: dict) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO records (username, raw_text, parsed_json, record_time) VALUES (?, ?, ?, ?)",
            (username, raw_text, json.dumps(parsed or {}, ensure_ascii=False),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_report(record_id: int, report: dict):
    conn = get_conn()
    try:
        conn.execute("UPDATE records SET report_json = ? WHERE id = ?",
                     (json.dumps(report, ensure_ascii=False), record_id))
        conn.commit()
    finally:
        conn.close()


def update_record(username: str, record_id: int, raw_text: str, parsed: dict) -> bool:
    """更新一条记录的结构化指标与原文；只允许本人操作，返回是否命中。"""
    conn = get_conn()
    try:
        cur = conn.execute(
            "UPDATE records SET raw_text = ?, parsed_json = ? WHERE id = ? AND username = ?",
            (raw_text, json.dumps(parsed or {}, ensure_ascii=False), record_id, username),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_record(username: str, record_id: int) -> bool:
    """删除一条记录；只允许本人操作，返回是否命中。"""
    conn = get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM records WHERE id = ? AND username = ?", (record_id, username)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _row_to_dict(r) -> dict:
    try:
        parsed = json.loads(r["parsed_json"]) if r["parsed_json"] else {}
    except (ValueError, TypeError):
        parsed = {}
    try:
        report = json.loads(r["report_json"]) if r["report_json"] else None
    except (ValueError, TypeError):
        report = None
    return {
        "id": r["id"],
        "record_time": r["record_time"],
        "raw_text": r["raw_text"],
        "parsed_data": parsed,
        "report": report,
    }


def get_records(username: str) -> list:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, record_time, raw_text, parsed_json, report_json FROM records "
            "WHERE username = ? ORDER BY record_time ASC", (username,)
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def get_record(username: str, record_id: int):
    conn = get_conn()
    try:
        r = conn.execute(
            "SELECT id, record_time, raw_text, parsed_json, report_json FROM records "
            "WHERE username = ? AND id = ?", (username, record_id)
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(r) if r else None


# ------------------------------------------------------------------ RBAC / 医生工作台

def list_staff_patients(role: str = "doctor", q: str = "", limit: int = 100) -> list:
    """医生只查看患者角色；管理员可查看所有账号（含医护人员）。"""
    limit = max(1, min(int(limit), 100))
    conn = get_conn()
    try:
        sql = "SELECT username, nickname, role, sex, created_at FROM users WHERE 1=1"
        args = []
        if role != "admin":
            sql += " AND role = 'user'"
        if q:
            sql += " AND (username LIKE ? OR nickname LIKE ?)"
            args.extend([f"%{q}%", f"%{q}%"])
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def get_record_global(record_id: int):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT username, id, record_time, raw_text, parsed_json, report_json "
            "FROM records WHERE id = ?", (record_id,)
        ).fetchone()
        return ({"username": row["username"], **_row_to_dict(row)}) if row else None
    finally:
        conn.close()


def list_diagnoses_for_record(record_id: int) -> list:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT id, record_id, doctor_username, title, impression, advice, follow_up, created_at "
            "FROM diagnoses WHERE record_id=? ORDER BY id DESC", (record_id,)
        ).fetchall()]
    finally:
        conn.close()


def add_diagnosis(record_id: int, doctor_username: str, data: dict) -> int:
    conn = get_conn()
    try:
        if not conn.execute("SELECT 1 FROM records WHERE id=?", (record_id,)).fetchone():
            raise ValueError("记录不存在")
        cur = conn.execute("""
            INSERT INTO diagnoses(record_id, doctor_username, title, impression, advice, follow_up, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (record_id, doctor_username, data["title"], data["impression"],
              data["advice"], data.get("follow_up", ""), datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_my_diagnoses(username: str) -> list:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute("""
            SELECT d.id, d.record_id, d.doctor_username, d.title, d.impression,
                   d.advice, d.follow_up, d.created_at, r.record_time
            FROM diagnoses d JOIN records r ON r.id = d.record_id
            WHERE r.username=? ORDER BY d.id DESC
        """, (username,)).fetchall()]
    finally:
        conn.close()


def audit_events(actor: str, action: str, target_username: str | None = None, record_id: int | None = None):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO audit_logs(actor_username, action, target_username, record_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (actor, action, target_username, record_id, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    finally:
        conn.close()


def admin_update_record(actor: str, record_id: int, raw_text: str, parsed: dict) -> bool:
    """单个事务保存修改与审计，不能绕过授权直接对外暴露。"""
    conn = get_conn()
    try:
        row = conn.execute("SELECT username FROM records WHERE id=?", (record_id,)).fetchone()
        if not row:
            return False
        conn.execute("""
            UPDATE records SET raw_text=?, parsed_json=?, report_json=NULL WHERE id=?
        """, (raw_text, json.dumps(parsed, ensure_ascii=False), record_id))
        conn.execute("""
            INSERT INTO audit_logs(actor_username, action, target_username, record_id, created_at)
            VALUES (?, 'admin.update_record', ?, ?, ?)
        """, (actor, row["username"], record_id, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return True
    finally:
        conn.close()


def admin_delete_record(actor: str, record_id: int) -> bool:
    conn = get_conn()
    try:
        row = conn.execute("SELECT username FROM records WHERE id=?", (record_id,)).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM records WHERE id=?", (record_id,))
        conn.execute("""
            INSERT INTO audit_logs(actor_username, action, target_username, record_id, created_at)
            VALUES (?, 'admin.delete_record', ?, ?, ?)
        """, (actor, row["username"], record_id, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return True
    finally:
        conn.close()


def admin_create_record(actor: str, username: str, raw_text: str, parsed: dict) -> int:
    conn = get_conn()
    try:
        if not conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise ValueError("用户不存在")
        cur = conn.execute("""
            INSERT INTO records(username, raw_text, parsed_json, record_time)
            VALUES (?, ?, ?, ?)
        """, (username, raw_text, json.dumps(parsed, ensure_ascii=False),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        rid = cur.lastrowid
        conn.execute("""
            INSERT INTO audit_logs(actor_username, action, target_username, record_id, created_at)
            VALUES (?, 'admin.create_record', ?, ?, ?)
        """, (actor, username, rid, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return rid
    finally:
        conn.close()


def admin_set_role(actor: str, username: str, role: str) -> bool:
    if role not in ("user", "doctor", "admin") or actor == username:
        return False
    conn = get_conn()
    try:
        cur = conn.execute("UPDATE users SET role=? WHERE username=?", (role, username))
        if cur.rowcount:
            conn.execute("""
                INSERT INTO audit_logs(actor_username, action, target_username, created_at)
                VALUES (?, 'admin.change_role', ?, ?)
            """, (actor, username, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
