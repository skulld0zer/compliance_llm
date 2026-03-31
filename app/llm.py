from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def generate_answer(question, context_chunks, hints, pre_classification):

    context = "\n\n".join([
        f"[{c['reference']}] {c['text']}" for c in context_chunks
    ])

    prompt = f"""
You are an EU AI Act classification assistant.

Your goal is:
1. Classify the use case
2. Provide a clear answer
3. Ask ONLY for missing inputs that affect classification

IMPORTANT RULES:

- Follow-up questions MUST be about the USER'S SYSTEM
- NEVER ask general legal/compliance questions
- ONLY ask questions that change risk classification

GOOD follow-ups:
- Does the system make decisions affecting employment?
- Is biometric data used?
- Is monitoring continuous or occasional?
- Are workers aware?

BAD follow-ups:
- What legal requirements apply?
- What oversight measures are required?

---

Context:
{context}

Question:
{question}

Return STRICT JSON:

{{
"classification": "...",
"answer": "Clear answer WITH MULTIPLE references like [Annex III], [Article 72]",
"reasoning": ["step1", "step2"],
"follow_up": ["max 3 precise questions about the system"]
}}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=500
    )

    return response.choices[0].message.content