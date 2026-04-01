from app.confidence import calculate_confidence


def test_calculate_confidence_returns_zero_when_no_results():
    confidence, breakdown = calculate_confidence([], {}, {"answer": "", "classification": "unclear"}, return_breakdown=True)

    assert confidence == 0.0
    assert breakdown["retrieval_strength"] == 0.0


def test_confidence_rewards_clear_consistent_and_cited_answers():
    strong_results = [
        {"score": 0.15, "locator": "Article 50, paragraph 2"},
        {"score": 0.25, "locator": "Article 53, paragraph 1"},
        {"score": 0.35, "locator": "Annex III, paragraph 4"},
    ]
    strong_decision = {
        "pre_classification": "high_risk_candidate",
        "decision_tree": [
            {"step": "surveillance_detected", "value": True},
            {"step": "employment_context", "value": True},
            {"step": "employment_decision_impact", "value": True},
        ],
    }
    strong_answer = {
        "classification": "high-risk",
        "answer": "This is high-risk under [Article 6, paragraph 1] and [Annex III, paragraph 4].",
    }

    weak_results = [
        {"score": 1.9, "locator": ""},
    ]
    weak_decision = {
        "pre_classification": "minimal_candidate",
        "decision_tree": [
            {"step": "personal_assistant_context", "value": True},
        ],
    }
    weak_answer = {
        "classification": "unclear",
        "answer": "This might depend and could potentially be unclear.",
    }

    strong_confidence = calculate_confidence(strong_results, strong_decision, strong_answer)
    weak_confidence = calculate_confidence(weak_results, weak_decision, weak_answer)

    assert strong_confidence > weak_confidence
    assert strong_confidence >= 0.6
