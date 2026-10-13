"""
Compute Inter-Annotator Agreement (IAA) and Cohen's Kappa (§14.5).

Evaluates agreement across:
- hallucination (binary: yes vs no)
- correctness (3-class: correct, partially_correct, incorrect)
- error_type (categorical)
- abstention_status (categorical)

Supports pilot gate (--pilot): enforces kappa >= threshold (default 0.70 from
configs/annotation.yaml) before main-phase annotation commences.
"""

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml
from sklearn.metrics import cohen_kappa_score

# Add repo root to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.validate_data import load_jsonl


def compute_pairwise_iaa(annotations: list[dict]) -> dict[str, Any]:
    """Compute pairwise Cohen's kappa and observed agreement across overlap generations."""
    by_gen: dict[str, dict[str, dict]] = defaultdict(dict)
    for ann in annotations:
        gid = ann["generation_id"]
        annotator = ann["annotator_id"]
        by_gen[gid][annotator] = ann

    pairs_data: dict[str, dict[str, list[str]]] = {
        "hallucination": {"r1": [], "r2": []},
        "correctness": {"r1": [], "r2": []},
        "error_type": {"r1": [], "r2": []},
        "abstention_status": {"r1": [], "r2": []},
    }

    overlap_count = 0
    for gid, annotators in by_gen.items():
        if len(annotators) < 2:
            continue
        # Extract all distinct pairs for this generation
        for r1, r2 in combinations(sorted(annotators.keys()), 2):
            overlap_count += 1
            ann1 = annotators[r1]
            ann2 = annotators[r2]
            for metric in pairs_data:
                v1 = str(ann1.get(metric, "")).strip().lower()
                v2 = str(ann2.get(metric, "")).strip().lower()
                pairs_data[metric]["r1"].append(v1)
                pairs_data[metric]["r2"].append(v2)

    results: dict[str, Any] = {
        "num_overlap_pairs": overlap_count,
        "metrics": {},
    }

    if overlap_count == 0:
        return results

    for metric, vals in pairs_data.items():
        r1 = vals["r1"]
        r2 = vals["r2"]
        n = len(r1)
        if n == 0:
            continue

        # Observed agreement
        agreed = sum(1 for a, b in zip(r1, r2) if a == b)
        po = agreed / n

        # Cohen's Kappa via scikit-learn
        try:
            # If all ratings are identical across all items and raters, kappa is 1.0
            if len(set(r1)) == 1 and len(set(r2)) == 1 and r1[0] == r2[0]:
                kappa = 1.0
            else:
                kappa = float(cohen_kappa_score(r1, r2))
                if np_isnan(kappa):
                    kappa = 0.0
        except Exception:
            kappa = 0.0

        results["metrics"][metric] = {
            "n": n,
            "observed_agreement": round(po, 4),
            "cohens_kappa": round(kappa, 4),
        }

    return results


def np_isnan(val: float) -> bool:
    import math
    return math.isnan(val)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Cohen's kappa IAA (§14.5)")
    parser.add_argument("--run-id", help="Benchmark run ID")
    parser.add_argument("--annotations", help="Direct path to annotations JSONL")
    parser.add_argument("--output-dir", default="outputs", help="Base output directory")
    parser.add_argument("--config", default="configs/annotation.yaml", help="Path to annotation config")
    parser.add_argument("--threshold", type=float, help="Override kappa threshold (default from config)")
    parser.add_argument("--pilot", action="store_true", help="Enforce pilot gate threshold (§14.5)")
    parser.add_argument("--json-out", help="Optional path to write results JSON")
    args = parser.parse_args()

    # Determine annotations path
    ann_path = None
    if args.annotations:
        ann_path = Path(args.annotations)
    elif args.run_id:
        ann_path = Path(args.output_dir) / args.run_id / "annotations" / "annotations.jsonl"
    else:
        parser.error("Must provide either --annotations or --run-id")

    if not ann_path.exists():
        print(f"Error: annotations file not found at {ann_path}")
        sys.exit(1)

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    threshold = args.threshold if args.threshold is not None else float(config.get("kappa_threshold", 0.70))

    annotations = load_jsonl(ann_path)
    iaa_results = compute_pairwise_iaa(annotations)

    print("=" * 60)
    print("MATIBHROM INTER-ANNOTATOR AGREEMENT (IAA) REPORT")
    print("=" * 60)
    print(f"Source file:           {ann_path}")
    print(f"Total annotations:     {len(annotations)}")
    print(f"Overlap pairs:         {iaa_results['num_overlap_pairs']}")
    print(f"Target kappa threshold:{threshold:.2f}")
    print("-" * 60)
    print(f"{'Metric':<20} {'Agreement (Po)':<16} {'Cohen Kappa (k)':<16}")
    print("-" * 60)

    for metric, stats in iaa_results["metrics"].items():
        po_str = f"{stats['observed_agreement']:.2%}"
        kappa_str = f"{stats['cohens_kappa']:.4f}"
        print(f"{metric:<20} {po_str:<16} {kappa_str:<16}")

    print("=" * 60)

    if args.json_out:
        out_file = Path(args.json_out)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(iaa_results, f, indent=2)
        print(f"Wrote JSON results to {out_file}")

    if args.pilot:
        print("\n--- PILOT GATE EVALUATION (§14.5) ---")
        metrics = iaa_results.get("metrics", {})
        k_hallucination = metrics.get("hallucination", {}).get("cohens_kappa", 0.0)
        k_correctness = metrics.get("correctness", {}).get("cohens_kappa", 0.0)

        passed = (k_hallucination >= threshold) and (k_correctness >= threshold)
        if passed:
            print(f"[PILOT GATE PASSED] Hallucination k={k_hallucination:.4f} >= {threshold:.2f}, Correctness k={k_correctness:.4f} >= {threshold:.2f}.")
            print("Ready to proceed to full annotation.")
            sys.exit(0)
        else:
            print(f"[PILOT GATE FAILED] Agreement below threshold {threshold:.2f}:")
            if k_hallucination < threshold:
                print(f"  - Hallucination kappa: {k_hallucination:.4f} < {threshold:.2f}")
            if k_correctness < threshold:
                print(f"  - Correctness kappa:   {k_correctness:.4f} < {threshold:.2f}")
            print("Action required: Annotators must resolve codebook ambiguities and retrain before main-phase run.")
            sys.exit(1)


if __name__ == "__main__":
    main()
