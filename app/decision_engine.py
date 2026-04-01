import re


EMPLOYMENT_TERMS = {
    "employee", "employees", "worker", "workers", "workplace", "employer",
    "hr", "human resources", "staff", "hiring", "recruitment", "candidate",
    "promotion", "termination", "performance review", "productivity", "manager",
}

MONITORING_TERMS = {
    "monitor", "monitoring", "track", "tracking", "surveillance", "watch",
    "screen capture", "screenshot", "keystroke", "keystrokes", "location tracking",
    "activity logging", "usage analytics", "behavioral monitoring", "real-time tracking",
}

BIOMETRIC_IDENTITY_TERMS = {
    "biometric", "biometrics", "face recognition", "facial recognition",
    "fingerprint", "iris", "retina", "voiceprint", "speaker identification",
    "speaker verification", "gait recognition", "identity verification",
}

EMOTION_TERMS = {
    "emotion recognition", "emotion detection", "sentiment from voice",
    "affect detection", "mood detection", "emotion analysis",
    "detect emotions", "infer emotions", "emotion from voice",
    "emotions from voice", "emotion inference",
}

VOICE_AUDIO_TERMS = {
    "voice", "vocal", "speech", "audio", "singing", "song", "vocals",
    "voice cloning", "voice synthesis", "voice generation", "tts",
}

DEEPFAKE_TERMS = {
    "deepfake", "synthetic voice", "voice clone", "clone a voice",
    "face swap", "synthetic media", "manipulated audio", "manipulated video",
}

DECISION_IMPACT_TERMS = {
    "decision", "decisions", "evaluate", "evaluation", "score", "ranking",
    "screening", "approve", "reject", "promotion", "termination",
}


def _normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def _contains_any(text, terms):
    matches = []
    for term in terms:
        if term in text:
            matches.append(term)
    return matches


def _decision_step(step, value, detail, matches=None):
    return {
        "step": step,
        "value": value,
        "detail": detail,
        "matches": matches or [],
    }


def analyze_question(question):
    q = _normalize(question)

    monitoring_matches = _contains_any(q, MONITORING_TERMS)
    employment_matches = _contains_any(q, EMPLOYMENT_TERMS)
    biometric_identity_matches = _contains_any(q, BIOMETRIC_IDENTITY_TERMS)
    emotion_matches = _contains_any(q, EMOTION_TERMS)
    voice_audio_matches = _contains_any(q, VOICE_AUDIO_TERMS)
    deepfake_matches = _contains_any(q, DEEPFAKE_TERMS)
    decision_impact_matches = _contains_any(q, DECISION_IMPACT_TERMS)

    monitoring = bool(monitoring_matches)
    employment = bool(employment_matches)
    biometric_identification = bool(biometric_identity_matches)
    emotion_recognition = bool(emotion_matches)
    voice_or_audio = bool(voice_audio_matches)
    synthetic_media = bool(deepfake_matches)
    employment_decision_impact = bool(employment and decision_impact_matches)

    # Important nuance: plain "voice" or "audio" is not automatically biometric use.
    biometric_usage = biometric_identification or emotion_recognition

    steps = [
        _decision_step(
            "surveillance_detected",
            monitoring,
            "Checks whether the description includes monitoring, tracking, or surveillance behavior.",
            monitoring_matches,
        ),
        _decision_step(
            "employment_context",
            employment,
            "Checks whether the use case sits in a workplace, HR, or employment setting.",
            employment_matches,
        ),
        _decision_step(
            "employment_decision_impact",
            employment_decision_impact,
            "Checks whether the system influences employment decisions such as hiring, promotion, evaluation, or termination.",
            decision_impact_matches if employment else [],
        ),
        _decision_step(
            "biometric_identification",
            biometric_identification,
            "Checks for explicit biometric identification or verification signals.",
            biometric_identity_matches,
        ),
        _decision_step(
            "emotion_recognition",
            emotion_recognition,
            "Checks for explicit emotion or affect inference claims.",
            emotion_matches,
        ),
        _decision_step(
            "synthetic_media_generation",
            synthetic_media,
            "Checks whether the system appears to generate or manipulate synthetic media such as cloned voices or deepfakes.",
            deepfake_matches,
        ),
        _decision_step(
            "voice_audio_processing",
            voice_or_audio,
            "Checks for general voice or audio processing. This alone does not imply biometric identification.",
            voice_audio_matches,
        ),
        _decision_step(
            "biometric_usage",
            biometric_usage,
            "Aggregated biometric signal: true only for explicit biometric identification or emotion recognition indicators.",
            biometric_identity_matches + emotion_matches,
        ),
    ]

    hints = []
    pre_classification = "unclear"

    if employment and monitoring:
        pre_classification = "potential_high_risk"
        hints.append(
            "Potential Annex III employment-related high-risk scenario because the system appears to monitor people in a workplace context."
        )

    if employment_decision_impact:
        pre_classification = "high_risk_candidate"
        hints.append(
            "The description suggests the system may influence employment decisions, which is a strong high-risk signal under Annex III employment use cases."
        )

    if emotion_recognition and employment:
        pre_classification = "sensitive_prohibited_or_high_risk_candidate"
        hints.append(
            "Emotion recognition in a workplace context requires careful assessment because it is specifically sensitive under the EU AI Act."
        )
    elif emotion_recognition:
        hints.append(
            "The description suggests emotion recognition, so the answer should assess that specifically and avoid collapsing it into generic voice processing."
        )
    elif biometric_identification:
        hints.append(
            "The description mentions explicit biometric identification or verification, so the answer should distinguish identification, verification, and simple media processing."
        )
    elif voice_or_audio and not biometric_usage:
        hints.append(
            "General voice or audio processing is present, but this alone should not be treated as biometric identification or emotion recognition."
        )

    if synthetic_media:
        hints.append(
            "The use case appears to involve synthetic or manipulated media, so the answer should address transparency and disclosure obligations instead of assuming Annex III high-risk classification."
        )
        if pre_classification == "unclear":
            pre_classification = "transparency_candidate"

    if not hints:
        hints.append(
            "The description is still incomplete. Focus on whether the system monitors people, affects employment decisions, or performs biometric identification or emotion recognition."
        )

    return {
        "decision_tree": steps,
        "hints": hints,
        "pre_classification": pre_classification,
    }


def generate_followups(decision_tree):
    questions = []
    steps = {s["step"]: s["value"] for s in decision_tree}

    if steps.get("surveillance_detected") and steps.get("employment_context"):
        questions.append(
            "Does the system make or influence decisions affecting employment, such as hiring, promotion, termination, or performance evaluation?"
        )
        questions.append(
            "What exact data is collected or observed, for example keystrokes, screenshots, app usage, location, camera, or audio?"
        )
        questions.append(
            "Is the monitoring continuous, real-time, or only occasional and event-based?"
        )
        return questions[:3]

    if steps.get("voice_audio_processing") and not steps.get("biometric_identification"):
        questions.append(
            "Does the system use voice only to generate or modify audio, or does it identify, verify, or authenticate a person based on their voice?"
        )

    if steps.get("voice_audio_processing") and not steps.get("emotion_recognition"):
        questions.append(
            "Does the system infer emotions, mood, stress, or mental state from voice, facial signals, or behavior?"
        )

    if not steps.get("surveillance_detected"):
        questions.append("Is your system monitoring or tracking individuals in any way?")

    if not steps.get("employment_context"):
        questions.append("Is the system used in an employment, HR, or workplace context?")

    if not steps.get("biometric_identification") and not steps.get("emotion_recognition"):
        questions.append(
            "Does the system use biometric identification, verification, or emotion recognition, for example face recognition, voiceprint matching, or affect detection?"
        )

    return questions[:3]
