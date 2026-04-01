import sys
import os
import base64
import html
import streamlit as st
import json
import re
from datetime import datetime
import plotly.graph_objects as go

from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag_pipeline import retrieve
from app.decision_engine import analyze_question, generate_followups
from app.llm import generate_answer
from app.confidence import calculate_confidence
from app.assessment_store import DEFAULT_STATUSES, delete_assessment, load_assessments, upsert_assessment, update_assessment_status


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
    background: linear-gradient(180deg, rgba(255,255,255,0.68), rgba(255,255,255,0.38));
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 24px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
    overflow: hidden;
}}

.followup-shell details summary {{
    background: rgba(166, 228, 255, 0.18);
    font-weight: 800;
    letter-spacing: 0.01em;
    color: #0f172a;
}}

.followup-shell details summary p {{
    font-weight: 800 !important;
}}

.followup-shell [data-testid="stExpanderDetails"] {{
    background: linear-gradient(180deg, rgba(166, 228, 255, 0.18), rgba(255,255,255,0.18));
    padding-top: 0.5rem;
}}

.sources-shell {{
    padding: 0 0 2px 0;
}}

.sources-shell .source-item {{
    background: rgba(255,255,255,0.34);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 18px;
    overflow: hidden;
    margin-bottom: 12px;
}}

.sources-shell .source-item [data-testid="stExpander"] {{
    border: none;
    background: transparent;
}}

.sources-shell .source-item details {{
    background: transparent;
    border: none;
}}

.sources-shell .source-item summary {{
    font-weight: 800;
    color: #0f172a;
}}

.sources-shell .source-item [data-testid="stExpanderDetails"] {{
    background: rgba(255,255,255,0.12);
}}

.sources-shell .source-body {{
    padding: 2px 4px 2px 4px;
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

.governance-card {{
    background: linear-gradient(180deg, rgba(255,255,255,0.72), rgba(255,255,255,0.42));
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 24px;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
    margin-bottom: 16px;
}}

.governance-card h3 {{
    margin: 0 0 10px 0 !important;
    font-size: 1.1rem;
}}

.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}}

.kpi-pill {{
    background: rgba(255,255,255,0.46);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 18px;
    padding: 14px 12px;
}}

.kpi-label {{
    color: #5b7282;
    font-size: 0.82rem;
    margin-bottom: 6px;
}}

.kpi-value {{
    font-size: 1.35rem;
    font-weight: 800;
    color: #0f172a;
}}

.case-card {{
    background: rgba(255,255,255,0.36);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 20px;
    padding: 14px 14px 10px 14px;
    margin-bottom: 12px;
}}

.case-title {{
    font-weight: 800;
    color: #0f172a;
    line-height: 1.4;
    margin-bottom: 6px;
}}

.case-meta {{
    color: #587082;
    font-size: 0.88rem;
    margin-bottom: 10px;
}}

.status-badge {{
    display: inline-flex;
    align-items: center;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 10px;
}}

.status-draft {{
    background: rgba(59, 130, 246, 0.14);
    color: #1d4ed8;
}}

.status-needs-more-info {{
    background: rgba(245, 158, 11, 0.16);
    color: #b45309;
}}

.status-in-review {{
    background: rgba(168, 85, 247, 0.14);
    color: #7e22ce;
}}

.status-approved {{
    background: rgba(16, 185, 129, 0.14);
    color: #047857;
}}

.workspace-nav {{
    display: flex;
    gap: 10px;
    margin: 6px 0 18px 0;
}}

.workspace-pill {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 10px 16px;
    border-radius: 999px;
    background: rgba(255,255,255,0.52);
    border: 1px solid rgba(148, 163, 184, 0.22);
    color: #0f172a;
    font-weight: 700;
    box-shadow: 0 14px 35px rgba(15, 23, 42, 0.08);
}}

.page-shell {{
    animation-duration: 0.55s;
    animation-fill-mode: both;
    animation-timing-function: ease;
}}

.view-enter-chat {{
    animation-name: chatEnter;
}}

.view-enter-dashboard {{
    animation-name: dashboardEnter;
}}

@keyframes chatEnter {{
    from {{
        opacity: 0;
        transform: translateX(-24px) scale(0.99);
    }}
    to {{
        opacity: 1;
        transform: translateX(0) scale(1);
    }}
}}

@keyframes dashboardEnter {{
    from {{
        opacity: 0;
        transform: translateX(24px) scale(0.99);
    }}
    to {{
        opacity: 1;
        transform: translateX(0) scale(1);
    }}
}}

.dashboard-table {{
    background: linear-gradient(180deg, rgba(255,255,255,0.7), rgba(255,255,255,0.42));
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 22px;
    padding: 8px 12px 8px 12px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}}

.dashboard-row {{
    display: grid;
    grid-template-columns: 0.9fr 3.1fr 1.05fr 1fr 1.35fr 0.95fr;
    gap: 14px;
    align-items: center;
    padding: 12px 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}}

.dashboard-row:last-child {{
    border-bottom: none;
}}

.dashboard-head {{
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #587082;
    font-weight: 800;
    padding-top: 4px;
    padding-bottom: 8px;
}}

.dashboard-cell-title {{
    color: #0f172a;
    font-weight: 700;
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
}}

.dashboard-cell-subtle {{
    color: #587082;
    font-size: 0.9rem;
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.dashboard-actions {{
    padding: 0 10px 12px 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}}

.dashboard-actions:last-child {{
    border-bottom: none;
}}

.issue-key {{
    color: #2563eb;
    font-weight: 800;
    font-size: 0.92rem;
    letter-spacing: 0.01em;
    white-space: nowrap;
}}

.dashboard-toolbar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 8px 0 12px 0;
}}

.dashboard-toolbar-copy {{
    color: #587082;
    font-size: 0.95rem;
}}

.dashboard-title-cell {{
    min-width: 0;
}}

.dashboard-header-buttons {{
    margin-bottom: 8px;
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
    normalized = str(c or "").strip().lower().replace("_", "-")
    return {
        "high-risk": "⚠️ High Risk",
        "transparency": "Transparency Obligations",
        "minimal": "✅ Minimal",
        "unclear": "Needs More Input",
    }.get(normalized, c)


def normalize_classification(value):
    normalized = str(value or "").strip().lower().replace("_", "-")
    mapping = {
        "highrisk": "high-risk",
        "high-risk": "high-risk",
        "transparency": "transparency",
        "transparency-obligation": "transparency",
        "minimal": "minimal",
        "low-risk": "minimal",
        "unclear": "unclear",
        "needs-more-info": "unclear",
    }
    return mapping.get(normalized, normalized or "unclear")


def _step_map(decision_tree):
    return {step.get("step"): bool(step.get("value")) for step in (decision_tree or [])}


def resolve_final_classification(raw_classification, decision_data):
    normalized = normalize_classification(raw_classification)
    step_values = _step_map((decision_data or {}).get("decision_tree", []))
    pre_classification = str((decision_data or {}).get("pre_classification", "")).strip().lower()

    if step_values.get("personal_assistant_context") and not any([
        step_values.get("surveillance_detected"),
        step_values.get("employment_context"),
        step_values.get("employment_decision_impact"),
        step_values.get("biometric_identification"),
        step_values.get("emotion_recognition"),
        step_values.get("biometric_usage"),
    ]):
        return "minimal"

    if (
        pre_classification == "transparency_candidate"
        and not step_values.get("employment_decision_impact")
        and not step_values.get("biometric_identification")
        and not step_values.get("emotion_recognition")
    ):
        return "transparency"

    if pre_classification in {"potential_high_risk", "high_risk_candidate", "sensitive_prohibited_or_high_risk_candidate"}:
        return "high-risk"

    if normalized in {"high-risk", "transparency", "minimal", "unclear"}:
        return normalized

    return "unclear"


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

    classification = normalize_classification(classification)

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


def build_rule_analysis_query(base_query, follow_up_questions, answers):
    facts = [str(base_query or "").strip()]

    for idx, _question in enumerate(follow_up_questions):
        answer = str(answers.get(idx, "")).strip()
        if answer:
            facts.append(answer)

    return "\n".join(part for part in facts if part).strip()


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


def status_class(status):
    return (
        status.lower()
        .replace(" ", "-")
    )


def format_saved_timestamp(timestamp):
    if not timestamp:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%d %b %y")
    except ValueError:
        return timestamp


def sort_assessments(items, sort_by, sort_dir):
    reverse = sort_dir == "desc"

    def sort_key(item):
        if sort_by == "issue_key":
            return str(item.get("issue_key", "")).lower()
        if sort_by == "title":
            return str(item.get("title", "")).lower()
        if sort_by == "status":
            return DEFAULT_STATUSES.index(item.get("status")) if item.get("status") in DEFAULT_STATUSES else 99
        if sort_by == "confidence":
            return float(item.get("confidence", 0.0) or 0.0)
        if sort_by == "classification":
            return str(item.get("classification", "")).lower()
        return str(item.get("updated_at", ""))

    return sorted(items, key=sort_key, reverse=reverse)


def toggle_dashboard_sort(sort_by):
    current_by = st.session_state.dashboard_sort_by
    current_dir = st.session_state.dashboard_sort_dir

    if current_by == sort_by:
        st.session_state.dashboard_sort_dir = "asc" if current_dir == "desc" else "desc"
    else:
        st.session_state.dashboard_sort_by = sort_by
        st.session_state.dashboard_sort_dir = "asc" if sort_by == "title" else "desc"


def dashboard_sort_label(label, sort_key):
    active = st.session_state.dashboard_sort_by == sort_key
    if not active:
        return label
    arrow = "↓" if st.session_state.dashboard_sort_dir == "desc" else "↑"
    return f"{label} {arrow}"


def render_pie_chart(title, labels, values, colors):
    filtered = [(label, value, colors[idx]) for idx, (label, value) in enumerate(zip(labels, values)) if value > 0]
    if not filtered:
        st.markdown(
            f"""
            <div class="insight-card">
                <h3>{title}</h3>
                <div class="insight-subtle">No data yet.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    labels = [item[0] for item in filtered]
    values = [item[1] for item in filtered]
    colors = [item[2] for item in filtered]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.58,
                marker={"colors": colors},
                textinfo="label+percent",
                sort=False,
            )
        ]
    )
    fig.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 10, "r": 10, "t": 48, "b": 10},
        font={"color": "#0f172a"},
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def build_assessment_record(title_override=None, status="Draft"):
    debug = st.session_state.last_debug or {}
    if not debug:
        return None

    user_messages = [msg for msg in st.session_state.messages if msg.get("role") == "user" and not msg.get("typing")]
    last_user_message = user_messages[-1]["content"] if user_messages else "Untitled assessment"
    base_title = (st.session_state.base_query or last_user_message or "Untitled assessment").strip()
    title = title_override.strip() if title_override and title_override.strip() else base_title[:120]

    existing_status = status
    if st.session_state.active_assessment_id:
        current_cases = load_assessments()
        existing = next((item for item in current_cases if item.get("id") == st.session_state.active_assessment_id), None)
        if existing and existing.get("status"):
            existing_status = existing["status"]

    return {
        "id": st.session_state.active_assessment_id,
        "title": title,
        "status": existing_status,
        "classification": normalize_classification(debug.get("classification", "")),
        "confidence": debug.get("confidence", 0.0),
        "messages": st.session_state.messages,
        "follow_up": st.session_state.follow_up,
        "resolved_followups": st.session_state.resolved_followups,
        "debug": debug,
        "summary": next(
            (msg.get("content", "") for msg in reversed(st.session_state.messages) if msg.get("role") == "assistant" and not msg.get("typing")),
            ""
        ),
    }


def load_assessment_into_workspace(assessment):
    st.session_state.messages = assessment.get("messages", [])
    st.session_state.last_debug = assessment.get("debug")
    st.session_state.follow_up = assessment.get("follow_up", [])
    st.session_state.resolved_followups = assessment.get("resolved_followups", [])
    st.session_state.answers = {}
    st.session_state.pending_query = None
    st.session_state.pending_rule_query = None
    st.session_state.display_query = None
    st.session_state.processing = False
    st.session_state.base_query = next(
        (msg.get("content", "") for msg in assessment.get("messages", []) if msg.get("role") == "user"),
        ""
    )
    st.session_state.assessment_title_value = assessment.get("title", "")
    st.session_state.pending_assessment_title = assessment.get("title", "")


def reset_workspace():
    st.session_state.messages = []
    st.session_state.last_debug = None
    st.session_state.follow_up = []
    st.session_state.resolved_followups = []
    st.session_state.answers = {}
    st.session_state.pending_query = None
    st.session_state.pending_rule_query = None
    st.session_state.display_query = None
    st.session_state.base_query = None
    st.session_state.processing = False
    st.session_state.active_assessment_id = None
    st.session_state.assessment_title_value = ""
    st.session_state.pending_assessment_title = ""


def render_dashboard_view(assessments):
    st.markdown('<div class="page-shell view-enter-dashboard">', unsafe_allow_html=True)
    st.markdown('<div class="header-box"><h2>Review Board</h2></div>', unsafe_allow_html=True)

    nav_col1, nav_col2 = st.columns([1, 3.5])
    with nav_col1:
        if st.button("Back to Workspace", width="stretch"):
            st.session_state.view_mode = "chat"
            st.rerun()
    with nav_col2:
        st.markdown(
            '<div class="dashboard-toolbar-copy">Review and manage persisted assessment cases with sortable issue keys and workflow status.</div>',
            unsafe_allow_html=True
        )

    total_assessments = len(assessments)
    in_review_count = sum(1 for item in assessments if item.get("status") == "In Review")
    approved_count = sum(1 for item in assessments if item.get("status") == "Approved")
    avg_confidence = (
        sum(float(item.get("confidence", 0.0) or 0.0) for item in assessments) / total_assessments
        if total_assessments else 0.0
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    for col, label, value in [
        (kpi1, "Total Cases", total_assessments),
        (kpi2, "In Review", in_review_count),
        (kpi3, "Approved", approved_count),
        (kpi4, "Average Confidence", f"{round(avg_confidence * 100)}%"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="governance-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    chart_col1, chart_col2, chart_col3 = st.columns([1.1, 1.1, 1])
    with chart_col1:
        render_pie_chart(
            "Cases by Status",
            DEFAULT_STATUSES,
            [sum(1 for item in assessments if item.get("status") == status) for status in DEFAULT_STATUSES],
            ["#60a5fa", "#f59e0b", "#a855f7", "#10b981"],
        )
    with chart_col2:
        render_pie_chart(
            "Cases by Classification",
            ["High Risk", "Transparency", "Minimal", "Needs More Input"],
            [
                sum(1 for item in assessments if normalize_classification(item.get("classification")) == "high-risk"),
                sum(1 for item in assessments if normalize_classification(item.get("classification")) == "transparency"),
                sum(1 for item in assessments if normalize_classification(item.get("classification")) == "minimal"),
                sum(1 for item in assessments if normalize_classification(item.get("classification")) == "unclear"),
            ],
            ["#ff5f8f", "#5c7cff", "#20d3c2", "#cbd5e1"],
        )
    with chart_col3:
        render_gauge(avg_confidence)

    st.markdown('<div class="dashboard-table">', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-header-buttons">', unsafe_allow_html=True)
    head_cols = st.columns([0.9, 3.1, 1.05, 1, 1.35, 0.95])
    header_defs = [
        ("Issue", "issue_key"),
        ("Title", "title"),
        ("Status", "status"),
        ("Confidence", "confidence"),
        ("Classification", "classification"),
        ("Updated", "updated_at"),
    ]
    for col, (label, sort_key) in zip(head_cols, header_defs):
        with col:
            if st.button(dashboard_sort_label(label, sort_key), key=f"sort_{sort_key}", width="stretch"):

                toggle_dashboard_sort(sort_key)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


    sorted_assessments = sort_assessments(
        assessments,
        st.session_state.dashboard_sort_by,
        st.session_state.dashboard_sort_dir,
    )

    if not sorted_assessments:
        st.markdown(
            """
            <div class="dashboard-row">
                <div class="dashboard-cell-subtle">No saved assessments yet.</div>
                <div></div><div></div><div></div><div></div><div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for assessment in sorted_assessments:
            status = assessment.get("status", "Draft")
            confidence = round(float(assessment.get("confidence", 0.0) or 0.0) * 100)
            classification = html.escape(classification_label(assessment.get("classification", "unclear")))
            title = html.escape(assessment.get("title", "Untitled assessment"))
            issue_key = html.escape(assessment.get("issue_key", ""))
            st.markdown(
                f"""
                <div class="dashboard-row">
                    <div class="issue-key">{issue_key}</div>
                    <div class="dashboard-title-cell">
                        <div class="dashboard-cell-title">{title}</div>
                    </div>
                    <div><span class="status-badge status-{status_class(status)}">{status}</span></div>
                    <div class="dashboard-cell-title">{confidence}%</div>
                    <div class="dashboard-cell-subtle">{classification}</div>
                    <div class="dashboard-cell-subtle">{format_saved_timestamp(assessment.get("updated_at"))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            action_col1, action_col2, action_col3 = st.columns([1.05, 1.05, 0.8])
            with action_col1:
                selected_status = st.selectbox(
                    f"Queue status for {assessment.get('id')}",
                    DEFAULT_STATUSES,
                    index=DEFAULT_STATUSES.index(status) if status in DEFAULT_STATUSES else 0,
                    key=f"queue_status_{assessment.get('id')}",
                    label_visibility="collapsed",
                )
                if selected_status != status:
                    update_assessment_status(assessment.get("id"), selected_status)
                    st.rerun()
            with action_col2:
                if st.button("Open", key=f"queue_open_{assessment.get('id')}", width="stretch"):

                    load_assessment_into_workspace(assessment)
                    st.session_state.active_assessment_id = assessment.get("id")
                    st.session_state.pending_assessment_title = assessment.get("title", "")
                    st.session_state.view_mode = "chat"
                    st.rerun()
            with action_col3:
                if st.button("Delete", key=f"queue_delete_{assessment.get('id')}", width="stretch"):

                    delete_assessment(assessment.get("id"))
                    if st.session_state.active_assessment_id == assessment.get("id"):
                        reset_workspace()
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ================= STATE =================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_debug" not in st.session_state:
    st.session_state.last_debug = None

if "follow_up" not in st.session_state:
    st.session_state.follow_up = []

if "resolved_followups" not in st.session_state:
    st.session_state.resolved_followups = []

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

if "display_query" not in st.session_state:
    st.session_state.display_query = None

if "pending_rule_query" not in st.session_state:
    st.session_state.pending_rule_query = None

if "base_query" not in st.session_state:
    st.session_state.base_query = None

if "processing" not in st.session_state:
    st.session_state.processing = False

if "assessment_title_value" not in st.session_state:
    st.session_state.assessment_title_value = ""

if "assessment_title_input" not in st.session_state:
    st.session_state.assessment_title_input = ""

if "active_assessment_id" not in st.session_state:
    st.session_state.active_assessment_id = None

if "pending_assessment_title" not in st.session_state:
    st.session_state.pending_assessment_title = None

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "chat"

if "dashboard_sort_by" not in st.session_state:
    st.session_state.dashboard_sort_by = "updated_at"

if "dashboard_sort_dir" not in st.session_state:
    st.session_state.dashboard_sort_dir = "desc"

if st.session_state.pending_assessment_title is not None:
    st.session_state.assessment_title_value = st.session_state.pending_assessment_title
    st.session_state.assessment_title_input = st.session_state.pending_assessment_title
    st.session_state.pending_assessment_title = None


assessments = load_assessments()

if st.session_state.view_mode == "dashboard":
    render_dashboard_view(assessments)
    st.stop()

col1, col2 = st.columns([2, 1])


# ================= CHAT =================
with col1:
    nav_col1, nav_col2 = st.columns([1.4, 4])
    with nav_col1:
        if st.button("Review Board", width="stretch"):

            st.session_state.view_mode = "dashboard"
            st.rerun()
    with nav_col2:
        st.markdown('<div class="workspace-pill">Live governance workspace</div>', unsafe_allow_html=True)

    st.markdown('<div class="page-shell view-enter-chat">', unsafe_allow_html=True)
    st.markdown('<div class="header-box"><h2>EU AI Act Governance Workspace</h2></div>', unsafe_allow_html=True)

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
        st.session_state.pending_rule_query = user_input
        st.session_state.display_query = user_input
        st.session_state.base_query = user_input
        st.session_state.active_assessment_id = None
        st.session_state.follow_up = []
        st.session_state.resolved_followups = []
        st.session_state.answers = {}
        if not st.session_state.assessment_title_value.strip():
            st.session_state.assessment_title_value = user_input[:80]
            st.session_state.pending_assessment_title = user_input[:80]
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": "", "typing": True})
        st.session_state.processing = True
        st.rerun()

    if st.session_state.pending_query and st.session_state.processing:
        query = st.session_state.pending_query
        rule_query = st.session_state.pending_rule_query or query
        st.session_state.pending_query = None
        st.session_state.pending_rule_query = None
        st.session_state.display_query = None

        results = retrieve(query)
        decision_data = analyze_question(rule_query)

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

        raw_classification = normalize_classification(answer.get("classification", ""))
        final_classification = resolve_final_classification(
            answer.get("classification", ""),
            decision_data
        )
        answer["classification"] = final_classification
        if raw_classification and raw_classification != final_classification:
            answer["answer"] = (
                f"{answer.get('answer', '').rstrip()}\n\n"
                f"Governance note: Based on the structured decision rules in this workspace, "
                f"this case is currently treated as {classification_label(final_classification)}."
            )

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

        answer_followups = answer.get("follow_up", []) if isinstance(answer, dict) else []
        next_followups = []
        for question in list(answer_followups) + list(generate_followups(decision_data["decision_tree"])):
            clean_question = str(question).strip()
            if not clean_question:
                continue
            if clean_question in st.session_state.resolved_followups:
                continue
            if clean_question in next_followups:
                continue
            next_followups.append(clean_question)
        st.session_state.follow_up = [
            question for question in next_followups
            if question not in st.session_state.resolved_followups
        ]
        st.session_state.answers = {}
        st.session_state.processing = False

        st.rerun()

    # ================= FOLLOW UPS =================
    if st.session_state.follow_up:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
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
                st.session_state.resolved_followups.extend(
                    question for question in st.session_state.follow_up
                    if question not in st.session_state.resolved_followups
                )
                combined, transcript = build_followup_context(
                    st.session_state.base_query or "",
                    st.session_state.follow_up,
                    st.session_state.answers
                )
                rule_query = build_rule_analysis_query(
                    st.session_state.base_query or "",
                    st.session_state.follow_up,
                    st.session_state.answers
                )
                st.session_state.pending_query = combined
                st.session_state.pending_rule_query = rule_query
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

    if st.session_state.last_debug:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="governance-card">', unsafe_allow_html=True)
        st.markdown("### Save Assessment")
        st.caption("Capture this assessment as a reusable governance case with review status and evidence snapshot.")
        title_value = st.text_input(
            "Assessment title",
            placeholder="Name this assessment...",
            key="assessment_title_input"
        )
        st.session_state.assessment_title_value = title_value
        save_col, new_case_col, info_col = st.columns([1, 1, 1])
        with save_col:
            if st.button("Save Current Assessment", width="stretch"):

                record = build_assessment_record(st.session_state.assessment_title_value, status="Draft")
                if record:
                    saved = upsert_assessment(record)
                    st.session_state.active_assessment_id = saved.get("id")
                    st.session_state.assessment_title_value = saved.get("title", "")
                    st.session_state.pending_assessment_title = saved.get("title", "")
                    st.success("Assessment saved to governance queue.")
                    st.rerun()
        with new_case_col:
            if st.button("Create New Case", width="stretch"):

                reset_workspace()
                st.session_state.pending_assessment_title = ""
                st.rerun()
        with info_col:
            active_label = st.session_state.active_assessment_id or "Not saved yet"
            st.caption(f"Active case ID: {active_label}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ================= INSIGHTS =================
with col2:
    st.markdown('<div class="header-box"><h2>Insights</h2></div>', unsafe_allow_html=True)

    debug = st.session_state.last_debug
    total_assessments = len(assessments)
    in_review_count = sum(1 for item in assessments if item.get("status") == "In Review")
    approved_count = sum(1 for item in assessments if item.get("status") == "Approved")
    high_risk_count = sum(1 for item in assessments if "high" in str(item.get("classification", "")).lower())

    st.markdown(
        f"""
        <div class="governance-card">
            <h3>Governance Snapshot</h3>
            <div class="kpi-grid">
                <div class="kpi-pill">
                    <div class="kpi-label">Total Cases</div>
                    <div class="kpi-value">{total_assessments}</div>
                </div>
                <div class="kpi-pill">
                    <div class="kpi-label">In Review</div>
                    <div class="kpi-value">{in_review_count}</div>
                </div>
                <div class="kpi-pill">
                    <div class="kpi-label">Approved</div>
                    <div class="kpi-value">{approved_count}</div>
                </div>
                <div class="kpi-pill">
                    <div class="kpi-label">High Risk</div>
                    <div class="kpi-value">{high_risk_count}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


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
                        decision clarity {breakdown.get('decision_clarity', 0):.2f}, citations {breakdown.get('citation_strength', 0):.2f},
                        locator quality {breakdown.get('locator_quality', 0):.2f}, consistency {breakdown.get('consistency', 0):.2f}
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









