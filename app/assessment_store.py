import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None


DB_PATH = os.path.join("data", "assessments", "assessments.db")
LEGACY_JSON_PATH = os.path.join("data", "assessments", "assessments.json")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "").strip()
DEFAULT_STATUSES = ["Draft", "Needs More Info", "In Review", "Approved"]
_MEMORY_CONNECTION = None
POSTGRES_CONNECT_TIMEOUT_SECONDS = 5
POSTGRES_DISABLE_SECONDS = 300
_POSTGRES_DISABLED_UNTIL = 0.0


def _is_postgres():
    return bool(
        SUPABASE_DB_URL
        and DB_PATH != ":memory:"
        and time.time() >= _POSTGRES_DISABLED_UNTIL
    )


def _sqlite_connect():
    global _MEMORY_CONNECTION
    if DB_PATH == ":memory:":
        if _MEMORY_CONNECTION is None:
            _MEMORY_CONNECTION = sqlite3.connect(":memory:")
        return _MEMORY_CONNECTION
    return sqlite3.connect(DB_PATH)


def _postgres_connect():
    global _POSTGRES_DISABLED_UNTIL
    if psycopg is None:
        raise RuntimeError("psycopg is required for Supabase/Postgres connections.")
    try:
        return psycopg.connect(
            SUPABASE_DB_URL,
            row_factory=dict_row,
            connect_timeout=POSTGRES_CONNECT_TIMEOUT_SECONDS,
            sslmode="require",
        )
    except Exception:
        _POSTGRES_DISABLED_UNTIL = time.time() + POSTGRES_DISABLE_SECONDS
        raise


def _connect():
    if _is_postgres():
        try:
            return _postgres_connect()
        except Exception:
            pass
    conn = _sqlite_connect()
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_store():
    if _is_postgres():
        try:
            _ensure_postgres_store()
        except Exception:
            _ensure_sqlite_store()
    else:
        _ensure_sqlite_store()
    _migrate_legacy_json_if_present()


def _ensure_sqlite_store():
    if DB_PATH != ":memory:":
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _sqlite_connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
                issue_key TEXT UNIQUE,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                classification TEXT,
                confidence REAL DEFAULT 0,
                messages_json TEXT NOT NULL,
                follow_up_json TEXT NOT NULL,
                resolved_followups_json TEXT NOT NULL,
                debug_json TEXT NOT NULL,
                summary TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(assessments)").fetchall()
        }
        if "issue_key" not in columns:
            conn.execute("ALTER TABLE assessments ADD COLUMN issue_key TEXT")
        _backfill_issue_keys(conn)
        conn.commit()
    finally:
        if DB_PATH != ":memory:":
            conn.close()


def _ensure_postgres_store():
    conn = _postgres_connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
                issue_key TEXT UNIQUE,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                classification TEXT,
                confidence DOUBLE PRECISION DEFAULT 0,
                messages_json TEXT NOT NULL,
                follow_up_json TEXT NOT NULL,
                resolved_followups_json TEXT NOT NULL,
                debug_json TEXT NOT NULL,
                summary TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        _backfill_issue_keys(conn)
        conn.commit()
    finally:
        conn.close()


def _serialize(value, fallback):
    return json.dumps(value if value is not None else fallback, ensure_ascii=True)


def _deserialize(text, fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return fallback


def _first_value(row):
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return row[0]
    if isinstance(row, dict):
        return next(iter(row.values()))
    return row[0]


def _row_to_assessment(row):
    return {
        "id": row["id"],
        "issue_key": row["issue_key"] or "",
        "title": row["title"],
        "status": row["status"],
        "classification": row["classification"] or "",
        "confidence": float(row["confidence"] or 0.0),
        "messages": _deserialize(row["messages_json"], []),
        "follow_up": _deserialize(row["follow_up_json"], []),
        "resolved_followups": _deserialize(row["resolved_followups_json"], []),
        "debug": _deserialize(row["debug_json"], {}),
        "summary": row["summary"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _legacy_json_items():
    if not os.path.exists(LEGACY_JSON_PATH):
        return []
    try:
        with open(LEGACY_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _migrate_legacy_json_if_present():
    legacy_items = _legacy_json_items()
    if not legacy_items:
        return

    conn = _connect()
    try:
        count = _first_value(conn.execute("SELECT COUNT(*) FROM assessments").fetchone())
        if count > 0:
            return

        insert_sql = (
            """
            INSERT INTO assessments (
                id, issue_key, title, status, classification, confidence, messages_json,
                follow_up_json, resolved_followups_json, debug_json, summary,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            if _is_postgres()
            else
            """
            INSERT OR REPLACE INTO assessments (
                id, issue_key, title, status, classification, confidence, messages_json,
                follow_up_json, resolved_followups_json, debug_json, summary,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )

        for item in legacy_items:
            conn.execute(
                insert_sql,
                (
                    item.get("id") or uuid.uuid4().hex,
                    item.get("issue_key", ""),
                    item.get("title", "Untitled assessment"),
                    item.get("status", "Draft"),
                    item.get("classification", ""),
                    float(item.get("confidence", 0.0) or 0.0),
                    _serialize(item.get("messages"), []),
                    _serialize(item.get("follow_up"), []),
                    _serialize(item.get("resolved_followups"), []),
                    _serialize(item.get("debug"), {}),
                    item.get("summary", ""),
                    item.get("created_at") or datetime.now(timezone.utc).isoformat(),
                    item.get("updated_at") or datetime.now(timezone.utc).isoformat(),
                ),
            )
        conn.commit()
    finally:
        if _is_postgres() or DB_PATH != ":memory:":
            conn.close()


def load_assessments():
    _ensure_store()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM assessments ORDER BY updated_at DESC"
        ).fetchall()
    return [_row_to_assessment(row) for row in rows]


def _next_issue_key(conn):
    rows = conn.execute("SELECT issue_key FROM assessments WHERE issue_key IS NOT NULL AND issue_key != ''").fetchall()
    highest = 0
    for row in rows:
        issue_key = row["issue_key"] if isinstance(row, (sqlite3.Row, dict)) else row[0]
        try:
            highest = max(highest, int(str(issue_key).split("-")[-1]))
        except (ValueError, TypeError):
            continue
    return f"COMPL-{highest + 1:03d}"


def _backfill_issue_keys(conn):
    rows = conn.execute(
        "SELECT id, issue_key FROM assessments ORDER BY created_at ASC, id ASC"
    ).fetchall()
    next_number = 1
    for row in rows:
        current = row["issue_key"] if isinstance(row, (sqlite3.Row, dict)) else row[1]
        assessment_id = row["id"] if isinstance(row, (sqlite3.Row, dict)) else row[0]
        if current:
            try:
                next_number = max(next_number, int(str(current).split("-")[-1]) + 1)
            except (ValueError, TypeError):
                pass
            continue
        if _is_postgres():
            conn.execute(
                "UPDATE assessments SET issue_key = %s WHERE id = %s",
                (f"COMPL-{next_number:03d}", assessment_id),
            )
        else:
            conn.execute(
                "UPDATE assessments SET issue_key = ? WHERE id = ?",
                (f"COMPL-{next_number:03d}", assessment_id),
            )
        next_number += 1


def upsert_assessment(assessment):
    now = datetime.now(timezone.utc).isoformat()
    assessment_id = assessment.get("id") or uuid.uuid4().hex

    _ensure_store()
    with _connect() as conn:
        select_sql = "SELECT created_at, issue_key FROM assessments WHERE id = %s" if _is_postgres() else "SELECT created_at, issue_key FROM assessments WHERE id = ?"
        existing = conn.execute(select_sql, (assessment_id,)).fetchone()
        created_at = existing["created_at"] if existing else now
        issue_key = existing["issue_key"] if existing and existing["issue_key"] else _next_issue_key(conn)

        payload = {
            "id": assessment_id,
            "issue_key": issue_key,
            "title": assessment.get("title", "Untitled assessment"),
            "status": assessment.get("status", "Draft"),
            "classification": assessment.get("classification", ""),
            "confidence": float(assessment.get("confidence", 0.0) or 0.0),
            "messages_json": _serialize(assessment.get("messages"), []),
            "follow_up_json": _serialize(assessment.get("follow_up"), []),
            "resolved_followups_json": _serialize(assessment.get("resolved_followups"), []),
            "debug_json": _serialize(assessment.get("debug"), {}),
            "summary": assessment.get("summary", ""),
            "created_at": created_at,
            "updated_at": now,
        }

        if _is_postgres():
            conn.execute(
                """
                INSERT INTO assessments (
                    id, issue_key, title, status, classification, confidence, messages_json,
                    follow_up_json, resolved_followups_json, debug_json, summary,
                    created_at, updated_at
                ) VALUES (
                    %(id)s, %(issue_key)s, %(title)s, %(status)s, %(classification)s, %(confidence)s, %(messages_json)s,
                    %(follow_up_json)s, %(resolved_followups_json)s, %(debug_json)s, %(summary)s,
                    %(created_at)s, %(updated_at)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    issue_key = EXCLUDED.issue_key,
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    classification = EXCLUDED.classification,
                    confidence = EXCLUDED.confidence,
                    messages_json = EXCLUDED.messages_json,
                    follow_up_json = EXCLUDED.follow_up_json,
                    resolved_followups_json = EXCLUDED.resolved_followups_json,
                    debug_json = EXCLUDED.debug_json,
                    summary = EXCLUDED.summary,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at
                """,
                payload,
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO assessments (
                    id, issue_key, title, status, classification, confidence, messages_json,
                    follow_up_json, resolved_followups_json, debug_json, summary,
                    created_at, updated_at
                ) VALUES (
                    :id, :issue_key, :title, :status, :classification, :confidence, :messages_json,
                    :follow_up_json, :resolved_followups_json, :debug_json, :summary,
                    :created_at, :updated_at
                )
                """,
                payload,
            )
        conn.commit()

    return {
        "id": assessment_id,
        "issue_key": payload["issue_key"],
        "title": payload["title"],
        "status": payload["status"],
        "classification": payload["classification"],
        "confidence": payload["confidence"],
        "messages": _deserialize(payload["messages_json"], []),
        "follow_up": _deserialize(payload["follow_up_json"], []),
        "resolved_followups": _deserialize(payload["resolved_followups_json"], []),
        "debug": _deserialize(payload["debug_json"], {}),
        "summary": payload["summary"],
        "created_at": payload["created_at"],
        "updated_at": payload["updated_at"],
    }


def update_assessment_status(assessment_id, status):
    now = datetime.now(timezone.utc).isoformat()
    _ensure_store()
    with _connect() as conn:
        if _is_postgres():
            conn.execute(
                "UPDATE assessments SET status = %s, updated_at = %s WHERE id = %s",
                (status, now, assessment_id),
            )
        else:
            conn.execute(
                "UPDATE assessments SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, assessment_id),
            )
        conn.commit()


def delete_assessment(assessment_id):
    _ensure_store()
    with _connect() as conn:
        if _is_postgres():
            conn.execute("DELETE FROM assessments WHERE id = %s", (assessment_id,))
        else:
            conn.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))
        conn.commit()
