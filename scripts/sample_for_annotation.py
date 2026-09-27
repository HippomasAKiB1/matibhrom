"""
Select which generations get annotated, per README §3.5 / §14.5.

Applies the configured annotation scope (configs/annotation.yaml: scope A/B/C)
and produces:

- outputs/{run_id}/annotation_plan/primary.jsonl      generation_ids for primary (single) annotation
- outputs/{run_id}/annotation_plan/overlap.jsonl       generation_ids sampled for a second annotator
- outputs/{run_id}/annotation_plan/pilot.jsonl         first `pilot_size` generation_ids, for the
                                                        kappa pilot before full annotation begins

Overlap is stratified by (domain x condition x model category) at
`overlap_fraction` (default 0.25), per §14.5.

Usage:
    python scripts/sample_for_annotation.py --run-id main_v1 --config configs/annotation.yaml
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from src.validate_data import load_jsonl


def model_category(model_id: str) -> str:
    """Coarse model family bucket used for overlap stratification."""
    lowered = model_id.lower()
    if "gpt" in lowered or "claude" in lowered or "gemini" in lowered:
        return "closed_api"
    if "dummy" in lowered:
        return "dummy"
    return "open_weights"


def select_scope_a(
    generations: list[dict],
    stratified_max: int = 6000,
    seed: int = 42,
) -> list[dict]:
    """Option A (README §3.5, recommended): a stratified subsample of at most
    `stratified_max` generations covering every (model x condition x domain x
    register) cell, rather than annotating every generation."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for g in generations:
        key = (g["model_id"], g["condition"], g.get("domain", "unknown"), g["language"])
        cells[key].append(g)

    if len(generations) <= stratified_max:
        return list(generations)

    rng = random.Random(seed)
    per_cell_quota = max(1, stratified_max // max(1, len(cells)))

    selected = []
    for key, items in cells.items():
        items_sorted = sorted(items, key=lambda g: g["generation_id"])  # deterministic order
        rng.shuffle(items_sorted)
        selected.extend(items_sorted[:per_cell_quota])

    return selected[:stratified_max]


def stratified_overlap(generations: list[dict], fraction: float, seed: int = 42) -> list[dict]:
    """Sample `fraction` of generations, stratified by
    (domain x condition x model_category), for a second annotator."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for g in generations:
        key = (g.get("domain", "unknown"), g["condition"], model_category(g["model_id"]))
        cells[key].append(g)

    rng = random.Random(seed)
    selected = []
    for key, items in cells.items():
        items_sorted = sorted(items, key=lambda g: g["generation_id"])
        rng.shuffle(items_sorted)
        n = max(1, round(len(items_sorted) * fraction))
        selected.extend(items_sorted[:n])
    return selected


def write_plan(generations: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for g in generations:
            f.write(json.dumps({"generation_id": g["generation_id"]}, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Select generations for annotation per the configured scope")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--config", default="configs/annotation.yaml")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        ann_config = yaml.safe_load(f)

    scope = ann_config.get("scope", "A")
    overlap_fraction = ann_config.get("overlap_fraction", 0.25)
    pilot_size = ann_config.get("pilot_size", 120)

    run_dir = Path(args.output_dir) / args.run_id
    generations_path = run_dir / "generations" / "generations.jsonl"
    if not generations_path.exists():
        print(f"No generations found at {generations_path}", file=sys.stderr)
        sys.exit(1)

    generations = load_jsonl(generations_path)

    if scope == "A":
        primary = select_scope_a(generations, seed=args.seed)
    elif scope in ("B", "C"):
        raise NotImplementedError(
            f"Annotation scope '{scope}' is not yet implemented (only Option A, the "
            f"recommended default, is implemented). See README §3.5 for scope B/C definitions."
        )
    else:
        raise ValueError(f"Unknown annotation scope: {scope!r}")

    overlap = stratified_overlap(primary, overlap_fraction, seed=args.seed)

    primary_sorted = sorted(primary, key=lambda g: g["generation_id"])
    pilot = primary_sorted[:pilot_size]

    plan_dir = run_dir / "annotation_plan"
    write_plan(primary, plan_dir / "primary.jsonl")
    write_plan(overlap, plan_dir / "overlap.jsonl")
    write_plan(pilot, plan_dir / "pilot.jsonl")

    print(f"Scope: {scope}")
    print(f"Primary annotation set: {len(primary)} generations (of {len(generations)} total)")
    print(f"Overlap set (second annotator, ~{overlap_fraction:.0%}): {len(overlap)} generations")
    print(f"Pilot set (first {pilot_size}, for kappa check before full annotation): {len(pilot)} generations")
    print(f"Wrote plan files to {plan_dir}")


if __name__ == "__main__":
    main()
