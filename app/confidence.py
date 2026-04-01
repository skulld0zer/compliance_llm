import json
import re


def _clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def _answer_text(answer):
    if isinstance(answer, dict):
        return str(answer.get("answer", ""))

    if isinstance(answer, str):
        try:
            parsed = json.loads(answer)
            if isinstance(parsed, dict):
                return str(parsed.get("answer", answer))
        except Exception:
            return answer

    return str(answer)


def calculate_confidence(results, decision_data, answer, return_breakdown=False):
    if not results:
        breakdown = {
            "retrieval_strength": 0.0,
            "coverage": 0.0,
            "decision_clarity": 0.0,
            "citation_strength": 0.0,
        }
        return (0.0, breakdown) if return_breakdown else 0.0

    distances = [max(float(r.get("score", 0.0)), 0.0) for r in results]
    similarities = [1 / (1 + distance) for distance in distances]

    top_similarity = max(similarities)
    avg_similarity = sum(similarities) / len(similarities)
    retrieval_strength = _clamp((top_similarity * 0.6) + (avg_similarity * 0.4))

    coverage = _clamp(len(results) / 5)

    steps = decision_data.get("decision_tree", []) if isinstance(decision_data, dict) else []
    if steps:
        true_ratio = sum(1 for step in steps if step.get("value")) / len(steps)
        decision_clarity = 0.35 + (0.65 * true_ratio)
    else:
        decision_clarity = 0.35
    decision_clarity = _clamp(decision_clarity)

    answer_text = _answer_text(answer)
    legal_refs = re.findall(r"\[(.*?)\]", answer_text)
    citation_strength = _clamp(len(legal_refs) / 3)

    locator_quality = sum(
        1 for result in results
        if result.get("locator") and "paragraph" in str(result.get("locator", "")).lower()
    )
    locator_quality = _clamp(locator_quality / max(len(results), 1))

    pre_classification = str(decision_data.get("pre_classification", "")) if isinstance(decision_data, dict) else ""
    answer_classification = ""
    if isinstance(answer, dict):
        answer_classification = str(answer.get("classification", "")).lower()
    elif isinstance(answer, str):
        try:
            parsed = json.loads(answer)
            if isinstance(parsed, dict):
                answer_classification = str(parsed.get("classification", "")).lower()
        except Exception:
            answer_classification = ""

    consistency_score = 0.55
    if pre_classification == "high_risk_candidate" and answer_classification == "high-risk":
        consistency_score = 1.0
    elif pre_classification == "transparency_candidate" and answer_classification == "transparency":
        consistency_score = 1.0
    elif pre_classification == "minimal_candidate" and answer_classification == "minimal":
        consistency_score = 1.0
    elif pre_classification == "unclear" and answer_classification == "unclear":
        consistency_score = 0.75
    elif pre_classification and answer_classification:
        consistency_score = 0.45

    uncertainty_terms = [
        "could potentially", "might", "may", "unclear", "insufficient", "depends"
    ]
    uncertainty_penalty = 0.0
    lowered_answer = answer_text.lower()
    if any(term in lowered_answer for term in uncertainty_terms):
        uncertainty_penalty = 0.08

    confidence = (
        retrieval_strength * 0.34
        + coverage * 0.16
        + decision_clarity * 0.16
        + citation_strength * 0.14
        + locator_quality * 0.10
        + consistency_score * 0.10
    )

    confidence = _clamp(confidence - uncertainty_penalty)

    breakdown = {
        "retrieval_strength": round(retrieval_strength, 2),
        "coverage": round(coverage, 2),
        "decision_clarity": round(decision_clarity, 2),
        "citation_strength": round(citation_strength, 2),
        "locator_quality": round(locator_quality, 2),
        "consistency": round(consistency_score, 2),
    }

    confidence = round(_clamp(confidence), 2)
    return (confidence, breakdown) if return_breakdown else confidence
