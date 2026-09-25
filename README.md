# Matibhrom - Bengali LLM Hallucination Experiment Platform
# Team Turtlers
# ELITE Research Lab LLC

# Akib - Jaef - Sabit 
# Supervised By - S M Asif Hossain

## README.md --- Research System Specification

> **Name note:** Project name defaults to **Matibhrom** (মতিভ্রম). The Bengali script appears only in the paper title and README header, never in repo paths, package names, config keys, Docker tags, or `run_id` values. If the team chooses a different name, replace `matibhrom` everywhere in this document before feeding it to an agent.

---

## 0. How to use this document

You are an AI coding agent. Build the system described here end-to-end. This document is the single source of truth.

**Rules of engagement:**

1. **Do not invent research scope beyond this document.** If something is listed under §4 Non-goals, do not build it.
2. **Where this document is silent, choose the simplest defensible option and record it in `DECISIONS.md`.** Include the choice, the alternatives considered, and the reason.
3. **Every artifact written to disk must validate against the Pydantic schemas in §9.** Invalid artifacts must be rejected, not repaired silently.
4. **The runner must be resumable and must never silently overwrite existing generations.**
5. **Build against dummy data first.** Real data arrives later and must drop in without code changes.
6. **Freeze prompt templates, model versions, and the test split before the main run.** Enforce this in code, not by convention.
7. **Research questions drive the system.** If a design choice does not serve RQ1–RQ4 (§2.3), do not make it.

---

## 1. Project overview

This project builds an experimental platform for studying hallucination in Bangla Large Language Models.

**Research question:**

> Under which linguistic and evidence conditions do LLMs produce unsupported or incorrect information in Bangla, and how much of that failure can be reduced by retrieval and calibrated abstention?

The system supports controlled evaluation across:

- **Language register:** Standard Bangla (`bn`) and Banglish (`banglish`)
- **Domains:** general factual, medical, Bangladeshi legal
- **Evidence conditions:** C0 (no evidence), C1 (oracle), C2 (realistic RAG), C3 (RAG + abstention)

---

## 2. Research goals, questions, and hypotheses

### 2.1 Goals

| ID | Goal |
|----|------|
| G1 | Build a source-grounded Bangla hallucination benchmark: 600 base questions → 1,200 matched prompts across three domains |
| G2 | Measure the effect of register (Standard Bangla vs. Banglish) holding the factual question constant |
| G3 | Separate missing-evidence failure from evidence-use failure (C0 vs. C1) |
| G4 | Measure how close realistic Bangla RAG comes to the oracle-evidence upper bound (C1 vs. C2) |
| G5 | Evaluate explicit abstention as a mitigation and its coverage trade-off (C2 vs. C3) |
| G6 | Produce a compact error taxonomy with domain-specific medical/legal analysis |
| G7 | Deliver reproducible artifacts: benchmark, code, codebook, IAA statistics, metrics |

### 2.2 Research questions and pre-registered hypotheses

| ID | Research question | Pre-registered hypothesis |
|----|-------------------|---------------------------|
| RQ1 | Does register affect hallucination when the underlying factual question is held constant? | H1: Banglish will show a higher unsupported/incorrect answer rate than Standard Bangla for at least some model families |
| RQ2 | How much of Bangla hallucination is attributable to missing factual evidence rather than failure to use available evidence? | H2: Gold evidence will substantially reduce hallucination relative to no-evidence prompting; the remaining error is evidence-use failure |
| RQ3 | How close can realistic Bangla RAG come to the oracle-evidence upper bound? | H3: Realistic RAG will improve factuality but underperform oracle evidence because retrieval introduces an additional failure mode |
| RQ4 | Does explicit abstention reduce harmful hallucination without unacceptable coverage loss? | H4: RAG + evidence-sufficiency abstention will reduce hallucination rate relative to C2, with a measurable drop in coverage |

### 2.3 Experimental conditions

| Condition | Input | Purpose | Interpretation |
|-----------|-------|---------|----------------|
| C0 | Question only | Natural baseline | Measures unsupported factual generation |
| C1 | Question + gold evidence passage | Upper-bound grounding | Separates knowledge absence from evidence-use failure |
| C2 | Question + top-k retrieved passages | Practical retrieval setting | Adds retrieval errors to the pipeline |
| C3 | Same retrieved passages as C2 + explicit evidence-sufficiency rule | Mitigation | Tests hallucination/coverage trade-off |

**Critical constraint:** C2 and C3 must use identical retrieved context for the same (item, language). The only difference is the abstention instruction. Enforce by caching the C2 retrieval and reusing it for C3.

---

## 3. Benchmark specification

### 3.1 Composition

| Domain | Base questions | Prompt variants | Purpose |
|--------|---------------|-----------------|---------|
| General factual | 200 | 400 | Low-stakes control |
| Medical | 200 | 400 | High-stakes factual and safety-sensitive |
| Legal | 200 | 400 | High-stakes statutes, procedures, case-related |
| **Total** | **600** | **1,200** | Core benchmark |

Each base question has exactly two language realizations: Standard Bangla and Banglish.

### 3.2 Source requirements

Every item must be anchored to an identifiable evidence passage. The benchmark is not built from free-form trivia.

- **General:** stable encyclopedic, governmental, educational, or other authoritative public sources.
- **Medical:** recognized medical/public-health sources or vetted Bangla medical resources. Avoid patient-specific content.
- **Legal:** official or reliably reproduced Bangladeshi statutes, judgments, regulations, or legal-aid information.
- **Never** use a model-generated answer as the gold reference without source verification.
- Exclude items whose answer changes frequently unless a fixed reference date is explicitly encoded.

### 3.3 Question writing protocol

- Prefer one or two factual claims per question. Avoid essay-length prompts.
- Create the Standard Bangla version first.
- Create the Banglish version manually or with machine assistance followed by native-speaker correction.
- Keep meaning, named entities, numbers, and difficulty constant across variants.
- Do not produce "dictionary Banglish." Use realistic digital Bangla-English transliteration conventions.

### 3.4 Data splits

- **Development:** 20% = 120 base items / 240 prompt variants.
- **Held-out test:** 80% = 480 base items / 960 prompt variants.
- **Grouped split:** items derived from the same document or statute must stay in the same split. Use `evidence_id` as the grouping key, or an optional `group_key` field when finer control is needed.
- **No tuning on test.** Prompts and retrieval are tuned only on dev.
- **No fine-tuning** tested models on benchmark answers.
- Check exact and near-duplicate questions before freezing the test set. Near-duplicate threshold: token Jaccard > 0.85 on `question_bn`.
- Record whether source material is likely to have appeared in public web training corpora. This does not invalidate the benchmark but must be acknowledged in the paper.

---

## 4. Non-goals (do not build)

- Large-scale mechanistic interpretability from attention maps or correlations.
- Full LoRA fine-tuning experiments.
- A large multi-dialect benchmark.
- A large prompt-engineering search over many templates.
- ROUGE/BERTScore as primary hallucination metrics.

If the user asks for any of these later, treat it as a new project.

---

## 5. Technology stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.11 | |
| Schema validation | Pydantic v2 | `extra="forbid"` on all models |
| Configuration | YAML + OmegaConf | Hydra optional |
| Local models | vLLM (primary), HuggingFace transformers (fallback) | |
| API models | LiteLLM | Unified OpenAI/Anthropic/Gemini/others |
| Embeddings | `BAAI/bge-m3` default; configurable | Must be Bangla-capable |
| Vector store | FAISS (`IndexFlatIP`) default; Qdrant/Chroma optional | |
| Storage | JSONL primary + SQLite mirror for annotations and cache | Postgres optional |
| Dashboard | Streamlit | |
| Annotation | Streamlit default; Label Studio acceptable | |
| Metrics/stats | scikit-learn, scipy, statsmodels | |
| Plots | matplotlib / seaborn | |
| Testing | pytest | |
| Reproducibility | Git, DVC or git-lfs, Docker | |

---

## 6. Repository structure

```
matibhrom/
├── README.md                      # this file
├── DECISIONS.md                   # agent decisions log
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── .env.example
├── .gitignore
├── configs/
│   ├── models.yaml
│   ├── experiments.yaml
│   ├── rag.yaml
│   ├── annotation.yaml
│   └── prompts/
│       ├── c0_no_evidence_bn.txt
│       ├── c0_no_evidence_banglish.txt
│       ├── c1_oracle_bn.txt
│       ├── c1_oracle_banglish.txt
│       ├── c2_rag_bn.txt
│       ├── c2_rag_banglish.txt
│       ├── c3_rag_abstention_bn.txt
│       ├── c3_rag_abstention_banglish.txt
│       └── abstention_phrase.txt
├── data/
│   ├── benchmark/
│   │   ├── items.jsonl
│   │   └── evidence.jsonl
│   ├── splits/
│   │   ├── dev.txt
│   │   └── test.txt
│   └── dummy/
│       ├── items.jsonl
│       └── evidence.jsonl
├── src/
│   ├── __init__.py
│   ├── schema.py
│   ├── validate_data.py
│   ├── hashing.py
│   ├── model_adapters/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dummy.py
│   │   ├── litellm_adapter.py
│   │   ├── vllm_adapter.py
│   │   └── hf_adapter.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── index.py
│   │   └── retriever.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── builder.py
│   ├── runner/
│   │   ├── __init__.py
│   │   ├── run.py
│   │   ├── generate.py
│   │   ├── cache.py
│   │   └── logging_utils.py
│   ├── annotation/
│   │   ├── __init__.py
│   │   └── app.py
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── app.py
│   └── eval/
│       ├── __init__.py
│       ├── metrics.py
│       ├── stats.py
│       └── report.py
├── scripts/
│   ├── build_index.py
│   ├── make_splits.py
│   ├── sample_for_annotation.py
│   └── export_tables.py
├── outputs/
│   ├── generations/
│   ├── retrieval/
│   ├── annotations/
│   ├── reports/
│   └── cache/
└── tests/
    ├── test_schema.py
    ├── test_validate_data.py
    ├── test_prompts.py
    ├── test_runner.py
    ├── test_rag.py
    └── test_metrics.py
```

---

## 7. Configuration files

### 7.1 `configs/models.yaml`

```yaml
models:
  - id: dummy
    adapter: dummy
    enabled: true
    params:
      response: "ডামি উত্তর।"

  - id: qwen2.5-7b-instruct
    adapter: vllm
    enabled: true
    path: "Qwen/Qwen2.5-7B-Instruct"
    params:
      temperature: 0.0
      max_tokens: 512
      top_p: 1.0

  - id: tigerllm
    adapter: hf
    enabled: false
    path: "TigerLLM/..."     # exact version frozen before main run
    params:
      temperature: 0.0
      max_tokens: 512

  - id: gpt-class
    adapter: litellm
    enabled: false
    model: "openai/gpt-4o"   # exact version frozen before main run
    params:
      temperature: 0.0
      max_tokens: 512
```

**Model policy:** four categories must be represented in the final suite (Bengali-specialized open, multilingual open, general open, frontier proprietary). Model names are configurable, but the *frozen versions* are not. Optional fifth model: a reasoning-focused model only if compute/API budget allows. Do not expand beyond five models unless a reviewer-relevant reason emerges.

### 7.2 `configs/experiments.yaml`

```yaml
run_id: main_v1
split: test
languages: [bn, banglish]
domains: [general, medical, legal]
conditions: [C0, C1, C2, C3]
models: [dummy, qwen2.5-7b-instruct]
rag_config: configs/rag.yaml
prompt_dir: configs/prompts
generation:
  temperature: 0.0
  max_tokens: 512
  seed: 42
  deterministic: true
output_dir: outputs
resume: true
freeze_test: true
```

### 7.3 `configs/rag.yaml`

```yaml
corpus_path: data/benchmark/evidence.jsonl
index_dir: outputs/retrieval/index
chunk_size: 384
chunk_overlap: 64
embedding_model: "BAAI/bge-m3"
top_k: 5
metric: "cosine"
freeze_corpus: true
```

### 7.4 `configs/annotation.yaml`

```yaml
overlap_fraction: 0.25
pilot_size: 120
kappa_threshold: 0.70
hide_model_identity: true
randomize_order: true
adjudication:
  trigger_on:
    - uncertain_label
    - severe_medical_or_legal
    - disagreement_in_overlap
```

---

## 8. Prompt templates

Templates use Python `str.format` placeholders. All templates are frozen before the main run and hashed. Two files per condition, one per language. Do not edit after freeze without a new `run_id`.

### 8.1 `c0_no_evidence_bn.txt`

```
তুমি একজন সহায়ক বাংলা সহকারী। নিচের প্রশ্নের সঠিক উত্তর দাও।

প্রশ্ন: {question}

উত্তর:
```

### 8.2 `c0_no_evidence_banglish.txt`

```
Tumi ekjon helpful Bangla assistant. Nicher proshner shothik uttor dao.

Proshno: {question}

Uttor:
```

### 8.3 `c1_oracle_bn.txt`

```
তুমি একজন সহায়ক বাংলা সহকারী। নিচের প্রমাণ ব্যবহার করে প্রশ্নের উত্তর দাও।

প্রমাণ: {evidence}

প্রশ্ন: {question}

উত্তর:
```

### 8.4 `c1_oracle_banglish.txt`

```
Tumi ekjon helpful Bangla assistant. Nicher proman bebohar kore proshner uttor dao.

Proman: {evidence}

Proshno: {question}

Uttor:
```

### 8.5 `c2_rag_bn.txt`

```
তুমি একজন সহায়ক বাংলা সহকারী। নিচের প্রমাণগুলো ব্যবহার করে প্রশ্নের উত্তর দাও।

প্রমাণ:
{retrieved_context}

প্রশ্ন: {question}

উত্তর:
```

`{retrieved_context}` is the concatenation of top-k passages, each prefixed with `[Passage {i}]`.

### 8.6 `c2_rag_banglish.txt`

```
Tumi ekjon helpful Bangla assistant. Nicher promangulo bebohar kore proshner uttor dao.

Proman:
{retrieved_context}

Proshno: {question}

Uttor:
```

### 8.7 `c3_rag_abstention_bn.txt`

```
তুমি একজন সহায়ক বাংলা সহকারী। নিচের প্রমাণগুলো ব্যবহার করে প্রশ্নের উত্তর দাও।

নিয়ম: যদি প্রদত্ত প্রমাণ প্রশ্নের উত্তর দিতে যথেষ্ট হয়, তবেই উত্তর দাও। প্রমাণ অপর্যাপ্ত হলে ঠিক এই বাক্যটি লেখো:
{abstention_phrase}

প্রমাণ:
{retrieved_context}

প্রশ্ন: {question}

উত্তর:
```

### 8.8 `c3_rag_abstention_banglish.txt`

```
Tumi ekjon helpful Bangla assistant. Nicher promangulo bebohar kore proshner uttor dao.

Niyom: Jodi prodatto proman proshner uttor dite jotheshto hoy, tobei uttor dao. Proman oporjapto hole thik ei bakkoti lekho:
{abstention_phrase}

Proman:
{retrieved_context}

Proshno: {question}

Uttor:
```

### 8.9 `abstention_phrase.txt`

```
প্রমাণ অপর্যাপ্ত, তাই আমি উত্তর দিতে পারছি না।
```

**Abstention detection rule:** normalized exact match. Normalize by stripping leading/trailing whitespace and collapsing internal whitespace. If the response contains the phrase plus other content, log a warning and treat the response as non-abstention. The phrase must be identical across C3 runs; changing it requires a new `run_id`.

---

## 9. Data contracts

All schemas live in `src/schema.py`. Pydantic v2. `extra="forbid"` on all models. All IDs are strings.

### 9.1 `Item`

```python
class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str
    domain: Literal["general", "medical", "legal"]
    question_bn: str
    question_banglish: str
    gold_answer: str
    evidence_id: str
    answer_type: Literal["entity", "numeric", "short explanation", "procedure", "citation"]
    risk_tag: Literal["normal", "high-stakes"]
    split: Literal["dev", "test"]
    group_key: str | None = None   # optional; defaults to evidence_id
```

### 9.2 `Evidence`

```python
class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    text: str
    source_url_or_id: str
    source_date: str          # ISO 8601
    domain: Literal["general", "medical", "legal"]
```

### 9.3 `Generation`

```python
class Generation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    generation_id: str
    item_id: str
    language: Literal["bn", "banglish"]
    condition: Literal["C0", "C1", "C2", "C3"]
    model_id: str
    model_version: str
    prompt: str
    prompt_hash: str
    response: str
    retrieved_evidence_ids: list[str]
    temperature: float
    seed: int | None
    max_tokens: int
    timestamp: str            # ISO 8601 UTC
    latency_ms: int | None
    error: str | None
```

### 9.4 `RetrievalLog`

```python
class RetrievedPassage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rank: int
    passage_id: str
    evidence_id: str
    score: float
    text: str

class RetrievalLog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    item_id: str
    language: Literal["bn", "banglish"]
    query: str
    top_k: int
    retrieved: list[RetrievedPassage]
    gold_evidence_id: str
    gold_retrieved: bool
    recall_at_k: float
    index_version: str
```

### 9.5 `Annotation`

```python
class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generation_id: str
    annotator_id: str
    correctness: Literal["correct", "partially_correct", "incorrect"]
    hallucination: Literal["yes", "no"]
    error_type: Literal["H1", "H2", "H3", "H4", "H5", "A", "R", "none"]
    abstention_status: Literal["none", "appropriate", "unnecessary"]
    notes: str = ""
    timestamp: str
    is_overlap: bool
```

### 9.6 `Adjudication`

```python
class Adjudication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generation_id: str
    adjudicator_id: str
    final_correctness: Literal["correct", "partially_correct", "incorrect"]
    final_hallucination: Literal["yes", "no"]
    final_error_type: Literal["H1", "H2", "H3", "H4", "H5", "A", "R", "none"]
    rationale: str
    timestamp: str
```

### 9.7 Validation rules (`src/validate_data.py`)

Exit non-zero on any error. Print a summary table.

- Every `item.evidence_id` exists in `evidence.jsonl`.
- All `item_id` unique; all `evidence_id` unique.
- `question_bn` and `question_banglish` both non-empty.
- Split assignment is grouped by `group_key` (or `evidence_id` if `group_key` is null).
- No exact duplicate `question_bn` in the test split.
- Near-duplicate check: flag token Jaccard > 0.85 on `question_bn`.
- Domain counts match the spec (200 / 200 / 200 for the full benchmark).
- Dev/test ratio is 20/80 by base item.
- Each `evidence_id` referenced by at least one item; no orphan evidence.
- `risk_tag="high-stakes"` only in medical and legal domains.

---

## 10. Model adapters

### 10.1 Base interface (`src/model_adapters/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class GenerationResult:
    text: str
    model_version: str
    latency_ms: int | None = None
    error: str | None = None

class ModelAdapter(ABC):
    def __init__(self, model_id: str, params: dict):
        self.model_id = model_id
        self.params = params

    @abstractmethod
    def generate(self, prompt: str) -> GenerationResult:
        ...

    def generate_batch(self, prompts: list[str]) -> list[GenerationResult]:
        return [self.generate(p) for p in prompts]

    def unload(self) -> None:
        return None
```

### 10.2 `DummyAdapter`

Returns a fixed string from `params.response`. Deterministic. Used in tests and smoke runs.

### 10.3 `LiteLLMAdapter`

- Wraps `litellm.completion`.
- Passes `temperature`, `max_tokens`, `seed` when supported.
- Records the exact returned model string as `model_version`.
- Retries: 3 attempts with exponential backoff starting at 2s on rate limit/timeout.
- Logs API call date. Never logs API keys.

### 10.4 `VLLMAdapter`

- Loads model once per process via `vllm.LLM`.
- Implements `generate_batch` for throughput.
- Deterministic sampling when `temperature=0`.
- `unload()` frees the engine.

### 10.5 `HFAdapter`

- `transformers.pipeline("text-generation")` fallback.
- `torch_dtype="auto"`, `device_map="auto"`.
- Same interface.

### 10.6 Adapter selection

`src/runner/run.py` loads `configs/models.yaml`, instantiates adapters by the `adapter` key, and filters by the `models` list in the experiment config. Unknown adapter names must raise a clear error.

---

## 11. RAG design

### 11.1 Principles

- Use the frozen evidence corpus from which the benchmark items were sourced.
- Never inject the gold passage directly into C2 or C3. C1 is the only condition that sees gold.
- One retrieval configuration selected on the dev split. Do not tune on test.
- Same retrieved context for C2 and C3 for the same (item, language).

### 11.2 Chunker (`src/rag/chunker.py`)

- Token-based chunking using the embedding model's tokenizer.
- `chunk_size` and `chunk_overlap` from `rag.yaml`.
- Stable `passage_id = f"{evidence_id}::{chunk_index}"`.
- Store chunk text and parent `evidence_id`.

### 11.3 Embedder (`src/rag/embedder.py`)

- Loads `embedding_model` from config.
- Encodes chunks in batches (default 32).
- Normalizes embeddings for cosine similarity via inner product.
- Caches embeddings to `outputs/retrieval/index/embeddings.npy` with a hash of (corpus file, chunk config, model name).

### 11.4 Index (`src/rag/index.py`)

- FAISS `IndexFlatIP` on normalized vectors.
- Persists index and passage metadata to `index_dir`.
- `index_version` = hash of (corpus hash, chunk config, embedding model, build timestamp). Logged with every retrieval.

### 11.5 Retriever (`src/rag/retriever.py`)

- `retrieve(query: str, top_k: int) -> list[RetrievedPassage]`
- For C2/C3, the query is the question in the same language condition.
- `gold_retrieved = any(p.evidence_id == item.evidence_id for p in retrieved)`
- `recall_at_k = 1.0 if gold_retrieved else 0.0` (single-gold setup).

### 11.6 Index build

`scripts/build_index.py` reads `rag.yaml`, builds the FAISS index, and writes `index_version`. Must be re-run if the corpus or chunking changes. Frozen index is a precondition for the main run.

---

## 12. Experiment runner

### 12.1 CLI (`src/runner/run.py`)

```
python -m src.runner.run \
  --config configs/experiments.yaml \
  --models configs/models.yaml \
  --rag-config configs/rag.yaml \
  --run-id main_v1 \
  --split test \
  --resume \
  --unlock-test
```

Flags:

| Flag | Meaning |
|------|---------|
| `--config` | Experiment config path |
| `--models` | Models config path |
| `--rag-config` | RAG config path |
| `--run-id` | Overrides `run_id` in config |
| `--split` | `dev` or `test` |
| `--conditions` | Comma list; overrides config |
| `--models-filter` | Comma list of model IDs; overrides config |
| `--limit` | Run only first N items (smoke test) |
| `--resume` | Skip generations already present |
| `--dry-run` | Print planned calls; write nothing |
| `--unlock-test` | Bypass `freeze_test` guard |
| `--no-cache` | Disable cache reads (still writes) |

### 12.2 Core loop (`src/runner/generate.py`)

```
for item in items_by_split:
    for language in languages:
        for condition in conditions:
            for model in models:
                prompt = build_prompt(item, language, condition)
                key = hash(prompt, model_id, model_version, temperature, max_tokens, seed)
                if resume and key in cache:
                    continue
                if condition in {C2, C3}:
                    retrieved = retriever.retrieve(question, top_k)
                    log_retrieval(...)
                    if condition == C3 and C2_result_cached:
                        reuse_retrieved_from_C2()
                result = model.generate(prompt)
                write Generation(...)
                write cache_entry(...)
```

### 12.3 Generation ID

`generation_id = sha256(f"{run_id}|{item_id}|{language}|{condition}|{model_id}")[:16]`

Deterministic. Enables resume and dedup.

### 12.4 Cache (`src/runner/cache.py`)

- SQLite at `outputs/cache/cache.db`.
- Table `cache(key TEXT PRIMARY KEY, generation_id TEXT, response TEXT, model_version TEXT, timestamp TEXT)`.
- Key = SHA256 of `(prompt, model_id, model_version, temperature, max_tokens, seed)`.
- Cache is per-machine. Never edit manually.

### 12.5 Logging

- One JSONL file per (run_id, model_id, condition) under `outputs/generations/`.
- Flush after every write.
- On error, write a `Generation` with `error` set and continue.
- Write retrieval logs to `outputs/retrieval/{run_id}.jsonl`.

### 12.6 Freeze guard

- If `freeze_test: true` and `--split test` and no `--unlock-test`: exit with a clear error.
- After the first legitimate test run, write `outputs/{run_id}/TEST_RUN_LOCK` with timestamp and config hash.
- Further test runs with the same run_id require `--unlock-test` and append to `outputs/{run_id}/test_run_audit.log`.

### 12.7 Determinism

- Default `temperature=0.0`, `top_p=1.0`, fixed `max_tokens`, fixed `seed` where supported.
- Record `temperature`, `seed`, `max_tokens` in every Generation.
- For APIs that do not support seeds, record `seed: null` and note it in the run report.
- **Stochastic robustness check:** optional, 200-item stratified subset, three seeds/temperature settings, separate `run_id` (`stochastic_v1`). Must not delay the main experiment.

---

## 13. Annotation system

### 13.1 Purpose

Blind annotation of every test response with stratified overlap and adjudication.

### 13.2 UI (`src/annotation/app.py`, Streamlit)

**Show:**

- Question (in the item's language)
- Gold answer
- Evidence passage
- Model response

**Hide:**

- Model identity
- Condition
- Domain (unless needed during adjudication)

**Fields:**

- Correctness: correct / partially correct / incorrect
- Hallucination present: yes / no
- Error type: H1 / H2 / H3 / H4 / H5 / A / R / none
- Abstention/refusal status: none / appropriate / unnecessary
- Notes: free text

**Behavior:**

- Save writes to `annotations.jsonl` immediately and mirrors to SQLite.
- Randomize presentation order per annotator.
- Progress counter and remaining count.
- Jump-to-`generation_id` for adjudication.
- Keyboard shortcuts: 1/2/3 for correctness, y/n for hallucination.

### 13.3 Sampling (`scripts/sample_for_annotation.py`)

- **100% primary annotation** for every test response.
- **25% stratified overlap** independently labeled by a second annotator. Stratify by domain × condition × model category.
- **Third adjudicator** reviews: all uncertain responses, all severe medical/legal hallucinations, all overlap disagreements.
- **Pilot:** 120 responses before full annotation. Compute Cohen's kappa on binary hallucination labels. If kappa < 0.70, revise the codebook and repeat the pilot before full labeling.

### 13.4 Error taxonomy (annotator reference)

| Code | Error type | Example pattern |
|------|-----------|-----------------|
| H1 | Contradiction | Answer conflicts with source-supported fact |
| H2 | Unsupported addition | Adds factual content not supported by available evidence |
| H3 | Fabricated entity/citation | Invents statute, case, institution, medicine, source, or authority |
| H4 | Numeric/temporal error | Wrong dosage, date, amount, threshold, sequence, or duration |
| H5 | Inference error | Evidence is present but model draws an unsupported conclusion |
| A | Appropriate abstention | Declines because available evidence is insufficient |
| R | Unnecessary refusal | Refuses despite sufficient evidence |

### 13.5 Primary definition of hallucination

A response contains hallucination when it asserts a factual claim that is **contradicted by, or unsupported by**, the benchmark's validated evidence and source record. Missing information alone is not hallucination unless the model replaces it with an unsupported claim.

### 13.6 Agreement

- Report Cohen's kappa for binary hallucination labels on the double-annotated overlap.
- Keep adjudicated gold labels separate from raw annotator labels. Never overwrite raw labels.
- Store both. Report both.

---

## 14. Evaluation metrics

`src/eval/metrics.py` computes, per (model, condition, domain, language):

| Metric | Definition | Role |
|--------|-----------|------|
| Hallucination Rate | Fraction of responses with `hallucination=yes` | Primary outcome |
| Answer Accuracy | Fraction `correct`, with `partially_correct` weighted 0.5 | Complementary |
| Unsupported Claim Rate | Fraction with any H2/H3 claim among partially correct | Claim-level |
| Coverage | Fraction with a substantive (non-abstention, non-refusal) answer | Mitigation trade-off |
| Selective Accuracy | Accuracy among answered/non-abstained cases | Mitigation quality |
| Retrieval Recall@k | Fraction of items where gold evidence retrieved | RAG diagnosis |
| Error-type distribution | Counts of H1–H5, A, R by domain/register | Diagnostic |
| Abstention Rate | Fraction with `abstention_status != none` | Diagnostic |
| Unnecessary Refusal Rate | Fraction with `error_type=R` | Diagnostic |

All proportions reported with 95% bootstrap confidence intervals (≥1000 resamples, stratified by item).

### 14.1 Joining annotations

- Use adjudicated labels where available.
- Otherwise use primary annotator labels.
- For overlap items without adjudication, use primary and log the disagreement.
- Never mix raw and adjudicated labels silently.

---

## 15. Statistical analysis

`src/eval/stats.py`:

1. **Paired comparisons** — same item across register and evidence conditions.
   - Standard Bangla vs. Banglish within model/condition: McNemar's test.
   - C0 vs. C1, C1 vs. C2, C2 vs. C3: McNemar's test.

2. **Primary model** — mixed-effects logistic regression:

   ```
   hallucination ~ register + domain + evidence_condition + model
                   + register:evidence_condition
                   + domain:evidence_condition
                   + (1 | item)
   ```

   - Pre-specify this small set of interactions. Do not fish.
   - `item` is a random intercept.

3. **Multiple comparisons** — Benjamini–Hochberg correction for planned secondary pairwise tests only.

4. **Reporting** — effect sizes and confidence intervals, not only p-values.

`src/eval/report.py` produces:

- `outputs/reports/metrics.csv`
- `outputs/reports/tables/*.tex`
- `outputs/reports/plots/*.png`
- `outputs/reports/summary.md` with RQ-aligned findings

---

## 16. Reproducibility

Every experiment stores:

- Dataset version (hash of `items.jsonl` + `evidence.jsonl`)
- Prompt hash (per template and per rendered prompt)
- Model version and API/model date
- Retrieval index version
- Configuration hash
- Timestamp
- Raw generations
- Retrieval logs with ranked passage IDs
- Annotation records (raw and adjudicated)

### 16.1 Lock files

After freeze, write under `outputs/{run_id}/`:

- `CONFIG_LOCK.json` — hash of configs, prompt templates, model versions, split file
- `PROMPT_LOCK.json` — hash of each prompt template
- `MODEL_LOCK.json` — model IDs and versions

Any change after lock requires a new `run_id`.

### 16.2 Publication

- Release annotation codebook and inter-annotator agreement statistics.
- Publish benchmark and code when source licensing permits; otherwise release IDs/scripts and a reproducible reconstruction process.

---

## 17. Testing

`pytest` must cover:

| Test file | What it checks |
|-----------|---------------|
| `test_schema.py` | Valid/invalid items, evidence, generations, annotations; `extra="forbid"` enforced |
| `test_validate_data.py` | Duplicate IDs, missing evidence, orphan evidence, wrong split ratio, near-duplicate flags |
| `test_prompts.py` | Each template renders without missing placeholders; language switch correct; abstention phrase exact |
| `test_runner.py` | Resume skips existing; `generation_id` deterministic; freeze guard blocks test split; cache key stable |
| `test_rag.py` | Chunking stable; `recall_at_k` computed correctly; C2/C3 reuse same context |
| `test_metrics.py` | Hallucination rate, coverage, selective accuracy on synthetic labels |

Use dummy data in `data/dummy/`. Tests must pass without network access or GPU.

---

## 18. Ethics and safety

Because the benchmark includes medical and legal domains:

- No patient-specific medical cases.
- No personal legal advice generation.
- Dataset items are factual evaluation tasks only.
- Outputs are research artifacts, not professional advice.
- Native-speaker annotators are credited; annotation is compensated work.
- Do not release source text from restricted corpora; release IDs and reconstruction scripts when licensing forbids redistribution.

---

## 19. Setup and environment

### 19.1 `.env.example`

```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
HF_TOKEN=
```

### 19.2 Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.validate_data --items data/dummy/items.jsonl --evidence data/dummy/evidence.jsonl
python -m src.runner.run --config configs/experiments.yaml --split dev --limit 5
```

### 19.3 Docker

- Base image: `python:3.11-slim`
- Install system deps for FAISS and tokenizers.
- Copy repo, install requirements, entrypoint to shell.
- GPU support optional via `nvidia/cuda` base and `--gpus all`. Default CPU-only.

---

## 20. Milestones and build order

| Day | Deliverable | Acceptance |
|-----|-------------|-----------|
| 1 | Schemas + dummy data + repo scaffold | `pytest tests/test_schema.py` passes |
| 2 | `validate_data.py` + `make_splits.py` | Validates dummy data; clear errors on malformed input |
| 3 | `DummyAdapter` + `LiteLLMAdapter` + prompt builder | C0/C1 run on dummy items; `generations.jsonl` written |
| 4 | Runner CLI with resume, cache, freeze guard | Rerun produces no duplicates; test split blocked |
| 5 | RAG: chunk, embed, index, retrieve | `recall_at_k` logged; C2/C3 use same context |
| 6 | Streamlit dashboard | Launch run, view generations, export |
| 7 | Annotation UI + sampling script | Annotate 10 dummy responses; JSONL written |
| 8 | Metrics + stats + report | `metrics.csv` and summary on dummy annotations |
| 9 | Docker + docs + full test suite | Full pipeline runs in container on dummy data |
| 10 | Real-data dry run | Swap dummy for real JSONL; pipeline runs unchanged |

---

## 21. Definition of done

The system is complete when:

1. `validate_data.py` accepts a correctly formed benchmark and rejects malformed input with actionable errors.
2. A single command runs C0–C3 across all configured models on the dev split, writing valid `generations.jsonl` and `retrieval_logs.jsonl`.
3. The runner is resumable, cached, and refuses to run the frozen test split without explicit unlock.
4. The annotation UI writes valid `annotations.jsonl`, supports overlap and adjudication, and hides model identity.
5. `metrics.py` and `stats.py` produce `metrics.csv`, LaTeX tables, and a summary aligned with RQ1–RQ4.
6. All tests pass without network or GPU.
7. The full pipeline runs on dummy data in Docker.
8. `DECISIONS.md` records every place the agent chose an option not specified here.
9. Real benchmark data replaces dummy data without modifying the pipeline.

---

## Appendix A — Example JSONL lines

### A.1 `items.jsonl`

```json
{"item_id":"gen_0001","domain":"general","question_bn":"বাংলাদেশের জাতীয় ফুল কোনটি?","question_banglish":"Bangladesh er jatiyo phul konti?","gold_answer":"শাপলা","evidence_id":"ev_gen_0001","answer_type":"entity","risk_tag":"normal","split":"dev","group_key":null}
```

### A.2 `evidence.jsonl`

```json
{"evidence_id":"ev_gen_0001","text":"বাংলাদেশের জাতীয় ফুল শাপলা।","source_url_or_id":"https://example.gov.bd/national-symbols","source_date":"2026-01-15","domain":"general"}
```

### A.3 `generations.jsonl`

```json
{"run_id":"main_v1","generation_id":"a1b2c3d4e5f60718","item_id":"gen_0001","language":"bn","condition":"C1","model_id":"dummy","model_version":"dummy-1.0","prompt":"...","prompt_hash":"...","response":"শাপলা","retrieved_evidence_ids":[],"temperature":0.0,"seed":42,"max_tokens":512,"timestamp":"2026-09-25T10:00:00Z","latency_ms":12,"error":null}
```

### A.4 `retrieval_logs.jsonl`

```json
{"run_id":"main_v1","item_id":"gen_0001","language":"bn","query":"বাংলাদেশের জাতীয় ফুল কোনটি?","top_k":5,"retrieved":[{"rank":1,"passage_id":"ev_gen_0001::0","evidence_id":"ev_gen_0001","score":0.91,"text":"বাংলাদেশের জাতীয় ফুল শাপলা।"}],"gold_evidence_id":"ev_gen_0001","gold_retrieved":true,"recall_at_k":1.0,"index_version":"idx_v1"}
```

### A.5 `annotations.jsonl`

```json
{"generation_id":"a1b2c3d4e5f60718","annotator_id":"a1","correctness":"correct","hallucination":"no","error_type":"none","abstention_status":"none","notes":"","timestamp":"2026-09-25T12:00:00Z","is_overlap":false}
```

### A.6 `adjudications.jsonl`

```json
{"generation_id":"a1b2c3d4e5f60718","adjudicator_id":"adj1","final_correctness":"correct","final_hallucination":"no","final_error_type":"none","rationale":"Directly supported by evidence.","timestamp":"2026-09-25T13:00:00Z"}
```

---

## Appendix B — Glossary

| Term | Meaning |
|------|---------|
| Base question | A single factual question with one evidence passage and one gold answer |
| Prompt variant | A language realization of a base question (`bn` or `banglish`) |
| Matched prompts | The `bn` and `banglish` variants of the same base question |
| Condition | One of C0, C1, C2, C3 |
| Register | Standard Bangla vs. Banglish |
| Gold evidence | The evidence passage associated with the base question |
| Oracle evidence | Condition C1, where gold evidence is given directly |
| Realistic RAG | Condition C2, where top-k retrieved passages are given |
| Abstention | Model declines to answer due to insufficient evidence |
| Coverage | Fraction of questions with a substantive answer |
| Selective accuracy | Accuracy among answered/non-abstained cases |
| IAA | Inter-annotator agreement |
| Frozen | Locked by hash; changes require a new `run_id` |

---

## Appendix C — Open decisions for the agent

Record a decision in `DECISIONS.md` for each of these if not already specified. Defaults in parentheses.

1. Template layout: two files per condition vs. language switch inside builder. (Default: two files.)
2. Abstention detection rule: normalized exact match vs. regex. (Default: normalized exact match; warn if extra content.)
3. API retry policy: attempts and backoff. (Default: 3 attempts, exponential backoff starting at 2s.)
4. Overlap stratification keys. (Default: domain × condition × model category.)
5. Annotation storage: JSONL only vs. JSONL + SQLite mirror. (Default: JSONL primary, SQLite mirror for fast queries.)
6. Embedding batch size and FAISS index type. (Default: batch 32, `IndexFlatIP`.)
7. Whether to expose raw annotator labels in the dashboard. (Default: no; adjudicated only.)
8. Docker GPU base image. (Default: CPU-only; document GPU override.)
9. Near-duplicate threshold. (Default: Jaccard > 0.85 on `question_bn`.)
10. Optional fifth model. (Default: none unless budget allows.)
11. Handling of API responses that include the abstention phrase plus extra content. (Default: treat as non-abstention and log a warning.)
12. Prompt template language for the wrapper when annotators are bilingual. (Default: match the question language.)

---

*End of specification. Every deviation must be recorded in `DECISIONS.md`.*
