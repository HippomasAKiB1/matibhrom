# Budget and Cost Estimates

This document contains the budget estimates and cost projections for the Matibhrom project. All estimates are based on current pricing as of 2026-09-26.

## Overall Budget

**Total allocation:** $500 USD  
**GPU hours:** 100 hours  
**Storage:** 200 GB  

## Cost Breakdown by Component

### 1. Model Inference Costs

Based on the model configuration in `configs/models.yaml` and `configs/experiments.yaml`:

| Model | Provider | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Estimated Usage | Estimated Cost |
|-------|----------|---------------------------|----------------------------|-----------------|----------------|
| Qwen2.5-7B-Instruct | vLLM (local) | - | - | GPU-bound | - (local inference) |
| GPT-4o-2024-11-20 | OpenAI API | $2.50 | $10.00 | API calls | Variable (disabled by default) |

### 2. Estimate for Main Run (Test Split)

Assumptions:
- 480 test base items (80% of 600)
- 2 language variants per item (bn, banglish)
- 4 conditions (C0, C1, C2, C3)
- 2 models (dummy + qwen2.5-7b-instruct)
- Average 50 tokens per prompt
- Average 100 tokens per response

**Total generations:** 480 × 2 × 4 × 2 = 7,680  
**Total input tokens:** 7,680 × 50 = 384,000  
**Total output tokens:** 7,680 × 100 = 768,000

**Cost breakdown:**
- Qwen2.5-7B-Instruct (vLLM): GPU-bound, no direct API cost
- Dummy adapter: $0.00 (local, fixed response)
- OpenAI API (if enabled): (384,000/1,000,000 × $2.50) + (768,000/1,000,000 × $10.00) = $0.96 + $7.68 = $8.64

**Estimated total API cost:** < $10.00 (with only Qwen + dummy enabled)

### 3. Embedding Costs

- Embedding model: BAAI/bge-m3 (local, no API cost)
- Corpus passages: ~1,018 passages (6 gold + 17 dummy + distractor from corpus.jsonl)
- Embedding cost: Local computation, no API cost

### 4. Storage Costs

Estimated storage requirements:
- Generations: ~7,680 records × ~500 bytes = 3.8 MB
- Retrieval logs: ~7,680 records × ~200 bytes = 1.5 MB
- Annotations: ~6,000 records × ~500 bytes = 3.0 MB
- Cache: ~10,000 entries × ~1KB = 10 MB
- Index: FAISS index for ~1,018 vectors × 768 dim × 4 bytes = ~3.1 MB
- **Total estimated:** < 50 MB

### 5. Compute Costs

**CPU time (local processing):**
- Data validation: < 1 minute per run
- Prompt building: < 1 minute per run
- Generation (local vLLM): ~7,680 generations
  - Assuming 0.5 seconds per generation = ~64 minutes
  - With batching (batch size 8) = ~8 minutes
- Retrieval: ~7,680 queries
  - Assuming 0.1 seconds per query = ~12 minutes
- Annotation processing: ~6,000 annotations × 30 seconds = 300 minutes (5 hours)
- Report generation: < 10 minutes

**Total estimated CPU time:** < 8 hours

**GPU time (if using vLLM):**
- Depends on batch size and sequence length
- Estimated: < 10 hours for full run with batch size 8

### 6. Human Annotation Costs

Based on Option A (reduced factorial + LLM pre-labeling):

- **LLM pre-labeling:** ~12,288 generations (6,000 human + 6,288 LLM-only)
  - LLM cost: ~12,288 × (50+100) tokens × API rate
  - Assuming GPT-4o pre-labeling: ~$12.30
- **Human verification:** 6,000 labels
  - Stratified 20% verification: 1,200 labels
  - 100% medical/legal verification: ~800 additional labels (est.)
  - Total human labels: ~2,000
  - Time per label: 30 seconds
  - Total time: ~100 minutes
  - Cost at $15/hour: ~$25.00

**Estimated annotation cost:** < $40.00

## Total Estimated Cost

| Category | Estimated Cost |
|----------|----------------|
| Model API (Qwen + dummy) | $0.00 |
| Embedding (local) | $0.00 |
| LLM pre-labeling | $12.30 |
| Human annotation | $25.00 |
| Storage | < $1.00 |
| Compute (CPU) | < $5.00 |
| GPU (if used) | < $20.00 |
| **Total** | **< $63.30** |

## Budget Guard Thresholds

The runner will refuse to start if projected cost exceeds:

- **Maximum USD:** $500
- **Maximum GPU hours:** 100
- **Maximum disk GB:** 200

These are set in `configs/budget.yaml` and checked during pre-flight validation.

## Notes

1. All costs are estimates and subject to change based on actual usage.
2. Local model inference (vLLM, HF) has no direct API cost but consumes GPU/CPU resources.
3. API model costs vary based on actual token usage.
4. The budget guard uses projected costs based on estimated token counts.
5. Actual costs may vary based on:
   - Actual token lengths
   - Model efficiency
   - Network latency (for API models)
   - Retry attempts
   - Cache hit rates

## Updates

This budget should be updated before each major run to reflect:
- Actual model usage
- Current API pricing
- Updated corpus sizes
- Changed experimental scope

Last updated: 2026-09-26