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
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")