from app.decision_engine import analyze_question, generate_followups


def _step_map(result):
    return {step["step"]: step["value"] for step in result["decision_tree"]}


def test_personal_calendar_assistant_is_minimal_candidate():
    question = "Can I use AI to track my own personal calendar and notify me if I booked two meetings at the same time?"

    result = analyze_question(question)
    steps = _step_map(result)

    assert result["pre_classification"] == "minimal_candidate"
    assert steps["personal_assistant_context"] is True
    assert steps["surveillance_detected"] is False
    assert generate_followups(result["decision_tree"]) == []


def test_employee_monitoring_case_is_high_risk_candidate():
    question = (
        "Can I monitor the productivity of my employees by utilizing AI based surveillance "
        "software that monitors their screen activity during work hours?"
    )

    result = analyze_question(question)
    steps = _step_map(result)
    followups = generate_followups(result["decision_tree"])

    assert result["pre_classification"] in {"potential_high_risk", "high_risk_candidate"}
    assert steps["surveillance_detected"] is True
    assert steps["employment_context"] is True
    assert len(followups) == 3


def test_employee_marketing_images_without_consent_is_transparency_candidate():
    question = "Can I generate marketing images with AI of my employees without their consent?"

    result = analyze_question(question)
    steps = _step_map(result)

    assert result["pre_classification"] == "transparency_candidate"
    assert steps["image_or_likeness_usage"] is True
    assert steps["marketing_or_promotional_use"] is True
    assert steps["consent_sensitive_context"] is True


def test_employment_promotion_language_does_not_trigger_marketing_use():
    question = (
        "Does the system make or influence decisions affecting employment, such as hiring, "
        "promotion, termination, or performance evaluation?"
    )

    result = analyze_question(question)
    steps = _step_map(result)

    assert steps["employment_context"] is True
    assert steps["marketing_or_promotional_use"] is False
