"""
Matibhrom experiment runner CLI.

Usage:
    python -m src.runner.run \
      --config configs/experiments.yaml \
      --models configs/models.yaml \
      --rag-config configs/rag.yaml \
      --budget-config configs/budget.yaml \
      --run-id main_v1 \
      --split test \
      --resume \
      --unlock-test
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from src.schema_version import SCHEMA_VERSION
from src.validate_data import validate_artifact
from src.hashing import hash_config, hash_model_version, hash_corpus, hash_template
from src.runner.cache import GenerationCache
from src.runner.locks import create_lock_atomic, LockError, write_lock_atomic, read_lock
from src.budget import check_budget, BudgetExceededError, load_pricing
from src.model_adapters import get_adapter_class
from src.prompts.builder import PromptBuilder
from src.rag.retriever import Retriever
from src.runner.generate import GenerationRunner
from src.runner.logging_utils import setup_logging, get_logger

logger = get_logger(__name__)


def load_models_config(path: str | Path) -> list[dict]:
    """Load models configuration."""
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("models", [])


def load_experiment_config(path: str | Path) -> dict:
    """Load experiment configuration."""
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def pre_flight_checks(
    items_path: Path,
    evidence_path: Path,
    corpus_path: Path,
    budget_config: Path,
    split: str,
    freeze_test: bool,
    unlocked: bool = False,
) -> None:
    """
    Run all pre-flight checks before generation starts.

    Raises:
        SystemExit: If any check fails
    """
    errors = []

    # 1. Validate inputs
    validation_errors = validate_artifact(items_path, evidence_path, corpus_path, min_corpus_passages=10)
    if validation_errors:
        errors.extend(validation_errors)

    # 2. Check corpus size
    import json
    corpus_raw = []
    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                corpus_raw.append(json.loads(line))
    if len(corpus_raw) < 1000 and split == "test":
        errors.append(f"Corpus has {len(corpus_raw)} passages, minimum is 1000 for test split")

    # 3. Check budget
    try:
        pricing = load_pricing(budget_config)
        # Estimate cost for the planned run
        projected_cost = 0.0  # Will be updated with actual token estimates
        check_budget(budget_config, projected_cost)
    except BudgetExceededError as e:
        errors.append(f"Budget exceeded: {e}")

    # 4. Check disk space
    disk_usage = os.statvfs(Path("outputs")) if hasattr(os, "statvfs") else None
    if disk_usage:
        free_pct = disk_usage.f_bavail / disk_usage.f_blocks * 100
        if free_pct < 20:
            errors.append(f"Disk space below 20%: {free_pct:.1f}% free")

    # 5. Check schema version (done by validate_data)

    # 6. Check model revisions
    models = load_models_config("configs/models.yaml")
    for model in models:
        if model.get("revision") == "main" and split == "test":
            errors.append(f"Model {model['id']} has revision 'main' - pin to SHA before test split")

    # 7. Check freeze guard
    if split == "test" and freeze_test and not unlocked:
        unlock_env = os.environ.get("MATIBHROM_UNLOCK_TEST", "0")
        if unlock_env != "1":
            errors.append(
                "Test split is frozen. Unlock with MATIBHROM_UNLOCK_TEST=1 --unlock-test"
            )

    if errors:
        print("=" * 60)
        print("PRE-FLIGHT CHECKS FAILED")
        print("=" * 60)
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


def create_locks(
    run_id: str,
    config_paths: list[str],
    prompt_dir: str | Path,
    models_config: list[dict],
    output_dir: str | Path,
) -> None:
    """Create lock files after freeze."""
    locks_dir = Path(output_dir) / run_id / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)

    # Config lock
    config_hash = hash_config(config_paths)
    write_lock_atomic(locks_dir / "CONFIG_LOCK.json", json.dumps({
        "hash": config_hash,
        "paths": config_paths
    }))

    # Prompt lock
    prompt_hashes = {}
    builder = PromptBuilder(prompt_dir)
    prompt_hashes = builder.get_template_hashes()
    write_lock_atomic(locks_dir / "PROMPT_LOCK.json", json.dumps(prompt_hashes))

    # Model lock
    model_locks = []
    for m in models_config:
        model_locks.append({
            "id": m["id"],
            "revision": m.get("revision", "main"),
            "version": hash_model_version(m["id"], m.get("revision", "main"))
        })
    write_lock_atomic(locks_dir / "MODEL_LOCK.json", json.dumps(model_locks))

    # Corpus lock
    corpus_path = "data/dummy/corpus.jsonl"
    rag_config = load_experiment_config("configs/rag.yaml")
    chunk_config = {
        "chunk_size": rag_config.get("chunk_size", 384),
        "chunk_overlap": rag_config.get("chunk_overlap", 64)
    }
    corpus_hash = hash_corpus(corpus_path, chunk_config, rag_config.get("embedding_model", "BAAI/bge-m3"))
    write_lock_atomic(locks_dir / "CORPUS_LOCK.json", json.dumps({
        "hash": corpus_hash,
        "corpus": corpus_path
    }))

    # Copy locks to repo root
    repo_locks = Path("locks")
    repo_locks.mkdir(exist_ok=True)
    for lock_file in locks_dir.glob("*.json"):
        import shutil
        shutil.copy(str(lock_file), str(repo_locks / lock_file.name))


def main() -> None:
    parser = argparse.ArgumentParser(description="Matibhrom Experiment Runner")
    parser.add_argument("--config", required=True, help="Experiment config path")
    parser.add_argument("--models", required=True, help="Models config path")
    parser.add_argument("--rag-config", required=True, help="RAG config path")
    parser.add_argument("--budget-config", required=True, help="Budget config path")
    parser.add_argument("--run-id", required=True, help="Run ID")
    parser.add_argument("--split", default="test", choices=["dev", "test"])
    parser.add_argument("--conditions", help="Comma list of conditions")
    parser.add_argument("--models-filter", help="Comma list of model IDs")
    parser.add_argument("--limit", type=int, help="Run only first N items")
    parser.add_argument("--resume", action="store_true", help="Resume from existing generations")
    parser.add_argument("--dry-run", action="store_true", help="Print planned calls without running")
    parser.add_argument("--unlock-test", action="store_true", help="Unlock frozen test split")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache reads")
    parser.add_argument("--workers", type=int, default=8, help="Concurrency level")
    parser.add_argument("--check-budget", action="store_true", help="Estimate cost and exit")
    parser.add_argument("--bitwise-reproducible", action="store_true", help="Enable bitwise reproducible mode")

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    logger.info(f"Starting Matibhrom runner: {args.run_id}")

    # Load configs
    exp_config = load_experiment_config(args.config)
    models_config = load_models_config(args.models)
    rag_config = load_experiment_config(args.rag_config)

    # Override with CLI args
    conditions = args.conditions.split(",") if args.conditions else exp_config.get("conditions", ["C0", "C1", "C2", "C3"])
    models_filter = args.models_filter.split(",") if args.models_filter else exp_config.get("models", [])
    limit = args.limit
    split = args.split

    # Filter models
    selected_models = [m for m in models_config if m["id"] in models_filter and m.get("enabled", True)]
    if not selected_models:
        logger.error("No models selected")
        sys.exit(1)

    # Run pre-flight checks
    pre_flight_checks(
        items_path=Path("data/dummy/items.jsonl"),
        evidence_path=Path("data/dummy/evidence.jsonl"),
        corpus_path=Path("data/dummy/corpus.jsonl"),
        budget_config=Path(args.budget_config),
        split=split,
        freeze_test=exp_config.get("freeze_test", True),
        unlocked=args.unlock_test,
    )

    # Create output dirs
    output_dir = Path(exp_config.get("output_dir", "outputs"))
    (output_dir / args.run_id).mkdir(parents=True, exist_ok=True)

    # Load data
    from src.schema import Item, Evidence, CorpusPassage
    from src.validate_data import load_jsonl

    items_raw = load_jsonl(Path("data/dummy/items.jsonl"))
    evidence_raw = load_jsonl(Path("data/dummy/evidence.jsonl"))
    corpus_raw = load_jsonl(Path("data/dummy/corpus.jsonl"))

    items = [Item.model_validate(r) for r in items_raw]

    # Filter by split
    items = [i for i in items if i.split == split]
    if limit:
        items = items[:limit]

    # Build prompt builder
    prompt_builder = PromptBuilder(exp_config.get("prompt_dir", "configs/prompts"))

    # Setup cache
    cache = GenerationCache(output_dir / "cache" / "cache.db")

    # Setup retriever for C2/C3
    retriever = None
    if any(c in conditions for c in ["C2", "C3"]):
        retriever = Retriever(
            corpus_path=rag_config.get("corpus_path", "data/dummy/corpus.jsonl"),
            index_dir=output_dir / args.run_id / "retrieval" / "index",
            embedding_model=rag_config.get("embedding_model", "BAAI/bge-m3"),
            top_k=rag_config.get("top_k", 5),
            chunk_size=rag_config.get("chunk_size", 384),
            chunk_overlap=rag_config.get("chunk_overlap", 64),
        )

    # Create generation runner
    runner = GenerationRunner(
        run_id=args.run_id,
        items=items,
        languages=exp_config.get("languages", ["bn", "banglish"]),
        conditions=conditions,
        models=selected_models,
        prompt_builder=prompt_builder,
        cache=cache,
        retriever=retriever,
        output_dir=output_dir,
    )

    # Create lock files
    config_paths = [args.config, args.models, args.rag_config, args.budget_config]
    create_locks(args.run_id, config_paths, exp_config.get("prompt_dir", "configs/prompts"), selected_models, output_dir)

    # Check budget
    if args.check_budget:
        pricing = load_pricing(args.budget_config)
        # Estimate based on items * models * conditions * languages * avg tokens
        n_generations = len(items) * len(exp_config.get("languages", ["bn", "banglish"])) * len(conditions) * len(selected_models)
        projected_cost = n_generations * 0.01  # Rough estimate
        try:
            check_budget(args.budget_config, projected_cost)
            print(f"Budget OK: projected ${projected_cost:.2f} for {n_generations} generations")
        except BudgetExceededError as e:
            print(f"Budget exceeded: {e}")
            sys.exit(1)
        return

    # Dry run
    if args.dry_run:
        n_languages = len(exp_config.get("languages", ["bn", "banglish"]))
        print(f"Dry run: {len(items)} items x {n_languages} languages x {len(conditions)} conditions x {len(selected_models)} models")
        print(f"Conditions: {conditions}")
        print(f"Models: {[m['id'] for m in selected_models]}")
        return

    # Run generation
    generations = runner.generate_all()

    # Write generation log
    from src.io_atomic import write_jsonl_atomic
    generations_path = output_dir / args.run_id / "generations" / "generations.jsonl"
    for gen in generations:
        write_jsonl_atomic(str(generations_path), gen.model_dump())

    logger.info(f"Generation complete: {len(generations)} generations")
    cache.close()


if __name__ == "__main__":
    main()