def analyze_question(question):
    q = question.lower()

    steps = []

    surveillance = "monitor" in q or "track" in q
    employment = "employee" in q or "worker" in q
    biometric = any(x in q for x in ["biometric", "face", "emotion", "voice"])

    steps.append({"step": "surveillance_detected", "value": surveillance})
    steps.append({"step": "employment_context", "value": employment})
    steps.append({"step": "biometric_usage", "value": biometric})

    return {
        "decision_tree": steps,
        "hints": [],
        "pre_classification": "unclear"
    }


# 🔥 INTELLIGENTE FOLLOWUPS
def generate_followups(decision_tree):
    questions = []

    steps = {s["step"]: s["value"] for s in decision_tree}

    # ALWAYS ask these if surveillance + employment → HIGH RISK scenario
    if steps.get("surveillance_detected") and steps.get("employment_context"):

        questions.append(
            "Does the system make or influence decisions affecting employment (e.g. promotion, termination, performance evaluation)?"
        )

        questions.append(
            "What exact data is collected (e.g. application usage, keystrokes, screenshots, location)?"
        )

        questions.append(
            "Is the monitoring continuous (real-time tracking) or occasional/event-based?"
        )

    else:
        # fallback for unclear cases
        if not steps.get("surveillance_detected"):
            questions.append("Is your system monitoring or tracking individuals in any way?")

        if not steps.get("employment_context"):
            questions.append("Is the system used in an employment or workplace context?")

        if not steps.get("biometric_usage"):
            questions.append("Does the system use biometric data (face, voice, emotion)?")

    return questions[:3]