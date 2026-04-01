import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone


DB_PATH = os.path.join("data", "assessments", "assessments.db")
LEGACY_JSON_PATH = os.path.join("data", "assessments", "assessments.json")
DEFAULT_STATUSES = ["Draft", "Needs More Info", "In Review", "Approved"]
_MEMORY_CONNECTION = None


def _sqlite_connect():
    global _MEMORY_CONNECTION
    if DB_PATH == ":memory:":
        if _MEMORY_CONNECTION is None:
            _MEMORY_CONNECTION = sqlite3.connect(":memory:")
        return _MEMORY_CONNECTION
    return sqlite3.connect(DB_PATH)


def _ensure_store():
    if DB_PATH != ":memory:":
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _sqlite_connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
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
        conn.commit()
    finally:
        if DB_PATH != ":memory:":
            conn.close()

    _migrate_legacy_json_if_present()


def _connect():
    _ensure_store()
    conn = _sqlite_connect()
    conn.row_factory = sqlite3.Row
    return conn


def _serialize(value, fallback):
    return json.dumps(value if value is not None else fallback, ensure_ascii=True)


def _deserialize(text, fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return fallback


def _row_to_assessment(row):
    return {
        "id": row["id"],
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
    global _MEMORY_CONNECTION
    legacy_items = _legacy_json_items()
    if not legacy_items:
        return

    conn = _sqlite_connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0]
        if count > 0:
            return

        for item in legacy_items:
            conn.execute(
                """
                INSERT OR REPLACE INTO assessments (
                    id, title, status, classification, confidence, messages_json,
                    follow_up_json, resolved_followups_json, debug_json, summary,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("id") or uuid.uuid4().hex,
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
        if DB_PATH != ":memory:":
            conn.close()


def load_assessments():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM assessments ORDER BY updated_at DESC"
        ).fetchall()
    return [_row_to_assessment(row) for row in rows]


def upsert_assessment(assessment):
    now = datetime.now(timezone.utc).isoformat()
    assessment_id = assessment.get("id") or uuid.uuid4().hex

    with _connect() as conn:
        existing = conn.execute(
            "SELECT created_at FROM assessments WHERE id = ?",
            (assessment_id,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now

        payload = {
            "id": assessment_id,
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

        conn.execute(
            """
            INSERT OR REPLACE INTO assessments (
                id, title, status, classification, confidence, messages_json,
                follow_up_json, resolved_followups_json, debug_json, summary,
                created_at, updated_at
            ) VALUES (
                :id, :title, :status, :classification, :confidence, :messages_json,
                :follow_up_json, :resolved_followups_json, :debug_json, :summary,
                :created_at, :updated_at
            )
            """,
            payload,
        )
        conn.commit()

    return {
        "id": assessment_id,
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
    with _connect() as conn:
        conn.execute(
            "UPDATE assessments SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, assessment_id),
        )
        conn.commit()


def delete_assessment(assessment_id):
    with _connect() as conn:
        conn.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))
        conn.commit()
