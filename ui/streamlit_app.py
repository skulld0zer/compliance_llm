import sys
import os
import base64
import streamlit as st
import json
import re

from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag_pipeline import retrieve
from app.decision_engine import analyze_question, generate_followups
from app.llm import generate_answer
from app.confidence import calculate_confidence


# ================= STYLE =================
st.set_page_config(layout="wide")

def get_background_css():
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    candidates = [
        ("background.jpg", "image/jpeg"),
        ("background.jpeg", "image/jpeg"),
        ("background.png", "image/png"),
        ("background.webp", "image/webp"),
    ]

    background = "linear-gradient(135deg, #a7d8ef 0%, #d9eef8 50%, #f5fbff 100%)"

    for filename, mime_type in candidates:
        asset_path = os.path.join(assets_dir, filename)
        if os.path.exists(asset_path):
            with open(asset_path, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode("utf-8")
            background = f'url("data:{mime_type};base64,{encoded}")'
            break

    return f"""
<style>
.stApp {{ background: none; }}

[data-testid="stAppViewContainer"] {{
    background-image: {background};
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: fixed;
    inset: 0;
    backdrop-filter: blur(10px);
    background: rgba(255,255,255,0.25);
    pointer-events: none;
    z-index: 0;
}}

[data-testid="stAppViewContainer"] > .main {{
    position: relative;
    z-index: 1;
}}

.header-box {{
    backdrop-filter: blur(20px);
    background: rgba(255,255,255,0.6);
    border-radius: 20px;
    padding: 16px 20px;
    margin-bottom: 20px;
}}

/* spacing fixes */
.user-bubble {{
    background: #007AFF;
    color: white;
    padding: 12px 18px;
    border-radius: 20px;
    max-width: 70%;
    margin-left: auto;
    margin-bottom: 18px;
    white-space: pre-line;
}}

.assistant-bubble {{
    background: rgba(255,255,255,0.9);
    padding: 12px 18px;
    border-radius: 20px;
    max-width: 70%;
    margin-bottom: 18px;
    white-space: pre-line;
}}

.typing-bubble {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 28px;
}}

.typing-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #64748b;
    display: inline-block;
    animation: typingPulse 1.2s infinite ease-in-out;
}}

.typing-dot:nth-child(2) {{
    animation-delay: 0.2s;
}}

.typing-dot:nth-child(3) {{
    animation-delay: 0.4s;
}}

@keyframes typingPulse {{
    0%, 80%, 100% {{
        opacity: 0.3;
        transform: translateY(0);
    }}
    40% {{
        opacity: 1;
        transform: translateY(-3px);
    }}
}}

textarea {{
    border-radius: 20px !important;
    background: rgba(255,255,255,0.9) !important;
}}

h3 {{
    margin-bottom: 6px !important;
}}

.flow-card {{
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(15,23,42,0.15);
    border-radius: 12px;
    padding: 10px 12px;
    margin-bottom: 8px;
}}

.flow-step-title {{
    font-weight: 600;
    margin-bottom: 4px;
}}

.flow-meta {{
    font-size: 0.9rem;
    color: #334155;
}}

.followup-question {{
    font-size: 1rem;
    font-weight: 700;
    line-height: 1.5;
    color: #0f172a;
    margin: 0.35rem 0 0.45rem 0;
}}

.followup-shell details {{
    background: rgba(166, 228, 255, 0.18);
    border: 1px solid rgba(56, 189, 248, 0.28);
    border-radius: 18px;
    box-shadow: 0 18px 45px rgba(56, 189, 248, 0.08);
    overflow: hidden;
}}

.followup-shell details summary {{
    background: rgba(117, 214, 255, 0.14);
    font-weight: 700;
    letter-spacing: 0.01em;
}}

.insight-card {{
    background: linear-gradient(180deg, rgba(255,255,255,0.68), rgba(255,255,255,0.38));
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 24px;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
    margin-bottom: 16px;
    opacity: 0;
    transform: translateY(-14px);
    animation: insightEnter 0.7s ease forwards;
}}

.insight-card h3 {{
    margin: 0 0 10px 0 !important;
    font-size: 1.15rem;
}}

.insight-metric {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}}

.insight-metric:last-child {{
    border-bottom: none;
    padding-bottom: 0;
}}

.insight-label {{
    font-weight: 600;
    color: #0f172a;
}}

.insight-value {{
    color: #0f172a;
}}

.insight-subtle {{
    color: #476072;
    font-size: 0.92rem;
    line-height: 1.5;
}}

.modern-gauge-card {{
    text-align: center;
}}

.modern-gauge-title {{
    margin-bottom: 12px;
    color: #476072;
    font-size: 0.95rem;
    letter-spacing: 0.01em;
}}

.modern-gauge-wrap {{
    position: relative;
    width: 100%;
    max-width: 290px;
    margin: 0 auto;
}}

.modern-gauge-svg {{
    width: 100%;
    height: auto;
    overflow: visible;
}}

.modern-gauge-center {{
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    transform: translateY(8px);
}}

.modern-gauge-percent {{
    font-size: 2rem;
    font-weight: 700;
    color: #0f172a;
}}

.modern-gauge-caption {{
    font-size: 0.86rem;
    color: #5b7282;
}}

@keyframes insightEnter {{
    from {{
        opacity: 0;
        transform: translateY(-14px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0);
    }}
}}
</style>
"""


st.markdown(get_background_css(), unsafe_allow_html=True)


# ================= HELPERS =================
def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else None


def classification_label(c):
    return {
        "high-risk": "⚠️ High Risk",
        "minimal": "✅ Minimal",
    }.get(c, c)


def render_gauge(confidence):
    percent = max(0, min(100, round(confidence * 100)))
    radius = 92
    circumference = 3.14159 * radius
    progress = circumference * (1 - percent / 100)

    gauge_html = f"""
    <div class="insight-card modern-gauge-card" style="animation-delay:0.28s;">
        <div class="modern-gauge-title">Confidence Score</div>
        <div class="modern-gauge-wrap">
            <svg class="modern-gauge-svg" viewBox="0 0 240 150" role="img" aria-label="Confidence score {percent}%">
                <defs>
                    <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stop-color="#ff5f8f"></stop>
                        <stop offset="48%" stop-color="#5c7cff"></stop>
                        <stop offset="100%" stop-color="#20d3c2"></stop>
                    </linearGradient>
                </defs>
                <path d="M 28 122 A 92 92 0 0 1 212 122" fill="none" stroke="rgba(255,255,255,0.45)" stroke-width="18" stroke-linecap="round"></path>
                <path d="M 28 122 A 92 92 0 0 1 212 122" fill="none" stroke="url(#gaugeGradient)" stroke-width="18" stroke-linecap="round" stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{circumference:.2f}">
                    <animate attributeName="stroke-dashoffset" begin="0.55s" dur="1.4s" fill="freeze" from="{circumference:.2f}" to="{progress:.2f}"></animate>
                </path>
                <text x="18" y="128" font-size="11" fill="#5b7282">0</text>
                <text x="114" y="26" font-size="11" fill="#5b7282">50</text>
                <text x="204" y="128" font-size="11" fill="#5b7282">100</text>
            </svg>
            <div class="modern-gauge-center">
                <div class="modern-gauge-percent">{percent}%</div>
                <div class="modern-gauge-caption">AI answer confidence</div>
            </div>
        </div>
    </div>
    """
    st.markdown(gauge_html, unsafe_allow_html=True)


def _pretty_step_name(step_name):
    return step_name.replace("_", " ").strip().title()


def decision_step_label(step_name):
    labels = {
        "surveillance_detected": "Monitoring/Surveillance detected",
        "employment_context": "Employment context detected",
        "employment_decision_impact": "Employment decision impact",
        "biometric_identification": "Biometric identification",
        "emotion_recognition": "Emotion recognition",
        "synthetic_media_generation": "Synthetic media generation",
        "voice_audio_processing": "Voice/audio processing",
        "biometric_usage": "Biometric data in use",
    }
    return labels.get(step_name, _pretty_step_name(step_name))


def render_decision_flow_diagram(decision_tree, classification):
    if not decision_tree:
        st.info("No decision flow data available.")
        return

    for i, step in enumerate(decision_tree, start=1):
        status = "PASS" if step["value"] else "FAIL"
        color = "#16a34a" if step["value"] else "#dc2626"
        title = decision_step_label(step["step"])
        detail = step.get("detail") or "Checks a classification-relevant signal from the decision engine."
        matches = step.get("matches") or []
        if matches:
            detail += f" Triggered by: {', '.join(matches[:4])}."
        st.markdown(
            f"""
            <div class="flow-card">
                <div class="flow-step-title">{i}. {title} - <span style="color:{color};">{status}</span></div>
                <div class="flow-meta">{detail}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if i < len(decision_tree):
            st.markdown("<div style='text-align:center; color:#475569; margin-bottom:8px;'>↓</div>", unsafe_allow_html=True)

    final_color = "#16a34a" if classification == "minimal" else "#dc2626"
    st.markdown(
        f"""
        <div class="flow-card" style="border-width:2px;">
            <div class="flow-step-title">Final Classification - <span style="color:{final_color};">{classification_label(classification)}</span></div>
            <div class="flow-meta">Outcome based on the combined evaluation of the rules above.</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def format_source_meta(source):
    reference = str(source.get("reference", "Unknown")).strip() or "Unknown"
    page = str(source.get("page", "n/a")).replace("\n", " ").strip() or "n/a"
    locator = str(source.get("locator", "")).replace("\n", " ").strip()
    paragraph = source.get("paragraph")

    if paragraph is None or paragraph == "":
        paragraph = "Unavailable in current index"
    else:
        paragraph = str(paragraph).replace("\n", " ").strip()

    if not locator:
        locator = f"{reference}, paragraph {paragraph}" if paragraph != "Unavailable in current index" else reference

    return reference, page, paragraph, locator


def source_excerpt(text, max_len=320):
    clean = " ".join(str(text).split())
    if len(clean) <= max_len:
        return clean
    return clean[:max_len].rstrip() + "..."


def source_header(reference, idx):
    short_ref = " ".join(reference.split())
    if len(short_ref) > 48:
        short_ref = short_ref[:48].rstrip() + "..."
    return f"Source {idx}: {short_ref}"


def build_followup_context(base_query, follow_up_questions, answers):
    filled_pairs = []

    for idx, question in enumerate(follow_up_questions):
        answer = str(answers.get(idx, "")).strip()
        if answer:
            filled_pairs.append((question, answer))

    if not filled_pairs:
        return base_query, ""

    transcript = "\n".join(
        f"{question}\n{answer}" for question, answer in filled_pairs
    )

    combined_query = (
        f"Original question:\n{base_query}\n\n"
        f"Additional clarifications:\n{transcript}"
    )

    return combined_query, transcript


def typing_indicator_html():
    return """
    <div class="assistant-bubble">
        <div class="typing-bubble" aria-label="Assistant is typing">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    </div>
    """


# ================= STATE =================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_debug" not in st.session_state:
    st.session_state.last_debug = None

if "follow_up" not in st.session_state:
    st.session_state.follow_up = []

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

if "display_query" not in st.session_state:
    st.session_state.display_query = None

if "base_query" not in st.session_state:
    st.session_state.base_query = None

if "processing" not in st.session_state:
    st.session_state.processing = False


col1, col2 = st.columns([2, 1])


# ================= CHAT =================
with col1:
    st.markdown('<div class="header-box"><h2>EU AI Act Chat</h2></div>', unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg.get("typing"):
            st.markdown(typing_indicator_html(), unsafe_allow_html=True)
        else:
            cls = "user-bubble" if msg["role"] == "user" else "assistant-bubble"
            st.markdown(f'<div class="{cls}">{msg["content"]}</div>', unsafe_allow_html=True)

    # 🔥 spacing before input
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    user_input = st.chat_input("Ask something...")

    if user_input and not st.session_state.processing:
        st.session_state.pending_query = user_input
        st.session_state.display_query = user_input
        st.session_state.base_query = user_input
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": "", "typing": True})
        st.session_state.processing = True
        st.rerun()

    if st.session_state.pending_query and st.session_state.processing:
        query = st.session_state.pending_query
        st.session_state.pending_query = None
        st.session_state.display_query = None

        results = retrieve(query)
        decision_data = analyze_question(query)

        raw = generate_answer(
            query,
            results,
            decision_data["hints"],
            decision_data["pre_classification"]
        )

        try:
            answer = json.loads(extract_json(raw))
        except:
            answer = {"answer": raw}

        confidence, confidence_breakdown = calculate_confidence(
            results,
            decision_data,
            answer,
            return_breakdown=True
        )

        st.session_state.last_debug = {
            "confidence": confidence,
            "confidence_breakdown": confidence_breakdown,
            "classification": answer.get("classification", ""),
            "decision_tree": decision_data["decision_tree"],
            "sources": results
        }

        if st.session_state.messages and st.session_state.messages[-1].get("typing"):
            st.session_state.messages[-1] = {
                "role": "assistant",
                "content": answer["answer"]
            }
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer["answer"]
            })

        st.session_state.follow_up = generate_followups(decision_data["decision_tree"])
        st.session_state.answers = {}
        st.session_state.processing = False

        st.rerun()

    # ================= FOLLOW UPS =================
    if st.session_state.follow_up:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="followup-shell">', unsafe_allow_html=True)
        with st.expander("Follow-up Questions for Refinement", expanded=False):
            for i, q in enumerate(st.session_state.follow_up):
                st.markdown(f'<div class="followup-question">{q}</div>', unsafe_allow_html=True)
                st.session_state.answers[i] = st.text_input(
                    q,
                    key=f"q_{i}",
                    label_visibility="collapsed",
                    placeholder="Type your answer..."
                )

            if st.button("Refine Answer"):
                combined, transcript = build_followup_context(
                    st.session_state.base_query or "",
                    st.session_state.follow_up,
                    st.session_state.answers
                )
                st.session_state.pending_query = combined
                st.session_state.display_query = transcript or combined
                st.session_state.follow_up = []
                st.session_state.answers = {}
                st.session_state.messages.append({
                    "role": "user",
                    "content": transcript or combined
                })
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "",
                    "typing": True
                })
                st.session_state.processing = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ================= INSIGHTS =================
with col2:
    st.markdown('<div class="header-box"><h2>Insights</h2></div>', unsafe_allow_html=True)

    debug = st.session_state.last_debug

    if debug:
        st.markdown(
            f"""
            <div class="insight-card" style="animation-delay:0.04s;">
                <h3>Analytics</h3>
                <div class="insight-metric">
                    <span class="insight-label">Decision Depth</span>
                    <span class="insight-value">{len(debug['decision_tree'])}</span>
                </div>
                <div class="insight-metric">
                    <span class="insight-label">Sources Used</span>
                    <span class="insight-value">{len(debug['sources'])}</span>
                </div>
                <div class="insight-metric">
                    <span class="insight-label">Evidence Strength</span>
                    <span class="insight-value">{debug['confidence']:.2f}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        breakdown = debug.get("confidence_breakdown", {})
        if breakdown:
            st.markdown(
                f"""
                <div class="insight-card" style="animation-delay:0.16s;">
                    <h3>Confidence Factors</h3>
                    <div class="insight-subtle">
                        Retrieval {breakdown.get('retrieval_strength', 0):.2f}, coverage {breakdown.get('coverage', 0):.2f},
                        decision clarity {breakdown.get('decision_clarity', 0):.2f}, citations {breakdown.get('citation_strength', 0):.2f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        render_gauge(debug["confidence"])

        st.markdown(
            f"""
            <div class="insight-card" style="animation-delay:0.4s;">
                <h3>Classification</h3>
                <div class="insight-subtle" style="font-size:1.05rem; font-weight:700; color:#0f172a;">
                    {classification_label(debug["classification"])}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="insight-card" style="animation-delay:0.52s; margin-bottom:12px;">
                <h3>Decision Flow</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.expander("Show Decision Flow Diagram", expanded=False):
            render_decision_flow_diagram(debug["decision_tree"], debug["classification"])

        for step in debug["decision_tree"]:
            icon = "PASS" if step["value"] else "FAIL"
            st.write(f"{icon}: {decision_step_label(step['step'])}")

        st.markdown(
            """
            <div class="insight-card" style="animation-delay:0.64s; margin-bottom:12px;">
                <h3>Sources</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        for idx, s in enumerate(debug["sources"], start=1):
            reference, page, paragraph, locator = format_source_meta(s)
            with st.expander(source_header(reference, idx)):
                st.markdown(f"**Reference:** {reference}")
                st.markdown(f"**Locator:** {locator}")
                st.markdown(f"**Section/Page:** {page}")
                st.markdown(f"**Paragraph:** {paragraph}")
                if reference == "General Provision" or page == "General":
                    st.warning("This source comes from an older index without precise legal locators. Re-run `python scripts/ingest.py` to rebuild citations with article/paragraph metadata.")
                st.markdown("**Excerpt:**")
                st.info(source_excerpt(s.get("text", "")))
                with st.expander("Show full excerpt", expanded=False):
                    st.write(s.get("text", ""))





