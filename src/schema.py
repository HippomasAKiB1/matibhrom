"""
Pydantic v2 schemas for all Matibhrom data contracts.
Every model uses extra="forbid" — unknown fields are rejected, not silently dropped.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.schema_version import SCHEMA_VERSION, CODEBOOK_VERSION


def load_data(path: Path) -> list[dict]:
    """Load JSONL data from file, one dict per line."""
    data = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    item_id: str
    domain: Literal["general", "medical", "legal"]
    question_bn: str
    question_banglish: str
    gold_answer: str
    evidence_id: str
    answer_type: Literal["entity", "numeric", "short explanation", "procedure", "citation"]
    risk_tag: Literal["normal", "high-stakes"]
    split: Literal["dev", "test"]
    group_key: str | None = None


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    evidence_id: str
    text: str
    source_url_or_id: str
    source_date: str          # ISO 8601
    domain: Literal["general", "medical", "legal"]


class CorpusPassage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    passage_id: str
    text: str
    source_url_or_id: str
    source_date: str
    domain: Literal["general", "medical", "legal"]
    is_gold_for: list[str] = []


class Generation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    run_id: str
    generation_id: str
    item_id: str
    language: Literal["bn", "banglish"]
    condition: Literal["C0", "C1", "C2", "C3"]
    model_id: str
    model_version: str
    prompt: str
    prompt_hash: str
    prompt_tokens: int
    response: str
    response_tokens: int
    evidence_ids_used: list[str] = []
    temperature: float = 0.0
    seed: int | None = 42
    max_tokens: int = 512
    timestamp: str = ""
    latency_ms: int | None = None
    cost_usd: float | None = None
    truncated_input: bool = False
    error: str | None = None


class RetrievedPassage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    passage_id: str
    evidence_id: str
    score: float
    text: str


class RetrievalLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    run_id: str
    item_id: str
    language: Literal["bn", "banglish"]
    query: str
    query_hash: str
    top_k: int
    retrieved: list[RetrievedPassage] = []
    gold_evidence_id: str
    gold_retrieved: bool = False
    recall_at_k: float = 0.0
    index_version: str = ""
    corpus_version: str = ""


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    codebook_version: str = CODEBOOK_VERSION
    generation_id: str
    annotator_id: str
    labeler_type: Literal["human", "llm"] = "human"
    correctness: Literal["correct", "partially_correct", "incorrect"] | None = None
    hallucination: Literal["yes", "no"] | None = None
    error_type: Literal["H1", "H2", "H3", "H4", "H5", "A", "R", "none"] | None = None
    abstention_status: Literal["none", "appropriate", "unnecessary"] | None = None
    tier2_abstention_candidate: bool = False
    notes: str = ""
    timestamp: str = ""
    is_overlap: bool = False
    verified_by_human: bool = False


class Adjudication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    codebook_version: str = CODEBOOK_VERSION
    generation_id: str
    adjudicator_id: str
    final_correctness: Literal["correct", "partially_correct", "incorrect"] | None = None
    final_hallucination: Literal["yes", "no"] | None = None
    final_error_type: Literal["H1", "H2", "H3", "H4", "H5", "A", "R", "none"] | None = None
    rationale: str = ""
    timestamp: str = ""
