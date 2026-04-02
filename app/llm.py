from openai import OpenAI
import os

LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "25"))

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    timeout=LLM_TIMEOUT_SECONDS,
)

def generate_answer(question, context_chunks, hints, pre_classification):

    context = "\n\n".join([
        f"[{c.get('locator') or c['reference']}] {c['text']}" for c in context_chunks
    ])
    decision_guidance = "\n".join([f"- {hint}" for hint in hints]) if hints else "- No additional rule hints."

    prompt = f"""
You are an EU AI Act classification assistant.

Your goal is:
1. Classify the use case
2. Provide a clear answer
3. Ask ONLY for missing inputs that affect classification
4. Separate EU AI Act conclusions from non-AI-Act legal considerations when relevant

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

Decision engine pre-classification:
{pre_classification}

Decision engine hints:
{decision_guidance}

Important interpretation guardrails:
- Do not treat general voice or audio processing alone as biometric identification.
- Distinguish synthetic media generation/manipulation from biometric identification or emotion recognition.
- Do not call a case "unclear" if the main EU AI Act obligation is already reasonably identifiable from the facts.
- When consent, employment, privacy, or image-rights issues arise, explicitly distinguish them from EU AI Act classification.
- Personal productivity assistants for a single user, such as calendar conflict reminders, are usually not high-risk under the EU AI Act.
- Generating marketing images of employees without consent is not automatically high-risk under the EU AI Act; distinguish transparency duties from separate consent/privacy/employment-law concerns.
- If the use case is ambiguous, explain what is known, what is uncertain, and ask only the missing classification-critical question(s).

Context:
{context}

Question:
{question}

Return STRICT JSON:

{{
"classification": "one of: high-risk, transparency, minimal, unclear",
"answer": "Clear answer WITH MULTIPLE exact references like [Article 50, paragraph 2] or [Annex III, paragraph 4]",
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
        max_tokens=500,
        timeout=LLM_TIMEOUT_SECONDS,
    )

    return response.choices[0].message.content
