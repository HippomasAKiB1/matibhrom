"""
Cost estimator and budget guard for Matibhrom.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    """Raised when projected cost exceeds budget limits."""
    pass


def estimate_cost(
    model_id: str,
    prompt_tokens: int,
    response_tokens: int,
    pricing: dict[str, dict[str, float]],
) -> float:
    """
    Estimate cost for a generation.

    Args:
        model_id: Model identifier
        prompt_tokens: Number of input tokens
        response_tokens: Number of output tokens
        pricing: Pricing dictionary from configs/budget.yaml

    Returns:
        Cost in USD
    """
    if model_id not in pricing:
        # Fallback: try to match prefix
        matched = False
        for model_prefix in pricing:
            if model_id.startswith(model_prefix):
                pricing_info = pricing[model_prefix]
                matched = True
                break
        if not matched:
            logger.warning(f"No pricing found for {model_id}, assuming free")
            return 0.0
    else:
        pricing_info = pricing[model_id]

    input_cost = (prompt_tokens / 1_000_000) * pricing_info["input_per_million"]
    output_cost = (response_tokens / 1_000_000) * pricing_info["output_per_million"]

    return input_cost + output_cost


def load_pricing(config_path: str | Path) -> dict[str, dict[str, float]]:
    """Load pricing from budget config."""
    path = Path(config_path)
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("pricing", {})


def check_budget(
    config_path: str | Path,
    projected_cost: float,
) -> None:
    """
    Check if projected cost exceeds budget.

    Args:
        config_path: Path to budget config
        projected_cost: Estimated cost in USD

    Raises:
        BudgetExceededError: If cost exceeds max_usd
    """
    path = Path(config_path)
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    max_usd = config.get("max_usd", float("inf"))
    if projected_cost > max_usd:
        raise BudgetExceededError(
            f"Projected cost ${projected_cost:.2f} exceeds budget ${max_usd:.2f}"
        )