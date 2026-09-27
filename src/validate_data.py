"""
Data validation for Matibhrom benchmark.

Exit non-zero on any error. Print a summary table.
All checks from §9.9.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.schema_version import SCHEMA_VERSION

from src.schema import Item, Evidence, CorpusPassage

ITEM_ID_RE = re.compile(r"^[a-z]+_\d{4}$")
NEAR_DUPLICATE_JACCARD_THRESHOLD = 0.85
DEFAULT_MIN_CORPUS_PASSAGES = 1000


def tokenize(text: str) -> set[str]:
    return set(text.strip().split())


def jaccard(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def validate_artifact(
    items_path: Path,
    evidence_path: Path,
    corpus_path: Path,
    min_corpus_passages: int = DEFAULT_MIN_CORPUS_PASSAGES,
) -> list[str]:
    errors: list[str] = []

    # --- load all records ---
    items_raw = load_jsonl(items_path)
    evidence_raw = load_jsonl(evidence_path)
    corpus_raw = load_jsonl(corpus_path)

    # --- schema_version checks ---
    for rec in items_raw:
        if rec.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"schema_version mismatch in {items_path.name} record {rec.get('item_id')}")
    for rec in evidence_raw:
        if rec.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"schema_version mismatch in {evidence_path.name} record {rec.get('evidence_id')}")
    for rec in corpus_raw:
        if rec.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"schema_version mismatch in {corpus_path.name} record {rec.get('passage_id')}")

    # --- Pydantic validation ---
    items: list[Item] = []
    for rec in items_raw:
        try:
            items.append(Item.model_validate(rec))
        except Exception as exc:
            errors.append(f"Invalid Item {rec.get('item_id')}: {exc}")

    evidences: list[Evidence] = []
    for rec in evidence_raw:
        try:
            evidences.append(Evidence.model_validate(rec))
        except Exception as exc:
            errors.append(f"Invalid Evidence {rec.get('evidence_id')}: {exc}")

    passages: list[CorpusPassage] = []
    for rec in corpus_raw:
        try:
            passages.append(CorpusPassage.model_validate(rec))
        except Exception as exc:
            errors.append(f"Invalid CorpusPassage {rec.get('passage_id')}: {exc}")

    # --- uniqueness checks ---
    item_ids = [i.item_id for i in items]
    if len(item_ids) != len(set(item_ids)):
        errors.append("Duplicate item_id found")

    ev_ids = [e.evidence_id for e in evidences]
    if len(ev_ids) != len(set(ev_ids)):
        errors.append("Duplicate evidence_id found")

    pass_ids = [p.passage_id for p in passages]
    if len(pass_ids) != len(set(pass_ids)):
        errors.append("Duplicate passage_id found")

    # --- item_id format ---
    for i in items:
        if not ITEM_ID_RE.match(i.item_id):
            errors.append(f"item_id '{i.item_id}' does not match ^[a-z]+_\\d{{4}}$")

    # --- non-empty questions ---
    for i in items:
        if not i.question_bn.strip():
            errors.append(f"item {i.item_id}: empty question_bn")
        if not i.question_banglish.strip():
            errors.append(f"item {i.item_id}: empty question_banglish")

    # --- evidence_id references ---
    ev_id_set = {e.evidence_id for e in evidences}
    for i in items:
        if i.evidence_id not in ev_id_set:
            errors.append(f"item {i.item_id}: evidence_id '{i.evidence_id}' not found")

    # --- no orphan evidence (not referenced by any item) ---
    item_ev_ids = {i.evidence_id for i in items}
    for e in evidences:
        if e.evidence_id not in item_ev_ids:
            errors.append(f"Orphan evidence {e.evidence_id}: not referenced by any item")

    # --- evidence text matches corpus passage ---
    pass_by_id = {p.passage_id: p for p in passages}
    for e in evidences:
        cp = pass_by_id.get(e.evidence_id)
        if cp is None:
            errors.append(f"Evidence {e.evidence_id}: not found in corpus")
        elif cp.text != e.text:
            errors.append(f"Evidence {e.evidence_id}: text mismatch with corpus passage")

    # --- split grouping ---
    split_by_key: dict[str, set[str]] = defaultdict(set)
    for i in items:
        key = i.group_key if i.group_key else i.evidence_id
        split_by_key[key].add(i.split)
    for key, splits in split_by_key.items():
        if len(splits) > 1:
            errors.append(f"group_key/evidence_id '{key}' appears in both dev and test")

    # --- exact duplicate questions in test ---
    test_questions: dict[str, str] = {}  # question_bn -> item_id
    for i in items:
        if i.split == "test":
            if i.question_bn in test_questions:
                errors.append(f"Duplicate question_bn in test: '{i.question_bn}' ({i.item_id}, {test_questions[i.question_bn]})")
            else:
                test_questions[i.question_bn] = i.item_id

    # --- near-duplicate check (flag only) ---
    test_items_list = [i for i in items if i.split == "test"]
    for a_idx in range(len(test_items_list)):
        for b_idx in range(a_idx + 1, len(test_items_list)):
            a = test_items_list[a_idx]
            b = test_items_list[b_idx]
            sim = jaccard(a.question_bn, b.question_bn)
            if sim > NEAR_DUPLICATE_JACCARD_THRESHOLD:
                errors.append(
                    f"Near-duplicate flag: '{a.question_bn[:40]}...' vs '{b.question_bn[:40]}...' "
                    f"(Jaccard={sim:.2f})"
                )

    # --- domain counts (200/200/200 for full benchmark; warn for dummy) ---
    domain_counts = defaultdict(lambda: defaultdict(int))
    for i in items:
        domain_counts[i.split][i.domain] += 1
    for split_name, counts in domain_counts.items():
        if split_name == "test" and len(items) == 600:
            for d in ("general", "medical", "legal"):
                if counts[d] != 200:
                    errors.append(f"Test split: expected 200 {d}, got {counts[d]}")

    # --- dev/test ratio ---
    base_items = set(i.item_id for i in items)
    n_dev = len([i for i in items if i.split == "dev"])
    n_test = len([i for i in items if i.split == "test"])
    if len(base_items) > 0:
        ratio = n_dev / (n_dev + n_test) if (n_dev + n_test) > 0 else 0
        if abs(ratio - 0.2) > 0.05:
            errors.append(f"Dev/test ratio {ratio:.2f} not close to 0.20")

    # --- risk_tag in medical/legal only ---
    for i in items:
        if i.risk_tag == "high-stakes" and i.domain not in ("medical", "legal"):
            errors.append(f"item {i.item_id}: high-stakes risk_tag in {i.domain} domain")

    # --- gold_answer length heuristic ---
    ev_map = {e.evidence_id: e for e in evidences}
    for i in items:
        ev = ev_map.get(i.evidence_id)
        if ev and len(i.gold_answer) > len(ev.text):
            errors.append(f"item {i.item_id}: gold_answer longer than evidence text (heuristic flag)")

    # --- corpus size ---
    if len(corpus_raw) < min_corpus_passages:
        errors.append(
            f"Corpus has {len(corpus_raw)} passages, minimum is {min_corpus_passages}"
        )

    # --- at least 1 distractor per gold passage per domain ---
    gold_by_domain = defaultdict(set)
    for i in items:
        gold_by_domain[i.domain].add(i.evidence_id)
    distractor_by_domain = defaultdict(int)
    for p in passages:
        if not p.is_gold_for:
            distractor_by_domain[p.domain] += 1
    for d, gold_ids in gold_by_domain.items():
        if distractor_by_domain.get(d, 0) < len(gold_ids):
            errors.append(
                f"Domain '{d}': {len(gold_ids)} gold passages but only "
                f"{distractor_by_domain.get(d, 0)} distractor(s)"
            )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Matibhrom benchmark data")
    parser.add_argument("--items", required=True, type=Path, help="Path to items.jsonl")
    parser.add_argument("--evidence", required=True, type=Path, help="Path to evidence.jsonl")
    parser.add_argument("--corpus", required=True, type=Path, help="Path to corpus.jsonl")
    parser.add_argument("--min-corpus", type=int, default=10, help="Minimum corpus passages (default 10 for dummy)")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings too")
    args = parser.parse_args()

    errors = validate_artifact(
        args.items,
        args.evidence,
        args.corpus,
        min_corpus_passages=args.min_corpus,
    )

    if errors:
        print("=" * 60)
        print(f"VALIDATION FAILED - {len(errors)} error(s)")
        print("=" * 60)
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("=" * 60)
        print("VALIDATION PASSED")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
