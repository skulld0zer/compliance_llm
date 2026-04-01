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

    confidence = (
        retrieval_strength * 0.45
        + coverage * 0.20
        + decision_clarity * 0.20
        + citation_strength * 0.15
    )

    breakdown = {
        "retrieval_strength": round(retrieval_strength, 2),
        "coverage": round(coverage, 2),
        "decision_clarity": round(decision_clarity, 2),
        "citation_strength": round(citation_strength, 2),
    }

    confidence = round(_clamp(confidence), 2)
    return (confidence, breakdown) if return_breakdown else confidence
