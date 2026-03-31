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


st.set_page_config(layout="wide")


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
    st.title("AI Act Chat")

    # Chat history anzeigen
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Input
    user_input = st.chat_input("Ask something...")

    if user_input:
        st.session_state.pending_query = user_input

    # Verarbeitung
    if st.session_state.pending_query:

        query = st.session_state.pending_query
        st.session_state.pending_query = None

        # User message speichern
        st.session_state.messages.append({
            "role": "user",
            "content": query
        })

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                # RAG
                results = retrieve(query)

                # Decision Engine
                decision_data = analyze_question(query)

                # LLM Answer
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
                    answer = {
                        "answer": raw
                    }

                # Confidence
                confidence = calculate_confidence(results, decision_data, raw)

                # DEBUG speichern
                st.session_state.last_debug = {
                    "confidence": confidence,
                    "classification": answer.get("classification", ""),
                    "decision_tree": decision_data["decision_tree"],
                    "sources": results
                }

                # Antwort anzeigen
                st.write(answer["answer"])

                # 🔥 WICHTIG: Follow-ups kommen jetzt aus ENGINE
                st.session_state.follow_up = generate_followups(decision_data["decision_tree"])

                # Assistant message speichern
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer["answer"]
                })

    # ================= FOLLOW UPS =================
    if st.session_state.follow_up:
        st.markdown("### Need more details:")

        inputs = []

        for i, q in enumerate(st.session_state.follow_up):
            val = st.text_input(q, key=f"follow_{i}")
            inputs.append(val)

        if st.button("Refine Answer"):

            structured = " ".join([
                f"{q}: {a}" for q, a in zip(st.session_state.follow_up, inputs) if a
            ])

            # letzte user frage holen
            last_user = None
            for msg in reversed(st.session_state.messages):
                if msg["role"] == "user":
                    last_user = msg["content"]
                    break

            new_query = f"{last_user}\nAdditional details:\n{structured}"

            # reset
            st.session_state.follow_up = []
            st.session_state.pending_query = new_query

            st.rerun()


# ================= INSIGHTS =================
with col2:
    st.title("Insights")

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
            title = f"{s['reference']}"

            with st.expander(title):
                st.caption(f"Relevance score: {round(s['score'], 3)}")
                st.write(s["text"])