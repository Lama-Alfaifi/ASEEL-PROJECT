أكيد، هذا كامل كـ`README.md` جاهز للنسخ:

````markdown
# ASEEL (أصيل) 🌴 — Agentic AI System for Saudi Cultural Guidance

ASEEL is an agentic AI system for answering questions about Saudi cultural etiquette, customs, and regional traditions.

It uses a curated, region-tagged knowledge base with a Retrieval-Augmented Generation (RAG) pipeline. When relevant evidence is not retrieved with sufficient confidence, ASEEL can fall back instead of generating an unsupported answer.

## Features

- **Multi-agent workflow** — Four specialized agents: Understanding → Retrieval → Validation → Response, orchestrated with LangGraph.
- **Retrieval-Augmented Generation (RAG)** — Retrieves relevant evidence from ChromaDB and applies a configurable relevance threshold before generating an answer.
- **Confidence-based fallback** — When retrieved evidence does not meet the configured relevance threshold, ASEEL can fall back instead of answering from unsupported information.
- **Multilingual support** — Translates non-English queries into English for retrieval and translates the final response back into the user's language.
- **Conversation memory** — Maintains session-based context for follow-up questions.
- **Regional awareness** — Resolves locations into Saudi regional context and uses region metadata during retrieval.
- **Human-in-the-loop feedback** — User feedback is reviewed by a human before approved information can be added to the knowledge base.
- **Deterministic tools** — Uses deterministic Python logic for selected tasks such as region resolution and validation.
- **Model tiering** — Different model configurations can be used for tools, understanding, response generation, and translation.
- **Evaluation** — Includes retrieval and hard-query evaluation pipelines.
- **Monitoring** — Records runtime information such as latency, confidence, region, and processing status.
- **REST API** — Backend implemented with FastAPI.
- **Web interface** — React + TypeScript + Vite frontend with Arabic/English support and interactive features.
- **Docker support** — Includes Docker configuration for containerized execution.

---

## Architecture

```text
                         User
                           │
                           ▼
              ┌─────────────────────────┐
              │   React / Vite Frontend │
              └────────────┬────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │    FastAPI API  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Translation     │
                  │ Layer           │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │    LangGraph    │
                  │    Workflow     │
                  └────────┬────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   Understanding      Retrieval        Validation
                           │                │
                           ▼                │
                    ┌────────────┐          │
                    │  ChromaDB  │          │
                    └─────┬──────┘          │
                          │                 │
                          └────────┬────────┘
                                   ▼
                            ┌────────────┐
                            │  Response  │
                            └─────┬──────┘
                                  │
                                  ▼
                            Final Answer
````

### Feedback Loop

```text
User Feedback
      │
      ▼
Pending Feedback
      │
      ▼
Human Review
   ┌──┴──┐
   │     │
Approve Reject
   │     │
   │     └──► No knowledge-base update
   │
   ▼
Validation
   │
   ▼
Duplicate Check
   │
   ▼
Knowledge Record
   │
   ▼
ChromaDB
```

Only approved feedback can proceed through the knowledge-base update process.

---

## Knowledge Base

ASEEL currently includes **1,851 records** across six datasets:

| Dataset   |   Records |
| --------- | --------: |
| Central   |       252 |
| East      |       343 |
| General   |       399 |
| North     |       338 |
| South     |       219 |
| West      |       300 |
| **Total** | **1,851** |

The datasets are stored under:

```text
data/raw/
```

---

## How the Pipeline Works

### 1. Understanding

The Understanding agent interprets the user's request and prepares it for the downstream workflow.

For non-English input, the translation layer can translate the query into English before retrieval.

### 2. Retrieval

The Retrieval agent searches the ChromaDB knowledge base for relevant records.

ASEEL uses:

* ChromaDB
* Sentence Transformers
* `all-MiniLM-L6-v2`
* Configurable `TOP_K`
* Configurable minimum relevance threshold

The current default configuration retrieves the top **5** results with a minimum relevance threshold of **0.33**.

### 3. Validation

The Validation agent checks the retrieved evidence before the final response is generated.

This provides an additional step for checking whether the retrieved information is suitable for answering the user's question.

### 4. Response

The Response agent generates the user-facing answer using the validated context.

For multilingual requests, the final answer can then be translated back into the user's original language.

---

## Regional Awareness

ASEEL uses location information as part of its retrieval and routing process.

The system can resolve a city into a broader Saudi regional context and use region metadata during retrieval.

A city is used for routing and regional context; it is not automatically treated as proof that a cultural practice is specific to that city.

The project also includes GeoJSON region data for map-related functionality.

---

## Human-in-the-Loop Feedback

ASEEL includes a feedback workflow designed to keep user-submitted information under human review.

The process is:

1. User submits feedback.
2. Feedback is stored as pending.
3. A human reviewer approves or rejects it.
4. Approved feedback goes through validation checks.
5. Duplicate content is checked.
6. Valid approved feedback is converted into a knowledge record.
7. The record can then be added to ChromaDB.
8. Rejected feedback does not update the knowledge base.

---

## Evaluation

ASEEL includes retrieval and hard-query evaluation pipelines.

### Retrieval Evaluation

The Top-5 relevance analysis contains **1,851 questions**.

Results:

| Metric                   |     Result |
| ------------------------ | ---------: |
| Mean Top-1 relevance     | **0.8572** |
| Mean Top-5 relevance     | **0.6692** |
| Top-1 relevance ≥ 0.33   |   **100%** |
| All Top-5 results ≥ 0.33 | **99.73%** |

A separate retrieval benchmark contains **374 evaluation queries**:

| Retrieval configuration |      Hit@5 |
| ----------------------- | ---------: |
| Old style               | **96.79%** |
| New Pass 1              | **99.73%** |
| New Full                | **99.73%** |

These metrics describe retrieval performance on the included evaluation datasets and should not be interpreted as general accuracy across all possible user questions.

### Hard-Query Evaluation

The hard-query results contain **119 evaluated cases**.

For the main strict Pass 1 configuration:

* **106** cases retrieved the expected result at rank 1.
* **113** cases retrieved the expected result within the top 5.
* **3** cases did not produce a rank.

For the lenient Pass 1 configuration:

* **107** cases retrieved the expected result at rank 1.
* **116** cases retrieved the expected result within the top 5.
* **1** case did not produce a rank.

Additional hard-query evaluation results are available in:

```text
data/eval/hard_results.csv
```

---

## Monitoring

ASEEL records runtime information that can be used to inspect system behavior, including:

* Latency
* Retrieval confidence
* Region
* Processing status
* Failure patterns

Optional LangSmith tracing is also supported.

---

## Project Structure

```text
ASEEL-PROJECT/
│
├── agents/
│
├── api/
│   └── main.py
│
├── aseel-frontend/
│
├── config/
│   └── settings.py
│
├── data/
│   ├── raw/
│   ├── eval/
│   └── ...
│
├── memory/
│
├── prompts/
│
├── retrieval/
│
├── scripts/
│
├── tests/
│
├── tools/
│
├── translation/
│
├── utils/
│
├── workflow/
│
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Tech Stack

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic

### Agentic AI

* LangChain
* LangGraph
* OpenAI models

### Retrieval

* ChromaDB
* Sentence Transformers
* `all-MiniLM-L6-v2`

### Frontend

* React
* TypeScript
* Vite
* Tailwind CSS

### Evaluation & Testing

* DeepEval
* pytest

### Observability

* LangSmith
* Runtime monitoring

### Deployment

* Docker

---

## Configuration

ASEEL reads configuration from a `.env` file.

Example:

```env
OPENAI_API_KEY=your_api_key_here

ASEEL_MODEL_TOOL=gpt-5.4-nano
ASEEL_MODEL_UNDERSTANDING=gpt-5.4-mini
ASEEL_MODEL_RESPONSE=gpt-5.4
ASEEL_MODEL_TRANSLATION=gpt-5.4

ASEEL_COLLECTION=aseel_cultural_knowledge
ASEEL_TOP_K=5
ASEEL_MIN_RELEVANCE=0.33

LANGSMITH_API_KEY=
LANGSMITH_TRACING=false
```

The model names above correspond to the defaults defined in `config/settings.py`.

**Do not commit your `.env` file or API keys to the repository.**

---

## Getting Started

### Prerequisites

* Python 3.11+
* Node.js 18+
* OpenAI API key
* Docker (optional)

### 1. Clone the repository

```bash
git clone https://github.com/Lama-Alfaifi/ASEEL-PROJECT.git
cd ASEEL-PROJECT
```

### 2. Create a Python virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
```

Additional configuration can be added using the variables shown in the Configuration section.

### 5. Build the knowledge index

```powershell
python -m scripts.build_index
```

### 6. Run the API

```powershell
uvicorn api.main:app --reload --port 8000
```

### 7. Run the frontend

Navigate to the frontend directory:

```powershell
cd aseel-frontend
npm install
npm run dev
```

---

## Running the Frontend and API Together

ASEEL also includes a Python UI server:

```powershell
python aseel-frontend/serve_ui.py
```

The server is configured to run on:

```text
http://localhost:8000
```

---

## Docker

ASEEL includes a `Dockerfile` for containerized execution.

Build the image:

```powershell
docker build -t aseel .
```

Run the container:

```powershell
docker run -p 8000:8000 --env-file .env aseel
```

Make sure the required environment variables are available before starting the container.

---

## Testing

Run the test suite:

```powershell
python -m pytest tests/ -v
```

For output-quality tests:

```powershell
python -m pytest tests/test_output_quality.py -v -s
```

Evaluation datasets and results are available under:

```text
data/eval/
```

Supporting evaluation scripts are located under:

```text
scripts/
```

---

## Example Questions

```text
What should I consider when visiting a Saudi family for the first time?

What are some traditional hospitality customs in Saudi Arabia?

What should guests consider when attending a Saudi cultural gathering?

What are appropriate clothing considerations for a cultural visit?

What customs are associated with a specific Saudi region?
```

ASEEL is designed to ground its responses in retrieved knowledge rather than relying only on the model's general knowledge.

---

## Key Design Principles

### Grounded Responses

ASEEL prioritizes retrieved evidence when generating answers.

### Controlled Uncertainty

When retrieved evidence does not meet the configured relevance threshold, the system can fall back rather than present unsupported information as fact.

### Human Oversight

User feedback does not directly modify the knowledge base. Approved updates go through a human review process.

### Deterministic Where Possible

Selected tasks such as region resolution and validation use deterministic logic where an LLM is not necessary.

### Modular Agent Design

Each agent has a defined responsibility, making the workflow easier to test and modify.

---

## Project Status

ASEEL was developed as a final project during the **Saudi Digital Academy (SDA) Agentic AI Engineering program**.

The project combines:

* Multi-agent orchestration
* LangGraph
* RAG
* Vector search
* Multilingual processing
* Validation
* Human-in-the-loop feedback
* Retrieval evaluation
* Monitoring
* FastAPI
* React
* Docker

---

## Future Improvements

Potential future improvements include:

* Expanding and continuously reviewing the cultural knowledge base
* Improving retrieval evaluation coverage
* Adding more multilingual evaluation
* Expanding monitoring and observability
* Improving the feedback-review interface
* Adding additional safeguards for ambiguous cultural questions
* Further optimizing retrieval and model usage

---

## License

This project is provided for educational and portfolio purposes.

```
```
