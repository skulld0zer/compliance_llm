import sys
import os
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

st.markdown("""
<style>

/* ===== Background ===== */
.stApp {
    background: none;
}

body::before {
    content: "";
    position: fixed;
    inset: 0;
    background: url("https://i.ibb.co/yzj7dwz/vivid-blurred-colorful-wallpaper-background.jpg");
    background-size: cover;
    background-position: center;
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

/* ===== Header ===== */
.header-box {
    backdrop-filter: blur(20px);
    background: rgba(255,255,255,0.6);
    border-radius: 20px;
    padding: 16px 20px;
    margin-bottom: 20px;
}

/* ===== Glass ===== */
.glass {
    backdrop-filter: blur(20px);
    background: rgba(255,255,255,0.65);
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.08);
}

/* ===== Chat ===== */
.user-bubble {
    background: #007AFF;
    color: white;
    padding: 12px 18px;
    border-radius: 20px;
    max-width: 70%;
    margin-left: auto;
    margin-bottom: 12px;
}

.assistant-bubble {
    background: rgba(255,255,255,0.9);
    padding: 12px 18px;
    border-radius: 20px;
    max-width: 70%;
    margin-right: auto;
    margin-bottom: 12px;
}

/* ===== CHAT INPUT FIX (DER WICHTIGE PART) ===== */

/* kompletter wrapper */
div[data-testid="stChatInput"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* innerer grauer balken */
div[data-testid="stChatInput"] > div {
    background: transparent !important;
    border: none !important;
}

/* textarea */
textarea {
    border-radius: 20px !important;
    padding: 14px !important;
    background: rgba(255,255,255,0.9) !important;
}

/* ===== Layout ===== */
.block-container {
    padding-top: 2rem;
}

[data-testid="column"] {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

</style>
""", unsafe_allow_html=True)


# ================= HELPERS =================
def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else None


def confidence_label(c):
    if c > 0.75:
        return "High"
    elif c > 0.5:
        return "Medium"
    else:
        return "Low"


def classification_label(c):
    mapping = {
        "prohibited": "🚫 Prohibited",
        "high-risk": "⚠️ High Risk",
        "limited": "ℹ️ Limited",
        "minimal": "✅ Minimal",
    }
    return mapping.get(c, c)


# ================= STATE =================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_debug" not in st.session_state:
    st.session_state.last_debug = None

if "follow_up" not in st.session_state:
    st.session_state.follow_up = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


col1, col2 = st.columns([2, 1])


# ================= CHAT =================
with col1:

    st.markdown('<div class="header-box"><h2>EU AI Act Chat</h2></div>', unsafe_allow_html=True)

    # ✅ WICHTIG: KEIN offenes div mehr!
    with st.container():

        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="assistant-bubble">{msg["content"]}</div>', unsafe_allow_html=True)

        user_input = st.chat_input("Ask something...")

        if user_input:
            st.session_state.pending_query = user_input

        if st.session_state.pending_query:

            query = st.session_state.pending_query
            st.session_state.pending_query = None

            st.session_state.messages.append({
                "role": "user",
                "content": query
            })

            with st.spinner("Thinking..."):

                results = retrieve(query)
                decision_data = analyze_question(query)

                raw = generate_answer(
                    query,
                    results,
                    decision_data["hints"],
                    decision_data["pre_classification"]
                )

                clean = extract_json(raw)

                try:
                    answer = json.loads(clean)
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

                st.rerun()


# ================= INSIGHTS =================
with col2:

    st.markdown('<div class="header-box"><h2>Insights</h2></div>', unsafe_allow_html=True)

    with st.container():

        debug = st.session_state.last_debug

        if debug:
            st.markdown("### Confidence")
            st.progress(float(debug["confidence"]))
            st.write(f"{round(debug['confidence']*100)}% ({confidence_label(debug['confidence'])})")

            st.markdown("### Classification")
            st.write(classification_label(debug["classification"]))

            st.markdown("### Decision Flow")
            for step in debug["decision_tree"]:
                icon = "✅" if step["value"] else "❌"
                st.write(f"{icon} {step['step']}")

            st.markdown("### Sources")
            for s in debug["sources"]:
                title = f"{s.get('reference','Unknown')}"

                with st.expander(title):
                    st.caption(f"Relevance score: {round(s.get('score',0), 3)}")
                    st.write(s["text"])