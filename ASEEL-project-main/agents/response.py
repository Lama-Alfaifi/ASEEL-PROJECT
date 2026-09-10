from __future__ import annotations
from openai import OpenAI
from agents.state import AseelState
from config.settings import OPENAI_API_KEY, OPENAI_MODEL
from prompts.response import SYSTEM_PROMPT

def _deterministic_answer(state: AseelState) -> str:
    facts = state.get("validated", [])
    if not facts:
        return "I could not find relevant guidance in the supplied ASEEL cultural knowledge base. Please try naming the region or describing the situation more specifically."
    opening = f"For {state.get('region') or facts[0]['region']} Saudi Arabia, the knowledge base indicates:"
    lines = [f"- {fact['answer']}" for fact in facts[:3]]
    return opening + "\n" + "\n".join(lines)

def generate_response(state: AseelState) -> dict:
    facts = state.get("validated", [])
    if not facts:
        return {"answer": _deterministic_answer(state), "status": "fallback", "sources": []}
    if OPENAI_API_KEY:
        evidence = "\n".join(f"[{i+1}] Region={x['region']}; Q={x['question']}; A={x['answer']}" for i, x in enumerate(facts))
        prompt = f"User question: {state['query']}\nUser role: {state.get('user_role')}\nOccasion: {state.get('occasion')}\n\nKnowledge records:\n{evidence}\n\nGive an actionable answer with a short 'Source scope' note."
        answer = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(model=OPENAI_MODEL, messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":prompt}], temperature=0.2).choices[0].message.content
    else:
        answer = _deterministic_answer(state)
    return {"answer": answer, "status": "grounded", "sources": facts}