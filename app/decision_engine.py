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
    "generate images", "generated images", "ai image", "ai images",
    "synthetic image", "synthetic images", "generated picture", "generated pictures",
}

DECISION_IMPACT_TERMS = {
    "decision", "decisions", "evaluate", "evaluation", "score", "ranking",
    "screening", "approve", "reject", "promotion", "termination",
}

IMAGE_TERMS = {
    "image", "images", "picture", "pictures", "photo", "photos",
    "portrait", "portraits", "face", "faces", "likeness",
}

MARKETING_TERMS = {
    "marketing", "advertising", "advertisement", "campaign",
    "promotional", "brand", "social media ad", "commercial use",
}

CONSENT_TERMS = {
    "consent", "without consent", "permission", "without permission",
    "authorisation", "authorization", "without approval",
}

SELF_USE_TERMS = {
    "my own", "for myself", "personal", "my calendar", "own calendar", "my meetings",
}

CALENDAR_ASSISTANCE_TERMS = {
    "calendar", "meetings", "meeting", "double booked", "double-booked",
    "schedule", "scheduling", "notify me", "remind me",
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
    image_matches = _contains_any(q, IMAGE_TERMS)
    marketing_matches = _contains_any(q, MARKETING_TERMS)
    consent_matches = _contains_any(q, CONSENT_TERMS)
    self_use_matches = _contains_any(q, SELF_USE_TERMS)
    calendar_assistance_matches = _contains_any(q, CALENDAR_ASSISTANCE_TERMS)

    monitoring = bool(monitoring_matches)
    employment = bool(employment_matches)
    biometric_identification = bool(biometric_identity_matches)
    emotion_recognition = bool(emotion_matches)
    voice_or_audio = bool(voice_audio_matches)
    synthetic_media = bool(deepfake_matches)
    employment_decision_impact = bool(employment and decision_impact_matches)
    image_generation_context = bool(image_matches and (marketing_matches or synthetic_media))
    consent_sensitive_context = bool(consent_matches)
    self_use_context = bool(self_use_matches)
    personal_assistant_context = bool(self_use_context and calendar_assistance_matches and not employment)

    if personal_assistant_context:
        monitoring = False
        monitoring_matches = []

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
            "image_or_likeness_usage",
            bool(image_matches),
            "Checks whether the use case involves images, photos, faces, or personal likeness.",
            image_matches,
        ),
        _decision_step(
            "marketing_or_promotional_use",
            bool(marketing_matches),
            "Checks whether the use case is for marketing, advertising, or promotional content.",
            marketing_matches,
        ),
        _decision_step(
            "consent_sensitive_context",
            consent_sensitive_context,
            "Checks whether the description explicitly raises consent or permission concerns.",
            consent_matches,
        ),
        _decision_step(
            "self_use_context",
            self_use_context,
            "Checks whether the use case is framed as personal self-use rather than monitoring other people.",
            self_use_matches,
        ),
        _decision_step(
            "personal_assistant_context",
            personal_assistant_context,
            "Checks whether the use case looks like a personal productivity or calendar assistant for the same user.",
            calendar_assistance_matches if self_use_context else [],
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

    if image_generation_context and employment:
        hints.append(
            "The use case involves employee images or likeness in a marketing or synthetic-media context. This does not automatically make it Annex III high-risk, but it strongly raises transparency and non-AI-law consent/privacy concerns."
        )
        if pre_classification == "unclear":
            pre_classification = "transparency_candidate"

    if consent_sensitive_context:
        hints.append(
            "The description explicitly raises consent concerns. The answer should distinguish EU AI Act obligations from separate employment, privacy, personality-rights, or data-protection issues."
        )

    if personal_assistant_context and not monitoring and not biometric_usage and not synthetic_media:
        pre_classification = "minimal_candidate"
        hints.append(
            "This looks like a personal productivity assistant for the same user rather than an AI system monitoring employees or third parties, so it is likely a minimal-risk use case under the EU AI Act."
        )

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

    if steps.get("personal_assistant_context"):
        return []

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

    if steps.get("image_or_likeness_usage") and not steps.get("marketing_or_promotional_use"):
        questions.append("Are the generated or manipulated images used for marketing, internal communications, identification, or another purpose?")

    if steps.get("image_or_likeness_usage") and not steps.get("consent_sensitive_context"):
        questions.append("Do the affected individuals explicitly consent to the use of their image or likeness for this purpose?")

    if not steps.get("biometric_identification") and not steps.get("emotion_recognition"):
        questions.append(
            "Does the system use biometric identification, verification, or emotion recognition, for example face recognition, voiceprint matching, or affect detection?"
        )

    return questions[:3]
