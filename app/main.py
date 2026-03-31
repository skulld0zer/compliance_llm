from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
from app.rag_pipeline import retrieve
from app.llm import generate_answer
from app.decision_engine import analyze_question
from app.confidence import calculate_confidence

app = FastAPI()

class Query(BaseModel):
    question: str

@app.post("/ask")
def ask(q: Query):
    results = retrieve(q.question)

    decision_data = analyze_question(q.question)

    answer = generate_answer(
        q.question,
        results,
        decision_data["hints"],
        decision_data["pre_classification"]
    )

    confidence = calculate_confidence(results, decision_data, answer)

    return {
        "question": q.question,
        "answer": answer,
        "sources": results,
        "debug": {
            "decision_tree": decision_data["decision_tree"],
            "pre_classification": decision_data["pre_classification"],
            "confidence": confidence
        }
    }