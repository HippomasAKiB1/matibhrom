# Matibhrom Quickstart Guide

Matibhrom is a rigorous benchmark and evaluation platform for Bengali LLM hallucinations across 4 conditions:
- **C0**: Closed-book (no evidence)
- **C1**: Oracle evidence
- **C2**: RAG retrieval
- **C3**: RAG with explicit abstention instruction

---

## 1. Setup & Installation

### Requirements
- Python 3.11+
- Git

### Install dependencies
```bash
# Clone and navigate to repo
git clone <repo-url> matibhrom
cd matibhrom

# Install in editable mode with CLI scripts
pip install -e .
```

### Configure API Keys
Create a `.env` file in the project root (gitignored):
```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```
> **Note**: You can use free OpenRouter models without incurring costs by setting `model: "openrouter/nvidia/nemotron-3-super-120b-a12b:free"` or `"openrouter/auto"` in `configs/models.yaml`.

---

## 2. Dataset Validation

Before executing experiments, validate data integrity, uniqueness, schema versions, and ensure zero group leakage across train/dev/test splits:
```bash
matibhrom-validate --items data/dummy/items.jsonl --evidence data/dummy/evidence.jsonl --corpus data/dummy/corpus.jsonl --min-corpus-passages 5
```
Or for the full benchmark:
```bash
matibhrom-validate --items data/benchmark/items.jsonl --evidence data/benchmark/evidence.jsonl --corpus data/benchmark/corpus.jsonl
```

---

## 3. Build RAG Vector Index

Build dense embeddings (`BAAI/bge-m3`, 1024-dim) and FAISS index:
```bash
matibhrom-build-index --corpus data/dummy/corpus.jsonl --output outputs/dummy_index/retrieval/index --dim 1024 --device cpu
```

---

## 4. Pre-Flight Budget Check & Dry Run

Check estimated token usage and cost bounds against `configs/budget.yaml`:
```bash
matibhrom-check-budget --budget-config configs/budget.yaml --split dev
```

Run a dry run (prints planned generation calls without invoking LLM APIs):
```bash
matibhrom-run --config configs/experiments.yaml --models configs/models.yaml --rag-config configs/rag.yaml --budget-config configs/budget.yaml --run-id test_dry --split dev --dry-run
```

---

## 5. Running the Benchmark

Execute the generation runner with multi-worker concurrency and caching:
```bash
matibhrom-run \
  --config configs/experiments.yaml \
  --models configs/models.yaml \
  --rag-config configs/rag.yaml \
  --budget-config configs/budget.yaml \
  --run-id run_dev_v1 \
  --split dev \
  --workers 4 \
  --resume
```

### Resuming & Failure Recovery
The runner is crash-resilient:
- **Resumability**: If interrupted (SIGKILL / power loss), add `--resume` to continue exactly from the last saved generation without re-invoking already completed tasks.
- **Lock Cleanup**: Stale locks from dead PIDs are automatically identified via `psutil` and reaped.
- **Corrupt Lines**: Any partial JSONL write from a sudden crash is quarantined to `corrupt_lines.log` and cleanly discarded.

---

## 6. Annotation & Pilot Gate

### 6.1 Sample Generations for Annotation
Sample primary and overlap evaluation sets under configured scope (A, B, or C):
```bash
matibhrom-sample-annotation --run-id run_dev_v1 --config configs/annotation.yaml
```

### 6.2 Pre-Labeling (Optional LLM Pass)
Run first-pass pre-labeling with retry-with-reformat fallbacks:
```bash
python src/annotation/prelabel.py --run-id run_dev_v1 --items data/dummy/items.jsonl
```

### 6.3 Pilot Agreement Gate (§14.5)
Enforce Cohen's $\kappa \ge 0.70$ on pilot annotations before committing annotators to full evaluation:
```bash
matibhrom-compute-iaa --run-id run_dev_v1 --pilot
```

### 6.4 Human Annotation & Adjudication UI
Launch the Streamlit annotation portal:
```bash
streamlit run src/annotation/app.py -- --run-id run_dev_v1
```
- **Annotators**: Blinded view (model, prompt condition, and domain masked).
- **Adjudicators**: Sign in with an adjudicator token to access the Adjudication Queue, view conflicting annotator ratings side-by-side, and unmask metadata.

---

## 7. Export Publication Artifacts

Compile final LaTeX tables, summary markdown, paired statistical comparisons, and retrieval diagnostics:
```bash
matibhrom-export-tables --run-id run_dev_v1 --group-by condition
```

Generated artifacts in `outputs/{run_id}/reports/`:
- `metrics.csv`: Tabular metrics per group
- `summary.md`: Complete summary with 95% Bootstrap CIs and McNemar paired tests
- `tables/primary_metrics.tex`: Camera-ready LaTeX table with confidence intervals
- `retrieval_diagnostics.md`: Recall@k, Top-1 precision broken down by language and domain
- `tokenization_report.md`: Prompt token analysis across Bangla vs Banglish
- `plots/*.png`: Visual distributions for each metric

---

## 8. Continuous Integration / Smoke Test

Run the full end-to-end benchmark suite offline without requiring network access:
```bash
python scripts/ci_smoke.py
```
Or run unit and regression test suite:
```bash
pytest tests/ -v
```
