# ASEEL Evaluation Module

A standalone evaluation suite for the existing ASEEL RAG/agent system,
using **DeepEval**.

It is additive: it reads from the existing system and evaluates its
end-to-end outputs without modifying the production RAG pipeline.

## Metrics

| Metric | Ground truth required? | What it evaluates |
|---|---|---|
| **Faithfulness** | No | Whether the generated answer is supported by the retrieved evidence |
| **Answer Relevancy** | No | Whether the answer addresses the user's question |
| **Contextual Relevancy** | No | Whether the retrieved context is relevant to the question |
| **Contextual Recall** | Yes | Whether the retrieved context contains the information needed by the ground-truth answer |

## Setup

Install DeepEval:

```bash
pip install deepeval
```

Set the API key for the configured judge provider.

For OpenAI:

```bash
export OPENAI_API_KEY=...
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="..."
```

The evaluation module currently uses `gpt-4o-mini` as the default
LLM-as-a-judge model.

## Run

Start with a small smoke test:

```bash
python -m evaluation.run_evaluation --limit 5
```

For a larger test:

```bash
python -m evaluation.run_evaluation --limit 20
```

Then run the full evaluation:

```bash
python -m evaluation.run_evaluation
```

Use a specific judge model if needed:

```bash
python -m evaluation.run_evaluation --judge-model gpt-4o-mini
```

The evaluation report is written to:

```text
data/evaluation/eval_report.csv
```

## Timeout Configuration

DeepEval uses asynchronous execution when evaluating the test cases.

The default timeout used in the current environment is 180 seconds.
For larger evaluations, increase the per-task timeout to 300 seconds:

### Windows PowerShell

```powershell
$env:DEEPEVAL_PER_TASK_TIMEOUT_SECONDS="300"
```

### macOS/Linux

```bash
export DEEPEVAL_PER_TASK_TIMEOUT_SECONDS=300
```

Then run:

```bash
python -m evaluation.run_evaluation
```

## Cost and Evaluation Runtime

The full evaluation calls the existing ASEEL graph for every evaluation
question and then applies DeepEval's LLM-as-a-judge metrics.

For hundreds of questions, this can consume a significant number of
API calls and tokens and may take a considerable amount of time.

It is recommended to first verify the setup using:

```bash
python -m evaluation.run_evaluation --limit 5
```

Then:

```bash
python -m evaluation.run_evaluation --limit 20
```

After confirming that the evaluation completes successfully, run the
full evaluation:

```bash
python -m evaluation.run_evaluation
```

## Pipeline Integration

`evaluation/pipeline_integration.py` calls the existing `ask(...)`
function from the ASEEL graph and evaluates the actual end-to-end
response.

The evaluation uses:

- The final generated answer from the ASEEL graph.
- The validated evidence stored in `state["sources"]`.
- `state["retrieved"]` as a fallback when validated sources are unavailable.

If `graph.py` is inside a package, update only the import line in
`evaluation/pipeline_integration.py`.

For example:

```python
from workflow.graph import ask
```

No production RAG files need to be changed.

## Evaluation Flow

```text
Evaluation Questions
        ↓
ASEEL Graph
        ↓
Understanding
        ↓
Retrieval
        ↓
Validation
        ↓
Final Answer + Evidence
        ↓
DeepEval
        ↓
RAG Evaluation Metrics
        ↓
eval_report.csv
```

The evaluation module does not replace or modify the production
retrieval, validation, or response-generation components.

## Contextual Recall

`Contextual Recall` requires a ground-truth answer.

Samples without a resolvable ground-truth answer are skipped from
Contextual Recall rather than being evaluated against an empty
ground-truth value.

The other three metrics can be evaluated without ground-truth answers:

- Faithfulness
- Answer Relevancy
- Contextual Relevancy

## Output

The final evaluation report contains the evaluated questions and
their DeepEval metric results.

The report is saved to:

```text
data/evaluation/eval_report.csv
```

A summary is also printed in the terminal after evaluation.

Example:

```text
=== ASEEL DeepEval Summary ===
Questions evaluated: 20
Faithfulness             0.983  (n=20)
Answer Relevancy         0.788  (n=20)
Contextual Relevancy     0.538  (n=20)
Contextual Recall        0.725  (n=20)
================================
```

These values are examples from a 20-question evaluation run and are
not intended to represent the final full-dataset evaluation results.

## Requirements

The evaluation module requires:

- Python environment with the ASEEL project dependencies installed.
- DeepEval.
- An API key for the configured LLM judge provider.
- The existing ASEEL RAG/agent pipeline.
- Access to the evaluation dataset and knowledge base.

Install DeepEval with:

```bash
pip install deepeval
```

## Files

```text
evaluation/
├── dataset.py
├── deepeval_metrics.py
├── pipeline_integration.py
├── raw_kb.py
├── report.py
├── run_evaluation.py
└── README.md
```

The generated evaluation report is stored separately at:

```text
data/evaluation/eval_report.csv
```

## Notes

This evaluation module is designed to be independent from the
production ASEEL RAG pipeline.

Changes to the evaluation configuration, judge model, timeout, or
evaluation dataset do not modify the production retrieval or
generation logic.

The evaluation should be run on a small sample first before running
the full dataset to verify API connectivity, model configuration,
retrieval availability, and evaluation stability.
