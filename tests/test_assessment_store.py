import shutil
import uuid
from pathlib import Path

from app import assessment_store


def test_store_initializes_empty(monkeypatch):
    test_root = Path("tests") / "_tmp" / f"store_{uuid.uuid4().hex}"
    try:
        store_path = test_root / "assessments" / "assessments.json"
        monkeypatch.setattr(assessment_store, "STORE_PATH", str(store_path))

        assert assessment_store.load_assessments() == []
        assert store_path.exists()
    finally:
        shutil.rmtree(test_root, ignore_errors=True)


def test_upsert_update_and_delete_assessment(monkeypatch):
    test_root = Path("tests") / "_tmp" / f"store_{uuid.uuid4().hex}"
    try:
        store_path = test_root / "assessments" / "assessments.json"
        monkeypatch.setattr(assessment_store, "STORE_PATH", str(store_path))

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

        assessment_store.update_assessment_status(saved["id"], "In Review")
        updated = assessment_store.load_assessments()
        assert updated[0]["status"] == "In Review"

        assessment_store.delete_assessment(saved["id"])
        assert assessment_store.load_assessments() == []
    finally:
        shutil.rmtree(test_root, ignore_errors=True)
