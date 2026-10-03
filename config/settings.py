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

OPENAI_MODEL_TOOL = os.getenv("ASEEL_MODEL_TOOL", "gpt-5.4-nano")
OPENAI_MODEL_UNDERSTANDING = os.getenv("ASEEL_MODEL_UNDERSTANDING", "gpt-5.4-mini")
OPENAI_MODEL_RESPONSE = os.getenv("ASEEL_MODEL_RESPONSE", "gpt-5.4")
OPENAI_MODEL_TRANSLATION = os.getenv("ASEEL_MODEL_TRANSLATION", "gpt-5.4")

# Kept for any code that hasn't migrated to a specific tier yet.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", OPENAI_MODEL_UNDERSTANDING)