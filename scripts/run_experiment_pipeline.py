"""
Matibhrom End-to-End Experiment Pipeline CLI.

Executes:
  1. Generation runner (C0, C1, C2, C3 across models and languages)
  2. Sampling plan for human + LLM annotation (Scope A)
  3. Pre-labeling with local LLM (e.g. ollama/gemma3:4b)
  4. Metrics, paired statistical tests (McNemar), bootstrap CIs, LaTeX tables, and plots

Usage:
  python scripts/run_experiment_pipeline.py --run-id dev_ollama_v1 --split dev --limit 10
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_pipeline(
    run_id: str,
    split: str = "dev",
    conditions: str = "C0,C1,C2,C3",
    models: str = "ollama/qwen3:1.7b,ollama/gemma3:4b",
    limit: int | None = None,
    per_domain_limit: int | None = None,
    workers: int = 1,
    skip_generation: bool = False,
):
    print("=" * 70)
    print(f"MATIBHROM EXPERIMENT PIPELINE: {run_id} ({split.upper()} SPLIT)")
    print("=" * 70)

    # 1. Generation Runner
    if not skip_generation:
        print(f"\n[Step 1/4] Running generation (conditions={conditions}, models={models}, limit={limit}, per_domain_limit={per_domain_limit})...")
        cmd_run = [
            sys.executable,
            "-u",
            "-m",
            "src.runner.run",
            "--config", "configs/experiments.yaml",
            "--models", "configs/models.yaml",
            "--rag-config", "configs/rag.yaml",
            "--budget-config", "configs/budget.yaml",
            "--run-id", run_id,
            "--split", split,
            "--conditions", conditions,
            "--models-filter", models,
            "--items", "data/benchmark/items.jsonl",
            "--evidence", "data/benchmark/evidence.jsonl",
            "--corpus", "data/benchmark/corpus.jsonl",
            "--workers", str(workers),
            "--resume",
        ]
        if per_domain_limit:
            cmd_run.extend(["--per-domain-limit", str(per_domain_limit)])
        elif limit:
            cmd_run.extend(["--limit", str(limit)])
        if split == "test":
            cmd_run.append("--unlock-test")

        print("Executing:", " ".join(cmd_run))
        subprocess.run(cmd_run, check=True)
    else:
        print("\n[Step 1/4] Skipping generation (--skip-generation).")

    # 2. Annotation Sampling Plan (Scope A)
    print(f"\n[Step 2/4] Sampling annotation plan (Scope A)...")
    cmd_sample = [
        sys.executable,
        "-u",
        "scripts/sample_for_annotation.py",
        "--run-id", run_id,
    ]
    subprocess.run(cmd_sample, check=True)

    # 3. LLM Pre-labeling
    print(f"\n[Step 3/4] Running LLM pre-labeling with local model...")
    cmd_prelabel = [
        sys.executable,
        "-u",
        "-m",
        "src.annotation.prelabel",
        "--run-id", run_id,
        "--items", "data/benchmark/items.jsonl",
    ]
    subprocess.run(cmd_prelabel, check=True)

    # 4. Metrics & Reports Export
    print(f"\n[Step 4/4] Exporting metrics, bootstrap CIs, McNemar tests, LaTeX tables & plots...")
    cmd_export = [
        sys.executable,
        "-u",
        "scripts/export_tables.py",
        "--run-id", run_id,
        "--items", "data/benchmark/items.jsonl",
    ]
    subprocess.run(cmd_export, check=True)

    print("\n" + "=" * 70)
    print(f"PIPELINE COMPLETED SUCCESSFULLY FOR {run_id}")
    print(f"Reports available at: outputs/{run_id}/reports/")
    print(f"Generations file:     outputs/{run_id}/generations/generations.jsonl")
    print(f"Annotations file:     outputs/{run_id}/annotations/annotations.jsonl")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Matibhrom End-to-End Experiment Pipeline")
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    parser.add_argument("--split", default="dev", choices=["dev", "test"], help="Dataset split")
    parser.add_argument("--conditions", default="C0,C1,C2,C3", help="Comma-separated conditions")
    parser.add_argument("--models", default="ollama/qwen3:1.7b,ollama/gemma3:4b", help="Comma-separated model IDs")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items for pilot/quick testing")
    parser.add_argument("--per-domain-limit", type=int, default=None, help="Limit number of items per domain")
    parser.add_argument("--workers", type=int, default=1, help="Inference concurrency")
    parser.add_argument("--skip-generation", action="store_true", help="Skip generation if already complete")
    args = parser.parse_args()

    run_pipeline(
        run_id=args.run_id,
        split=args.split,
        conditions=args.conditions,
        models=args.models,
        limit=args.limit,
        per_domain_limit=args.per_domain_limit,
        workers=args.workers,
        skip_generation=args.skip_generation,
    )


if __name__ == "__main__":
    main()
