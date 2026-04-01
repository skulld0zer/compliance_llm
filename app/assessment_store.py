import json
import os
from datetime import datetime, timezone


STORE_PATH = os.path.join("data", "assessments", "assessments.json")
DEFAULT_STATUSES = ["Draft", "Needs More Info", "In Review", "Approved"]


def _ensure_store():
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    if not os.path.exists(STORE_PATH):
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_assessments():
    _ensure_store()
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []

    if not isinstance(data, list):
        return []

    return sorted(data, key=lambda item: item.get("updated_at", ""), reverse=True)


def save_all_assessments(assessments):
    _ensure_store()
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(assessments, f, indent=2, ensure_ascii=True)


def upsert_assessment(assessment):
    assessments = load_assessments()
    now = datetime.now(timezone.utc).isoformat()

    if not assessment.get("id"):
        assessment["id"] = now.replace(":", "").replace("-", "").replace(".", "")
        assessment["created_at"] = now

    assessment["updated_at"] = now

    updated = False
    for idx, item in enumerate(assessments):
        if item.get("id") == assessment["id"]:
            assessment["created_at"] = item.get("created_at", assessment["created_at"])
            assessments[idx] = assessment
            updated = True
            break

    if not updated:
        assessments.append(assessment)

    save_all_assessments(sorted(assessments, key=lambda item: item.get("updated_at", ""), reverse=True))
    return assessment


def update_assessment_status(assessment_id, status):
    assessments = load_assessments()
    now = datetime.now(timezone.utc).isoformat()

    for item in assessments:
        if item.get("id") == assessment_id:
            item["status"] = status
            item["updated_at"] = now
            break

    save_all_assessments(sorted(assessments, key=lambda item: item.get("updated_at", ""), reverse=True))


def delete_assessment(assessment_id):
    assessments = load_assessments()
    assessments = [item for item in assessments if item.get("id") != assessment_id]
    save_all_assessments(sorted(assessments, key=lambda item: item.get("updated_at", ""), reverse=True))
