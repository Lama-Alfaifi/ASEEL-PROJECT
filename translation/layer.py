from __future__ import annotations

import json
import re

from langchain.agents import create_agent

from config.settings import OPENAI_MODEL_UNDERSTANDING, OPENAI_MODEL_TRANSLATION


_ARABIC_RANGE = re.compile(r"[\u0600-\u06FF]")
_NON_ASCII = re.compile(r"[^\x00-\x7F]")


_ARABIC_RANGE = re.compile(r"[\u0600-\u06FF]")
_NON_ASCII = re.compile(r"[^\x00-\x7F]")
_WORD_PATTERN = re.compile(r"[a-zA-Z']+")

# A small set of very common English function words. Their presence is a
# strong signal the text is actually English — unlike a pure-ASCII check,
# which cannot distinguish English from other Latin-script languages that
# happen to use no accented characters (Indonesian, Malay, and similar).
# That gap is exactly what test_indonesian_query_grounded caught: "Apa
# pakaian tradisional pria di Jeddah?" is pure ASCII but not English, and
# a script-only check silently misclassified it.
_ENGLISH_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "which", "who",
    "how", "why", "when", "where", "do", "does", "did", "in", "on", "at",
    "of", "for", "to", "and", "or", "but", "with", "about", "this",
    "that", "i", "you", "he", "she", "it", "we", "they", "can", "could",
    "would", "should", "will", "traditional", "common", "clothing",
}


_ARABIC_RANGE = re.compile(r"[\u0600-\u06FF]")
_NON_ASCII = re.compile(r"[^\x00-\x7F]")
_WORD_PATTERN = re.compile(r"[a-zA-Z']+")

# A small set of very common English function words. Their presence is a
# strong signal the text is actually English — unlike a pure-ASCII check,
# which cannot distinguish English from other Latin-script languages that
# happen to use no accented characters (Indonesian, Malay, and similar).
# That gap is exactly what test_indonesian_query_grounded caught: "Apa
# pakaian tradisional pria di Jeddah?" is pure ASCII but not English, and
# a script-only check silently misclassified it.
_ENGLISH_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "which", "who",
    "how", "why", "when", "where", "do", "does", "did", "in", "on", "at",
    "of", "for", "to", "and", "or", "but", "with", "about", "this",
    "that", "i", "you", "he", "she", "it", "we", "they", "can", "could",
    "would", "should", "will", "traditional", "common", "clothing",
}


def _quick_script_check(text: str) -> str | None:
    """
    Deterministic, zero-latency pre-check before paying for an LLM call.

    Returns "English" only when there's real lexical evidence (recognized
    English function words), not just a script/character-set guess.
    Returns None otherwise — including for pure-ASCII, non-English text
    like Indonesian or Malay — so those correctly fall through to the LLM
    call below rather than being silently misclassified.
    """
    if _ARABIC_RANGE.search(text):
        return None

    if _NON_ASCII.search(text):
        # Accented/non-Latin characters (French, German, etc.) — not
        # confidently English, let the LLM handle it.
        return None

    words = _WORD_PATTERN.findall(text.lower())
    if not words:
        return None

    stopword_hits = sum(1 for w in words if w in _ENGLISH_STOPWORDS)

    # Require both a minimum count and a minimum ratio, so a short
    # question with even one or two recognizable English words 
    # ("what","is") isn't mistaken for a fluke match, while still catching normal
    # English questions confidently.
    if stopword_hits >= 2 and (stopword_hits / len(words)) >= 0.25:
        return "English"

    return None


# ============================================================
# Inbound: detect language + translate to English (ONE LLM call)
# ============================================================
#
# Uses the lighter "understanding" tier, not the strongest model: this is
# short, simple input text, not the nuanced, safety-critical output the
# user actually reads (that stays on the strong model below). Same
# reasoning as the tool agents (retrieval/validation) being on the light
# tier — match the model to how demanding the actual decision is.

_inbound_agent = create_agent(
    model=OPENAI_MODEL_UNDERSTANDING,
    tools=[],
    system_prompt="""
You are ASEEL's Translation Layer (inbound direction).

Your ONLY job is to detect the language of the user's question and, if it
is not English, translate it into English for ASEEL's internal pipeline.

STRICT RULES — the translated query must preserve, unchanged:
- City and region names (transliterate consistently, do not invent an
  English place name that isn't a standard exonym — e.g. "الدمام" becomes
  "Dammam", not a description).
- Gender ("women", "men", "children") exactly as stated.
- Occasion, relationship, role, and any social context mentioned.
- The user's actual intent and scope — do not broaden a specific question
  into a general one, and do not narrow a general question.
- Saudi cultural terms that have no precise English equivalent: keep the
  original term (transliterated) rather than inventing a translation that
  could be wrong. You may add a short bracketed gloss only if it helps
  retrieval, e.g. "majlis [sitting room]".

Do NOT answer the question. Do NOT add information. Do NOT drop any part
of the question's meaning.

If the question is already in English, "translated_query" must be the
original text unchanged, and "detected_language" must be "English".

Return ONLY valid JSON, no other text, in this exact shape:
{
  "detected_language": "<language name in English, e.g. Arabic, French, English>",
  "translated_query": "<the query in English>"
}
""",
)


def _clean_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def detect_and_translate_to_english(query: str) -> tuple[str, str]:
    """
    Returns (detected_language, english_query).

    Fails safe: if the translation call errors or returns unusable JSON,
    treats the query as English and passes it through unchanged rather
    than blocking the whole request.
    """
    if not query or not query.strip():
        return "English", query

    # Zero-cost shortcut for the majority case (pure-ASCII English text).
    # Arabic and every other non-ASCII language still goes through the
    # LLM call below, since translation itself can't be skipped for them.
    quick_result = _quick_script_check(query)
    if quick_result == "English":
        return "English", query

    try:
        result = _inbound_agent.invoke(
            {"messages": [{"role": "user", "content": query}]}
        )

        for message in reversed(result.get("messages", [])):
            content = getattr(message, "content", "")
            if not content:
                continue
            try:
                parsed = json.loads(_clean_json(content))
                detected = parsed.get("detected_language") or "English"
                translated = parsed.get("translated_query") or query
                return detected, translated
            except (TypeError, ValueError, json.JSONDecodeError):
                continue

    except Exception:
        pass

    return "English", query


# ============================================================
# Outbound: translate the final answer back to the user's language
# ============================================================
#
# Only called when detected_language != "English" — the majority-case
# (English questions) never pays for this call at all. Stays on the
# strongest model tier: this is the text the user actually reads, and
# section 3.5's rules (never drop hedges/limitations/confidence wording)
# are safety-critical, not just stylistic.

_outbound_agent = create_agent(
    model=OPENAI_MODEL_TRANSLATION,
    tools=[],
    system_prompt="""
You are ASEEL's Translation Layer (outbound direction).

Your ONLY job is to translate ASEEL's final English answer into the
target language the user asked in, preserving meaning exactly.

STRICT RULES:
- Do NOT add any new information, claims, or cultural facts.
- Do NOT remove any part of the answer, including hedges, uncertainty,
  limitations, or confidence-related wording (e.g. "the evidence does not
  specify...", "based on the available regional evidence..."). These
  qualifications are safety-critical and must survive translation intact.
- Keep Saudi cultural terms and place names as ASEEL originally wrote
  them (transliterated), rather than inventing a new translation for
  them.
- Preserve the tone: concise, respectful, factual.
- Return ONLY the translated answer text — no explanation, no quotes
  around it, no JSON.
""",
)


def translate_from_english(answer: str, target_language: str) -> str:
    """
    Fails safe: on any error, returns the original English answer rather
    than losing the response entirely.
    """
    if not answer or not answer.strip():
        return answer

    if not target_language or target_language.strip().lower() == "english":
        return answer

    try:
        result = _outbound_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Target language: {target_language}\n\n"
                            f"Answer to translate:\n{answer}"
                        ),
                    }
                ]
            }
        )

        for message in reversed(result.get("messages", [])):
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                text = " ".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )
                if text.strip():
                    return text.strip()

    except Exception:
        pass

    return answer