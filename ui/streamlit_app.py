import sys
import os
import streamlit as st
import json
import re
import plotly.graph_objects as go

from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag_pipeline import retrieve
from app.decision_engine import analyze_question, generate_followups
from app.llm import generate_answer
from app.confidence import calculate_confidence


# ================= STYLE =================
st.set_page_config(layout="wide")

st.markdown("""
<style>
.stApp { background: none; }

body::before {
    content: "";
    position: fixed;
    inset: 0;
    background: url("https://i.ibb.co/yzj7dwz/vivid-blurred-colorful-wallpaper-background.jpg");
    background-size: cover;
    opacity: 0.5;
    z-index: -10;
}

body::after {
    content: "";
    position: fixed;
    inset: 0;
    backdrop-filter: blur(10px);
    background: rgba(255,255,255,0.25);
    z-index: -9;
}

.header-box {
    backdrop-filter: blur(20px);
    background: rgba(255,255,255,0.6);
    border-radius: 20px;
    padding: 16px 20px;
    margin-bottom: 20px;
}

/* 🔥 SPACING FIXES */
.user-bubble {
    background: #007AFF;
    color: white;
    padding: 12px 18px;
    border-radius: 20px;
    max-width: 70%;
    margin-left: auto;
    margin-bottom: 18px;
}

.assistant-bubble {
    background: rgba(255,255,255,0.9);
    padding: 12px 18px;
    border-radius: 20px;
    max-width: 70%;
    margin-bottom: 18px;
}

textarea {
    border-radius: 20px !important;
    background: rgba(255,255,255,0.9) !important;
}

/* headings tighter */
h3 {
    margin-bottom: 6px !important;
}

.flow-card {
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(15,23,42,0.15);
    border-radius: 12px;
    padding: 10px 12px;
    margin-bottom: 8px;
}

.flow-step-title {
    font-weight: 600;
    margin-bottom: 4px;
}

.flow-meta {
    font-size: 0.9rem;
    color: #334155;
}
</style>
""", unsafe_allow_html=True)


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
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence * 100,
        domain={'x': [0.08, 0.92], 'y': [0, 1]},
        number={'suffix': "%", 'font': {'size': 28}},
        title={'text': "Confidence Score", 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 50], 'color': "#ef4444"},
                {'range': [50, 75], 'color': "#f59e0b"},
                {'range': [75, 100], 'color': "#22c55e"},
            ],
            'bar': {'thickness': 0.35}
        }
    ))
    fig.update_layout(
        width=320,
        height=200,
        margin=dict(l=8, r=8, t=60, b=0),
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, width="content")


def _pretty_step_name(step_name):
    return step_name.replace("_", " ").strip().title()


def decision_step_label(step_name):
    labels = {
        "surveillance_detected": "Monitoring/Surveillance detected",
        "employment_context": "Employment context detected",
        "biometric_usage": "Biometric data in use",
    }
    return labels.get(step_name, _pretty_step_name(step_name))


def render_decision_flow_diagram(decision_tree, classification):
    if not decision_tree:
        st.info("No decision flow data available.")
        return

    logic_explanations = {
        "surveillance_detected": "Checks whether monitoring keywords like monitor/track are present.",
        "employment_context": "Checks whether an employee/worker context is present.",
        "biometric_usage": "Checks whether biometric indicators (face/voice/emotion) are present.",
    }

    for i, step in enumerate(decision_tree, start=1):
        status = "PASS" if step["value"] else "FAIL"
        color = "#16a34a" if step["value"] else "#dc2626"
        title = decision_step_label(step["step"])
        detail = logic_explanations.get(step["step"], "Regel aus der Decision Engine.")
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
    paragraph = source.get("paragraph")

    if paragraph is None or paragraph == "":
        paragraph = "n/a (not available in index)"
    else:
        paragraph = str(paragraph).replace("\n", " ").strip()

    return reference, page, paragraph


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


col1, col2 = st.columns([2, 1])


# ================= CHAT =================
with col1:
    st.markdown('<div class="header-box"><h2>EU AI Act Chat</h2></div>', unsafe_allow_html=True)

    for msg in st.session_state.messages:
        cls = "user-bubble" if msg["role"] == "user" else "assistant-bubble"
        st.markdown(f'<div class="{cls}">{msg["content"]}</div>', unsafe_allow_html=True)

    # 🔥 spacing before input
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    user_input = st.chat_input("Ask something...")

    if user_input:
        st.session_state.pending_query = user_input

    if st.session_state.pending_query:
        query = st.session_state.pending_query
        st.session_state.pending_query = None

        st.session_state.messages.append({"role": "user", "content": query})

        with st.spinner("Analyzing..."):
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

            confidence = calculate_confidence(results, decision_data, raw)

            st.session_state.last_debug = {
                "confidence": confidence,
                "classification": answer.get("classification", ""),
                "decision_tree": decision_data["decision_tree"],
                "sources": results
            }

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer["answer"]
            })

            st.session_state.follow_up = generate_followups(decision_data["decision_tree"])
            st.session_state.answers = {}

            st.rerun()

    # ================= FOLLOW UPS =================
    if st.session_state.follow_up:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("### Follow-up Questions")

        for i, q in enumerate(st.session_state.follow_up):
            st.session_state.answers[i] = st.text_input(q, key=f"q_{i}")

        if st.button("Refine Answer"):
            combined = " ".join(st.session_state.answers.values())
            st.session_state.pending_query = combined
            st.session_state.follow_up = []
            st.rerun()


# ================= INSIGHTS =================
with col2:
    st.markdown('<div class="header-box"><h2>Insights</h2></div>', unsafe_allow_html=True)

    debug = st.session_state.last_debug

    if debug:

        st.markdown("### Analytics")

        # 🔥 FIXED LAYOUT (untereinander statt side-by-side)
        st.markdown("**System Analysis**")
        st.write(f"Decision Depth: {len(debug['decision_tree'])}")
        st.write(f"Sources Used: {len(debug['sources'])}")
        st.write(f"Evidence Strength: {round(debug['confidence'],2)}")

        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

        render_gauge(debug["confidence"])

        # 🔥 tighter spacing
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        st.markdown("### Classification")
        st.write(classification_label(debug["classification"]))

        st.markdown("### Decision Flow")
        with st.expander("Show Decision Flow Diagram", expanded=False):
            render_decision_flow_diagram(debug["decision_tree"], debug["classification"])

        for step in debug["decision_tree"]:
            icon = "PASS" if step["value"] else "FAIL"
            st.write(f"{icon}: {decision_step_label(step['step'])}")

        st.markdown("### Sources")
        for idx, s in enumerate(debug["sources"], start=1):
            reference, page, paragraph = format_source_meta(s)
            with st.expander(source_header(reference, idx)):
                st.markdown(f"**Reference:** {reference}")
                st.markdown(f"**Page:** {page}")
                st.markdown(f"**Paragraph:** {paragraph}")
                st.markdown("**Excerpt:**")
                st.info(source_excerpt(s.get("text", "")))
                with st.expander("Show full excerpt", expanded=False):
                    st.write(s.get("text", ""))

