"""
Estimate the projected cost of a planned run and check it against
configs/budget.yaml's max_usd cap, without running any generations.

Usage:
    python scripts/check_budget.py --config configs/experiments.yaml \
        --models configs/models.yaml --budget-config configs/budget.yaml \
        --items data/dummy/items.jsonl
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from src.budget import BudgetExceededError, check_budget, estimate_cost, load_pricing
from src.validate_data import load_jsonl

# Rough average token counts used only for pre-run cost projection.
# Actual generations will use real prompt/response token counts.
AVG_PROMPT_TOKENS_BY_CONDITION = {"C0": 80, "C1": 300, "C2": 600, "C3": 650}
AVG_RESPONSE_TOKENS = 120


def project_cost(
    n_items: int,
    languages: list[str],
    conditions: list[str],
    models: list[dict],
    pricing: dict,
) -> tuple[float, dict[str, float]]:
    """Return (total_cost, cost_by_model) for the planned run."""
    cost_by_model: dict[str, float] = {}
    for model in models:
        model_id = model.get("model") or model["id"]
        model_cost = 0.0
        for condition in conditions:
            prompt_tokens = AVG_PROMPT_TOKENS_BY_CONDITION.get(condition, 200)
            n_calls = n_items * len(languages)
            model_cost += n_calls * estimate_cost(
                model_id, prompt_tokens, AVG_RESPONSE_TOKENS, pricing
            )
        cost_by_model[model["id"]] = model_cost
    return sum(cost_by_model.values()), cost_by_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Project run cost and check it against the budget cap")
    parser.add_argument("--config", default="configs/experiments.yaml")
    parser.add_argument("--models", default="configs/models.yaml")
    parser.add_argument("--budget-config", default="configs/budget.yaml")
    parser.add_argument("--items", default="data/dummy/items.jsonl")
    parser.add_argument("--conditions", help="Comma list of conditions (default: from experiments.yaml)")
    parser.add_argument("--models-filter", help="Comma list of model IDs (default: all enabled)")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        exp_config = yaml.safe_load(f)
    with open(args.models, encoding="utf-8") as f:
        models_config = yaml.safe_load(f).get("models", [])

    conditions = args.conditions.split(",") if args.conditions else exp_config.get("conditions", ["C0", "C1", "C2", "C3"])
    languages = exp_config.get("languages", ["bn", "banglish"])

    if args.models_filter:
        wanted = set(args.models_filter.split(","))
        selected_models = [m for m in models_config if m["id"] in wanted]
    else:
        selected_models = [m for m in models_config if m.get("enabled", True)]

    items = load_jsonl(Path(args.items))
    n_items = len(items)

    pricing = load_pricing(args.budget_config)
    total_cost, cost_by_model = project_cost(n_items, languages, conditions, selected_models, pricing)

    print(f"Planned run: {n_items} items x {len(languages)} languages x {len(conditions)} conditions x {len(selected_models)} models")
    print(f"Conditions: {conditions}")
    print("Projected cost by model:")
    for model_id, cost in cost_by_model.items():
        print(f"  {model_id}: ${cost:.2f}")
    print(f"Total projected cost: ${total_cost:.2f}")

    try:
        check_budget(args.budget_config, total_cost)
    except BudgetExceededError as e:
        print(f"\nBUDGET CHECK FAILED: {e}")
        sys.exit(1)

    print("\nBudget check passed.")


if __name__ == "__main__":
    main()
