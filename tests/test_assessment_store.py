import shutil
import uuid
from pathlib import Path

from app import assessment_store


def test_store_initializes_empty(monkeypatch):
    test_root = Path("tests") / "_tmp" / f"store_{uuid.uuid4().hex}"
    try:
        legacy_path = test_root / "assessments" / "assessments.json"
        monkeypatch.setattr(assessment_store, "DB_PATH", ":memory:")
        monkeypatch.setattr(assessment_store, "LEGACY_JSON_PATH", str(legacy_path))
        monkeypatch.setattr(assessment_store, "_MEMORY_CONNECTION", None)

        assert assessment_store.load_assessments() == []
    finally:
        if assessment_store._MEMORY_CONNECTION is not None:
            assessment_store._MEMORY_CONNECTION.close()
            assessment_store._MEMORY_CONNECTION = None
        shutil.rmtree(test_root, ignore_errors=True)


def test_upsert_update_and_delete_assessment(monkeypatch):
    test_root = Path("tests") / "_tmp" / f"store_{uuid.uuid4().hex}"
    try:
        legacy_path = test_root / "assessments" / "assessments.json"
        monkeypatch.setattr(assessment_store, "DB_PATH", ":memory:")
        monkeypatch.setattr(assessment_store, "LEGACY_JSON_PATH", str(legacy_path))
        monkeypatch.setattr(assessment_store, "_MEMORY_CONNECTION", None)

        saved = assessment_store.upsert_assessment(
            {
                "title": "Employee monitoring case",
                "status": "Draft",
                "classification": "high-risk",
                "confidence": 0.73,
                "messages": [],
                "follow_up": [],
                "resolved_followups": [],
                "debug": {"classification": "high-risk"},
                "summary": "Summary",
            }
        )

        loaded = assessment_store.load_assessments()
        assert len(loaded) == 1
        assert loaded[0]["title"] == "Employee monitoring case"
        assert loaded[0]["id"] == saved["id"]
        assert loaded[0]["issue_key"] == "COMPL-001"

        assessment_store.update_assessment_status(saved["id"], "In Review")
        updated = assessment_store.load_assessments()
        assert updated[0]["status"] == "In Review"

        assessment_store.delete_assessment(saved["id"])
        assert assessment_store.load_assessments() == []
    finally:
        if assessment_store._MEMORY_CONNECTION is not None:
            assessment_store._MEMORY_CONNECTION.close()
            assessment_store._MEMORY_CONNECTION = None
        shutil.rmtree(test_root, ignore_errors=True)


def test_legacy_json_is_migrated_to_sqlite(monkeypatch):
    test_root = Path("tests") / "_tmp" / f"store_{uuid.uuid4().hex}"
    try:
        legacy_path = test_root / "assessments" / "assessments.json"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text(
            """
            [
              {
                "id": "legacy-1",
                "issue_key": "COMPL-009",
                "title": "Legacy assessment",
                "status": "Draft",
                "classification": "minimal",
                "confidence": 0.68,
                "messages": [],
                "follow_up": [],
                "resolved_followups": [],
                "debug": {},
                "summary": "Migrated"
              }
            ]
            """.strip(),
            encoding="utf-8",
        )
        monkeypatch.setattr(assessment_store, "DB_PATH", ":memory:")
        monkeypatch.setattr(assessment_store, "LEGACY_JSON_PATH", str(legacy_path))
        monkeypatch.setattr(assessment_store, "_MEMORY_CONNECTION", None)

        loaded = assessment_store.load_assessments()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "legacy-1"
        assert loaded[0]["title"] == "Legacy assessment"
        assert loaded[0]["issue_key"] == "COMPL-009"
    finally:
        if assessment_store._MEMORY_CONNECTION is not None:
            assessment_store._MEMORY_CONNECTION.close()
            assessment_store._MEMORY_CONNECTION = None
        shutil.rmtree(test_root, ignore_errors=True)
