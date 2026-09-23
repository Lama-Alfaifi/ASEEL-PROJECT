from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
VECTOR_DB_DIR = ROOT_DIR / "data" / "vector_store"
COLLECTION_NAME = os.getenv("ASEEL_COLLECTION", "aseel_cultural_knowledge")
TOP_K = int(os.getenv("ASEEL_TOP_K", "5"))
MIN_RELEVANCE = float(os.getenv("ASEEL_MIN_RELEVANCE", "0.33"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ------------------------------------------------------------------
# Model tiering
#
# Not every agent needs the same model. The system stays agentic across
# all four agents (each is still a real LLM making a real decision), but
# the model backing each one is sized to how demanding that decision
# actually is:
#
# - TOOL agents (retrieval, validation) make simple, mechanical
#   tool-calling decisions with a tightly constrained protocol. A
#   lightweight model is enough, and validation_agent specifically has a
#   deterministic safety net (agents/validation.py reads the tool's own
#   payload as the source of truth, not the model's free-text PASS/RETRY),
#   so a weaker model occasionally misreading its own output doesn't
#   silently corrupt the confidence score.
# - The UNDERSTANDING agent needs genuine language understanding (parsing
#   follow-ups, pronouns, building a standalone retrieval_query), so it
#   sits a tier above the tool agents.
# - The RESPONSE agent is the only one the user directly reads. Its
#   output quality — grounding discipline, the city-to-region wording
#   rules, tone — matters more than any other single factor in the
#   pipeline, so it keeps the strongest model.
#
# Override any tier independently via .env without touching code.
# ------------------------------------------------------------------

OPENAI_MODEL_TOOL = os.getenv("ASEEL_MODEL_TOOL", "gpt-5.4-nano")
OPENAI_MODEL_UNDERSTANDING = os.getenv("ASEEL_MODEL_UNDERSTANDING", "gpt-5.4-mini")
OPENAI_MODEL_RESPONSE = os.getenv("ASEEL_MODEL_RESPONSE", "gpt-5.4")
OPENAI_MODEL_TRANSLATION = os.getenv("ASEEL_MODEL_TRANSLATION", "gpt-5.4")

# Kept for any code that hasn't migrated to a specific tier yet.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", OPENAI_MODEL_UNDERSTANDING)