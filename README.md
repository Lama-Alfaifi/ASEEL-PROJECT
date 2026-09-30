# ASEEL (أصيل) 🌴 — Agentic AI System for Saudi Cultural Guidance
 
ASEEL is an agentic AI system that answers questions about Saudi cultural
etiquette, customs, and regional traditions — grounded strictly in a
curated, region-tagged knowledge base. If the evidence isn't there or isn't
strong enough, ASEEL says so instead of guessing.
 
## Features
 
- **Four-agent pipeline** (Understanding → Retrieval → Validation →
  Response), orchestrated with LangGraph. Each agent has one job; only the
  Response agent ever writes user-facing text.
- **Retrieval-Augmented Generation**: answers are built only from evidence
  retrieved from ChromaDB and scored against a confidence threshold — below
  it, ASEEL refuses rather than fabricating an answer.
- **Multilingual support**: a translation layer wraps the pipeline
  (language detection + translate in → English → translate the final
  answer back), verified end-to-end for English, Arabic, French, Chinese,
  Urdu, and Indonesian.
- **Conversation memory**: session-based, server-side context so follow-up
  questions ("What about women?") correctly inherit the city, region, and
  topic from earlier turns.
- **Regional awareness**: city → administrative region → planning region
  resolution, backed by a real Saudi location dataset and GeoJSON region
  boundaries for map display. A city is used for routing only — never
  treated as proof a custom is city-specific.
- **Human-in-the-loop feedback**: users can flag an answer; a reviewer
  dashboard lets a human approve or reject it. Only approved feedback is
  converted into a knowledge-base record and upserted into ChromaDB —
  no automated process publishes anything on its own.
- **Deterministic tools where it matters**: region resolution, evidence
  validation, and metadata filtering are plain Python, not LLM judgment —
  kept reproducible and cheap.
- **Model tiering**: lightweight models handle tool/control agents
  (retrieval, validation); the strongest available model is reserved for
  the response the user actually reads and for translation.
- **Evaluation**: DeepEval (Answer Relevancy, Faithfulness) across
  grounded, fallback, multi-turn, and multilingual test cases, plus unit
  tests for every deterministic component.
- **Monitoring**: every run is logged (latency, confidence, region,
  status, failure pattern) and exposed via `/metrics`; LangSmith tracing
  is optional.
- **REST API + web frontend**: FastAPI backend, React + TypeScript +
  Vite frontend with bilingual (EN/AR) UI, an interactive region map, and
  a command palette.
- **Docker-ready** for containerized deployment.
## Architecture
 
```
User ──► Frontend (aseel-frontend, React + Vite)
              │
              ▼
        FastAPI (api/main.py)
              │
              ▼
   Translation layer (translation/)  ← detect + translate in/out
              │
              ▼
   LangGraph Workflow (workflow/graph.py)
     ├── Understanding  (agents/understanding.py)
     ├── Retrieval      (agents/retrieval_agent.py)
     ├── Validation     (agents/validation.py)
     └── Response       (agents/response.py)
              │
     ┌────────┴─────────┐
     ▼                   ▼
Tools (tools/)      Retrieval (retrieval/)
 region resolution,  ChromaDB + sentence-transformers
 evidence validation,
 metadata filtering
              │
              ▼
   Memory (memory/) · Monitoring (utils/monitoring.py)
   Feedback → Human Review → Knowledge Base (utils/feedback_service.py)
              │
              ▼
        LLM (OpenAI via LangChain)
```
 
## Project Structure
 
| Path | Description |
|---|---|
| `agents/` | The four agents (understanding, retrieval, validation, response) and shared state |
| `api/` | FastAPI application — `/chat`, `/feedback`, `/metrics`, `/regions-*`, `/locate` |
| `aseel-frontend/` | React + TypeScript + Vite web frontend |
| `config/` | Application settings, including the per-agent model tiers |
| `data/` | Regional CSVs (`data/raw/`), location lookup, region GeoJSON, feedback log, monitoring log |
| `memory/` | Per-session conversation memory |
| `prompts/` | Shared prompt text (e.g. the response agent's grounding rules) |
| `retrieval/` | Ingestion, `KnowledgeRecord` schema, and the ChromaDB-backed vector store |
| `scripts/` | `build_index.py` and offline retrieval-quality analysis scripts |
| `tests/` | Unit tests and the DeepEval-based quality suite |
| `tools/` | Deterministic tools the agents call (region resolution, evidence validation, metadata filtering, location lookup) |
| `translation/` | The inbound/outbound translation layer |
| `utils/` | Monitoring, feedback storage/service, region-to-map-region mapping |
| `workflow/` | The LangGraph graph definition and the `ask()` entry point |
| `data/regions.geojson` | Saudi administrative region boundaries, used by the interactive map |
| `Dockerfile` | Container build file |
| `requirements.txt` | Python dependencies |
 
## Tech Stack
 
- **Backend**: Python, FastAPI, Uvicorn
- **Agent orchestration**: LangChain, LangGraph
- **LLM**: OpenAI (via `langchain-openai`), tiered by agent role
- **Vector store**: ChromaDB
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`)
- **Frontend**: React, TypeScript, Vite
- **Validation**: Pydantic
- **Evaluation**: DeepEval, pytest
- **Deployment**: Docker
## Getting Started
 
### Prerequisites
 
- Python 3.11+
- An OpenAI API key
- Node.js 18+ (for the frontend)
- Docker (optional)
### 1. Clone the repository
 
```bash
git clone https://github.com/fatimacoding/ASEEL-Agentic-AI.git
cd ASEEL-Agentic-AI
```
 
### 2. Set up the backend
 
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
 
### 3. Configure environment variables
 
Create a `.env` file in the project root:
 
```dotenv
OPENAI_API_KEY=your_api_key_here
 
# Optional overrides — defaults are already tuned per agent role
ASEEL_MODEL_TOOL=gpt-5.4-nano          # retrieval + validation (control agents)
ASEEL_MODEL_UNDERSTANDING=gpt-5.4-mini # query understanding + translation (inbound)
ASEEL_MODEL_RESPONSE=gpt-5.4           # user-facing answer
ASEEL_MODEL_TRANSLATION=gpt-5.4        # final-answer translation (outbound)
 
ASEEL_COLLECTION=aseel_cultural_knowledge
ASEEL_TOP_K=5
ASEEL_MIN_RELEVANCE=0.33
 
# Optional: LangSmith tracing
LANGSMITH_API_KEY=
LANGSMITH_TRACING=false
```
 
### 4. Build the knowledge base
 
Loads every CSV in `data/raw/` and indexes it into ChromaDB:
 
```bash
python -m scripts.build_index
```
 
Re-run this whenever the source CSVs change. It replaces the collection
built from `data/raw/` — it does **not** touch records added later through
the approved-feedback pipeline, which uses a separate, additive upsert.
 
### 5. Run the API
 
```bash
uvicorn api.main:app --reload --port 8000
```
 
The API is available at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.
 
> If `pytest`/module imports complain about missing packages, run from the
> project root and prefer `python -m pytest` — an empty `conftest.py` at
> the root also fixes this permanently.
 
### 6. Run the frontend
 
**Development** (Vite dev server, proxies `/api` to FastAPI):
 
```bash
cd aseel-frontend
npm install
npm run dev
```
 
**Production-style** (single origin, no CORS needed):
 
```bash
cd aseel-frontend
npm install && npm run build
cd ..
python aseel-frontend/serve_ui.py   # serves the built frontend + API at :8000
```
 
### Docker
 
```bash
docker build -t aseel .
docker run -p 8000:8000 --env-file .env aseel
```
 
## Testing & Evaluation
 
Run the full test suite:
 
```bash
python -m pytest tests/ -v
```
 
Run the DeepEval-based quality suite (LLM calls — slower, costs API
credits):
 
```bash
python -m pytest tests/test_output_quality.py -v -s
```
 
## Feedback → Knowledge Base Loop
 
1. A user flags an answer from the chat UI (`POST /feedback`), stored as
   `status: pending` in `data/feedback.jsonl`.
2. A human reviewer opens the Feedback dashboard, reads the flagged
   message alongside the original question and answer, and clicks
   **Approve** or **Reject**.
3. On **Approve**, `utils/feedback_service.py` runs a deterministic
   content check, resolves a region, checks for near-duplicates against
   the existing knowledge base, converts the feedback into the same
   `KnowledgeRecord` schema used everywhere else, and **upserts** it into
   ChromaDB — the original ~550 curated records are never touched or
   rebuilt.
4. The feedback item is updated with `knowledge_base_status`
   (`added` / `skipped_duplicate` / `failed`) so the reviewer always knows
   what actually happened, not just that a button was clicked.
5. **Reject** marks the item `status: rejected` and changes nothing in
   ChromaDB. No automated process ever approves feedback — a human decides.
## Example Questions
 
- "What is the proper etiquette when visiting a Saudi home?"
- "How is Arabic coffee traditionally served?"
- "What traditional clothing is common for men in Dammam?"
- "ما هو اللباس التقليدي للرجال في الدمام؟"
- "Quels vêtements traditionnels les hommes portent-ils à Djeddah?"
## Roadmap
 
- [ ] Expand the cultural knowledge base across all regions
- [ ] Add voice input and output
- [ ] Add more evaluation benchmarks and languages
- [ ] Authenticate the feedback review dashboard
 
