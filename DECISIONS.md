# Agent Decisions Log

This file records the decisions made by the AI agent during the implementation of the Matibhrom project. Each decision should include the choice, alternatives considered, and the reason for the choice.

## Day 1 - Core Infrastructure

### 1. Schema Validation

**Choice:** Use Pydantic v2 with `extra="forbid"` on all models

**Alternatives considered:**
- Pydantic v1 (legacy)
- Marshmallow
- JSON Schema + custom validation

**Reason:** Pydantic v2 is the current standard, provides strong type validation, integrates well with Python, and the spec explicitly requires Pydantic v2 with `extra="forbid"`.

### 2. Atomic File Writes

**Choice:** Use fcntl.flock with background writer threads

**Alternatives considered:**
- Atomic writes with tmp files
- Database-backed writes
- Lock-free write algorithms

**Reason:** The spec explicitly requires `fcntl.flock` and a single writer thread per file for atomic appends. This ensures consistency even after crashes.

### 3. Cache Design

**Choice:** SQLite with WAL mode, version-aware invalidation

**Alternatives considered:**
- Redis-backed cache
- In-memory cache with disk backup
- File-based cache

**Reason:** SQLite is simple, persistent, cross-platform, and the spec explicitly requires SQLite WAL mode with version checking for schema/model invalidation.

### 4. Lock Design

**Choice:** Atomic O_EXCL lock files with timeout

**Alternatives considered:**
- Flocks on file descriptors
- Advisory locks with netfile
- Centralized lock server

**Reason:** The spec requires `os.open(path, O_CREAT | O_EXCL | O_WRONLY)` atomic creation for lock files.

### 5. Scoring System

**Choice:** Exact match scoring (0-100% based on token overlap)

**Alternatives considered:**
- BLEU score
- ROUGE score
- Custom semantic similarity

**Reason:** The spec requires exact match scoring based on token overlap, which is simpler and more deterministic for factual questions.

### 6. Annotation Scope

**Choice:** Option A: Reduced factorial + LLM pre-labeling

**Alternatives considered:**
- Option B: Full annotation of reduced design
- Option C: Full annotation with external annotators

**Reason:** Option A balances budget, speed, and quality. LLM pre-labeling provides 80% coverage with human verification on 20% stratified, plus 100% verification for medical/legal cases. Target of ≤ 6,000 human labels matches budget constraints.

### 7. Distractor Corpus

**Choice:** At least 1,000 distractor passages, one per gold passage per domain

**Alternatives considered:**
- Fixed number of distractors (e.g., 1,000 total)
- One distractor per gold passage but not per domain
- No strict requirement

**Reason:** The spec explicitly requires at least 1,000 distractor passages AND at least 1 distractor per gold passage per domain to ensure meaningful retrieval evaluation.

## Day 2 - Model Adapters

### 1. Model Adapter Architecture

**Choice:** Abstract base class with concrete implementations

**Alternatives considered:**
- Direct instantiation per model
- Plugin system
- Factory pattern with registry

**Reason:** Abstract base class provides clear interface, allows easy addition of new adapters, and matches the spec's interface requirements.

### 2. Adapter Selection

**Choice:** Dynamic loading via adapter registry

**Alternatives considered:**
- Command-line flag for adapter
- Configuration-based selection
- Hard-coded per model

**Reason:** Dynamic registry allows flexible configuration and matches the spec's requirement for adapter selection based on configs/models.yaml.

### 3. Token Counting

**Choice:** Whitespace splitting for dummy adapter, API counts for LiteLLM

**Alternatives considered:**
- tiktoken for exact counts
- Approximate neural count
n- No token counting

**Reason:** Whitespace splitting is simple and deterministic for the dummy adapter. For LiteLLM, use actual API counts as they're more accurate and the spec requires recording prompt/response tokens.

## Day 3 - Runner Core

### 1. Generation Loop

**Choice:** Four nested loops (items × languages × conditions × models)

**Alternatives considered:**
- Parallelize over models only
- Batch generation within models
- Dynamic scheduling

**Reason:** Simple nested loops are easiest to reason about, match the spec's requirements, and allow clear control over each dimension.

### 2. Caching Strategy

**Choice:** Cache per (prompt, model, temperature, max_tokens, seed)

**Alternatives considered:**
- Cache per (item, condition, model)
- Cache per (question, model)
- No caching

**Reason:** The spec explicitly requires cache key based on prompt hash + model params, which is exactly what this implements.

### 3. Concurrency

**Choice:** Thread pool per model, global rate limiting

**Alternatives considered:**
- Process pool
- Async/await
- No concurrency

**Reason:** The spec requires rate limiting per API provider, which is easier to implement with threads. Also matches the `--workers` flag requirement.

## Day 4 - RAG Module

### 1. Embedding Model

**Choice:** BAAI/bge-m3 as default

**Alternatives considered:**
- All available embedding models
- Model selection per config
- No default (always require config)

**Reason:** BAAI/bge-m3 is the spec's default embedding model.

### 2. Index Type

**Choice:** FAISS IndexFlatIP (inner product)

**Alternatives considered:**
- HNSW
- IVF
- Annoy

**Reason:** IndexFlatIP is simple, exact, and the spec explicitly requires FAISS with inner product for cosine similarity.

### 3. Chunks vs Passages

**Choice:** Chunk long passages, keep short passages intact

**Alternatives considered:**
- Always chunk
- Never chunk
- Hybrid with fixed size

**Reason:** The spec requires token-based chunking for long passages while single-chunk passages keep their original passage_id.

## Day 5 - Annotation System

### 1. Annotation UI

**Choice:** Streamlit with auth

**Alternatives considered:**
- Jupyter notebook
- Flask/Django
- Static web page

**Reason:** Streamlit is the spec's default choice, it's simple to deploy, and matches the existing technology stack.

### 2. Token-based Auth

**Choice:** Token file with mapping to annotator_id

**Alternatives considered:**
- OAuth
- API keys
- No auth

**Reason:** The spec explicitly requires token-based auth with `configs/annotation_tokens.json` (gitignored) and requires auth by default.

### 3. Pre-labeling Strategy

**Choice:** LLM pre-labeling with 20% human verification stratified

**Alternatives considered:**
- 100% human verification
- 50% human verification
- No pre-labeling

**Reason:** The spec's Option A requires stratified 20% human verification of LLM pre-labels plus 100% verification for medical/legal cases.

## Day 6 - Evaluation

### 1. Metrics

**Choice:** Primary metrics as specified in §15

**Alternatives considered:**
- Custom metrics
- ROUGE/BERTScore
- Only hallucination rate

**Reason:** The spec explicitly lists the required metrics: Hallucination Rate, Answer Accuracy, Unsupported Claim Rate, Coverage, Selective Accuracy, Retrieval Recall@k, Error-type distribution, Abstention Rate, Unnecessary Refusal Rate, Tier-2 Abstention Rate.

### 2. Statistical Analysis

**Choice:** McNemar tests + mixed-effects logistic regression with fallback

**Alternatives considered:**
- Only p-values
- Bayesian statistics
- No statistics

**Reason:** The spec requires McNemar tests for paired comparisons and mixed-effects regression with a fallback path for non-converging models.

## Day 7 - Testing

### 1. Test Strategy

**Choice:** Unit tests for all core modules + integration tests

**Alternatives considered:**
- Only integration tests
- Only unit tests
- Property-based tests

**Reason:** The spec requires comprehensive test coverage with specific test files for each major component.

### 2. CI Configuration

**Choice:** GitHub Actions with CPU-only and optional GPU jobs

**Alternatives considered:**
- Jenkins
- GitHub-hosted runners only
- Local only

**Reason:** Matches the spec's CI requirements and allows optional GPU testing on self-hosted runners.

## Day 8 - Documentation

### 1. Decisions Document

**Choice:** Maintain a log of all agent decisions

**Alternatives considered:**
- Commit messages only
- Pull request descriptions
- Wiki pages

**Reason:** The spec requires `DECISIONS.md` to record decisions for transparency and auditability.

### 2. Budget Tracking

**Choice:** Detailed cost estimates with per-million-token pricing

**Alternatives considered:**
- Flat fee
- Usage-based with hard caps
- No budget tracking

**Reason:** The spec requires budget estimates, hard caps, and per-million-token pricing updates before each run.

## Open Decisions (for future)

The following decisions are left open and must be resolved before the main run:

1. **Template layout:** Two files per condition vs. language switch (default: two files)
2. **Abstention tier-2 threshold:** Default: 0.80 normalized edit similarity
3. **API retry policy:** Default: 3 attempts, exponential backoff starting at 2s
4. **Overlap stratification keys:** Default: domain × condition × model category
5. **Annotation storage:** Default: JSONL primary, SQLite mirror
6. **Embedding batch size, FAISS index type:** Default: batch 32, `IndexFlatIP`
7. **Whether to expose raw annotator labels in the dashboard:** Default: no; adjudicated only
8. **Docker GPU base image:** Default: `nvidia/cuda:12.4.0-runtime-ubuntu22.04`
9. **Near-duplicate threshold:** Default: Jaccard > 0.85 on `question_bn`
10. **Optional fifth model:** Default: none unless budget allows
11. **Handling of responses containing the abstention phrase plus extra content:** Default: non-abstention, warn
12. **Prompt template wrapper language:** Default: match the question language
13. **Answer Accuracy weighting for `partially_correct`:** Default: 0.5
14. **Whether to commit the frozen benchmark to the repository:** Default: yes if licensing permits; otherwise scripts only
15. **Distractor corpus sourcing strategy:** Default: same authoritative sources as gold, adjacent topics, one distractor per gold minimum
16. **Bitwise-reproducible subset size:** Default: 200 generations

**Note:** These open decisions will be finalized in future interactions or when implementing specific features.
---

## Bug-fix / completion pass (post-initial-implementation)

Recorded per document rule 2 ("where this document is silent... record the choice in DECISIONS.md") and rule 4 (resumable, atomic writes) since fixing these required interpreting the spec.

**Bugs fixed in existing code (not scope changes, correctness fixes):**

1. `src/runner/generate.py` imported `write_jsonl_atomic` from a nonexistent
   `src.runner.io_atomic` (the module lives at `src/io_atomic.py`). Fixed the import.
2. `src/io_atomic.py` used `threading.Queue` (not a real attribute — `Queue`
   lives in the `queue` module) and leaked a file descriptor per write via a
   throwaway `open(path, "a").fileno()`. Rewrote the module: proper `queue.Queue`
   usage, the per-file writer thread now holds its own open file handle and
   flocks around each write, and a deadlock introduced during the first fix
   attempt (a non-reentrant lock acquired twice on the same thread) was found
   and removed. Added `flush_writer()` for callers that need to block until
   pending writes land.
3. `src/prompts/builder.py`: building a C2/C3 prompt called `str.format()` in
   a way that raised `KeyError: 'abstention_phrase'` for C3, because
   `str.format` requires every placeholder in the template to be supplied in
   one call. Fixed by formatting C3 templates with `retrieved_context`,
   `question`, and `abstention_phrase` together.
4. `src/model_adapters/__init__.py` eagerly imported the `litellm`, `vllm`,
   and `hf` adapter modules at package-import time, so any code path that
   only needed the `dummy` adapter (tests, dry runs, CI) required
   `litellm`/`torch`/`vllm`/`transformers` to be installed. Adapter classes
   are now lazily imported on first use via `get_adapter_class`.
5. `src/runner/generate.py`'s `GenerationRunner.generate_all()` was an
   unfinished stub — it built prompts and cache keys but never called a model
   adapter, never constructed `Generation` objects for cache misses, and
   always returned `[]`. Implemented the real loop: resolve the adapter via
   the registry, call `.generate()`, build and validate a `Generation`,
   populate the cache, and use a per-`generation_id` lock file
   (`outputs/{run_id}/locks/{generation_id}.lock`) so a crashed/resumed run
   skips generations another process already claimed rather than duplicating
   API spend.
6. `tests/test_core_smoke.py` had an assertion checking for the literal
   words "অবশেষে"/"সত্য" in a C3 prompt — neither appears in the actual
   `abstention_phrase.txt` wording. Replaced with a check that the
   configured abstention phrase is present in the rendered prompt (the
   behavior the test was actually meant to verify).

**Scripts added** (referenced by `pyproject.toml` console scripts and the
README, but the `scripts/` directory was empty):

- `scripts/make_splits.py` — writes derived `data/splits/{dev,test}.jsonl`
  from the authoritative `split` field on each `Item`; also asserts the
  grouped-split invariant (§3.4) using `group_key` (falling back to
  `evidence_id`) so a future annotator/curator change can't silently split a
  document's items across dev and test.
- `scripts/check_budget.py` — projects run cost from item/language/condition
  counts and per-model average token estimates, then calls
  `src.budget.check_budget` against `configs/budget.yaml`'s `max_usd`.
  Token estimates are rough (§ open decision, not pre-registered) and are
  clearly labeled as such; real runs use actual per-call token counts.
- `scripts/build_index.py` — chunks the corpus (`src.rag.chunker`), embeds it
  (`src.rag.embedder`), builds and saves the FAISS index
  (`src.rag.index.Index`) under `outputs/{run_id}/retrieval/index/`, and
  writes `corpus_version`/`index_version`. Enforces `min_corpus_passages`
  from `configs/rag.yaml` before building, matching the §12.1 P0 fix. Not
  executed end-to-end in this pass — the sandbox used to build this couldn't
  install `faiss-cpu`/`sentence-transformers` (disk constraints) — reviewed
  for correctness against `src/rag/*` but should be smoke-tested against the
  real corpus before the main run.
- `scripts/export_tables.py` — joins `generations.jsonl` with
  `annotations.jsonl` (preferring human/verified labels over unverified LLM
  pre-labels for the same `generation_id`, per §14.6), attaches `domain` by
  joining back through `items.jsonl` (generations don't carry `domain`
  directly), and writes `metrics.csv`, `summary.md`, one primary LaTeX table,
  and `tokenization_report.md`. Per-domain plots (`reports/plots/*.png`) are
  not yet implemented — left as a follow-up.
- `scripts/sample_for_annotation.py` — implements annotation **Option A**
  from §3.5 (stratified subsample by model × condition × domain × register,
  capped at `stratified_max`) plus the §14.5 stratified overlap sample
  (domain × condition × model-category) and the pilot-set cut. Options B and
  C from §3.5 raise `NotImplementedError` rather than silently behaving like
  A — this should be revisited if the team decides scope A is insufficient.

**Verification performed:** ran the full existing test suite (now passing,
4/4, after the fixes above — previously it didn't even collect), and ran the
generation loop and all five new scripts end-to-end against `data/dummy/*`
plus a synthetic annotations file, confirming `generations.jsonl` validates
against the `Generation` schema, cache-based resumability produces the same
6 generations without re-invoking the adapter on a second call, and
`export_tables.py`'s domain/condition grouping produces correct (not
`"unknown"`) group keys.

**Still open / recommended next steps:**

- `src/annotation/` has no annotation UI or pre-labeling implementation yet
  (only an empty `__init__.py`) — §14.3 (Streamlit UI), §14.4 (token auth),
  and §14.6 (LLM pre-labeling) are unimplemented.
- `scripts/build_index.py` and the full `src/rag/*` retrieval path need a
  smoke test against a real (or larger dummy) corpus with the actual
  `faiss-cpu`/`sentence-transformers` dependencies installed — not exercised
  in this pass due to sandbox disk limits.
- `scripts/migrate_schema.py` mentioned in README §9.1 is intentionally not
  written yet ("not yet written; write on demand") — still true.
- `reports/plots/*.png` generation in `scripts/export_tables.py` is not
  implemented.

---

## Second pass: completing remaining §14 modules + one more critical bug

Continuing the earlier bug-fix/completion pass, to cover the rest of the
README's modules.

**Critical bug found and fixed:**

- `src/runner/cache.py`'s `GenerationCache.get()` selected columns
  `(key, generation_id, response, model_version, config_hash, timestamp)` —
  six columns — but then read `row[4]` expecting `schema_version` to check
  cache validity. Column index 4 in that select list is actually
  `config_hash`, not `schema_version` (which wasn't selected at all). Since
  `config_hash` is always `""` and `expected_schema` is always `"1.0.0"`,
  every single cache lookup compared `"" != "1.0.0"`, invalidated the entry,
  and returned `None` — meaning **the cache never actually returned a hit**.
  Every "resumed" run would have silently regenerated (and re-billed) every
  generation from scratch, defeating the entire cost-control and
  resumability design the spec repeatedly emphasizes. Fixed the SELECT to
  include `schema_version` in the right position and re-verified: a runner
  now returns identical results with `generated_count` unchanged on a
  second `generate_all()` call. This is covered by
  `tests/test_annotation_and_rag.py::test_cache_hit_skips_second_adapter_call`.

**Other correctness fixes in the core runner (§9.10, §12, retrieval logging):**

- `Generation.evidence_ids_used` was set to `[item.evidence_id]` for C1
  *and* C2 *and* C3, which violates the §9.10 table (`C2`/`C3` should be the
  deduplicated, order-preserving evidence_ids from retrieval, not the gold
  evidence_id). Fixed, with a regression test.
- **`RetrievalLog` records were never written anywhere** — `generate.py`
  called `retriever.retrieve(...)` but nothing constructed or persisted a
  `RetrievalLog`, silently breaking Recall@k diagnostics (§15) for every
  run. Rewrote the C2/C3 path to retrieve exactly once per (item, language)
  — memoized so C2 and C3 share byte-identical context (§8.10/§12) instead
  of hitting the retriever twice — and to emit one validated `RetrievalLog`
  per (item, language) via `write_jsonl_atomic`.
- `Retriever` never exposed `index_version`/`corpus_version` (`generate.py`
  always fell back to `""` via `getattr(..., "")`). Added properties that
  read them from the loaded FAISS index's metadata.

**New modules built to complete README §14 (annotation system):**

- `src/annotation/store.py` — `AnnotationStore`: JSONL-of-record +
  SQLite-mirror storage for `Annotation`/`Adjudication`, immediate save,
  mirror rebuild from JSONL on restart (so deleting/losing the `.db` file
  is never destructive), and an overlap-disagreement query used to drive
  the adjudication trigger (§14.5/§14.9).
- `src/annotation/auth.py` — token auth against
  `configs/annotation_tokens.json` (gitignored; added
  `configs/annotation_tokens.example.json` as a template), plus
  `assert_safe_to_disable_auth()` enforcing the §14.4 requirement that a
  UI running with `auth.enabled: false` must refuse to bind to a
  non-localhost address.
- `src/annotation/prelabel.py` — LLM pre-labeling (§14.6): prompts the
  configured `prelabel_model` for JSON labels, robustly extracts JSON from
  fenced/chatty model output, validates against the same label vocabulary
  as `Annotation`, writes `labeler_type="llm"` / `verified_by_human=false`
  records, and produces `annotation_plan/verify_required.jsonl` — a
  stratified 20% (`prelabel_verify_fraction`) plus 100% of medical/legal
  hallucination=yes cases, per spec.
- `src/annotation/app.py` — the Streamlit UI (§14.3): shows
  question/gold-answer/evidence(joined from `evidence.jsonl` by
  `item.evidence_id`)/response; hides model identity, condition, and domain
  behind an explicit "adjudication only" sidebar toggle; shows the LLM
  pre-label inline for accept/override; immediate save via
  `AnnotationStore`; randomized per-annotator order; progress counter;
  jump-to-generation-id; prev/next; an Enter-to-submit keyboard binding via
  `st.html(..., unsafe_allow_javascript=True)`; token login via
  `src.annotation.auth`. Verified end-to-end with Streamlit's
  `AppTest` (no exceptions, no deprecation warnings): login, form
  rendering, and a full submit-and-persist cycle were all exercised
  against real generations produced by the fixed runner.

**Other README items completed:**

- `scripts/export_tables.py` now also writes `reports/plots/*.png` (one bar
  chart per metric across the requested `--group-by` dimension), via
  matplotlib's non-interactive `Agg` backend. Verified the PNGs render
  correctly.
- `scripts/migrate_schema.py` (§9.1, previously "not yet written; write on
  demand") is now written: a `check` subcommand reporting the
  `schema_version` distribution in a JSONL file, and a `migrate`
  subcommand that walks a per-record-type `MIGRATIONS` registry
  (`from_version -> migrate_fn`) until every record reaches the current
  `SCHEMA_VERSION`, re-validating against the Pydantic model on the way
  out. No migrations are registered yet, correctly, since `SCHEMA_VERSION`
  has never been bumped past 1.0.0 — this is the harness, ready for the
  first bump.

**Verified but with a known, environment-imposed limit:** `src/rag/index.py`
(FAISS `IndexFlatIP` build/save/load/search) was exercised directly with
synthetic embeddings and round-trips correctly, including metadata
(`corpus_version`/`index_version`) persistence. `src/rag/chunker.py` and
`src/rag/embedder.py` could **not** be exercised even with disk space freed,
because both call `AutoTokenizer.from_pretrained("BAAI/bge-m3")` /
`SentenceTransformer(...)`, which need to reach huggingface.co — outside
this sandbox's allowed egress domains (pypi/npm/github/anthropic only, no
huggingface.co). `scripts/build_index.py` is therefore still unexercised
end-to-end; it should be smoke-tested in an environment with real network
access before the main run, though its logic was reviewed against
`src/rag/*`'s actual interfaces (`chunk_corpus`, `Embedder.encode`,
`Index.build/save`) and lines up correctly.

**Test coverage added:** `tests/test_annotation_and_rag.py` — 5 new tests
covering the §9.10 evidence_ids_used table end-to-end (via a fake
retriever), the cache-resumability bug above, LLM pre-label JSON
extraction, the annotation store's save/reload/disagreement-detection, and
auth accept/reject behavior. Full suite: 9/9 passing.

### Cross-Platform / Windows Portability for Atomic IO
**Choice:** Made `fcntl` optional in `src/io_atomic.py` by guarding `fcntl.flock` with a fallback check when run on Windows platforms where `fcntl` is not part of standard POSIX C runtime.
**Reason:** Allows tests and local runner executions to seamlessly run on Windows developer workstations without breaking Linux production behavior.

