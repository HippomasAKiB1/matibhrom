"""
Statistical analysis for Matibhrom.
"""

from typing import Any
import numpy as np
from scipy import stats
from statsmodels.formula.api import mixedlm
from statsmodels.tools.sm_exceptions import ConvergenceWarning
import warnings

warnings.filterwarnings("ignore", category=ConvergenceWarning)


def cohens_kappa(contingency_table: list[list[int]]) -> float:
    """
    Compute Cohen's kappa for agreement.

    Args:
        contingency_table: 2x2 table [[a,b],[c,d]] where
            a = both say yes
            b = rater1 yes, rater2 no
            c = rater1 no, rater2 yes
            d = both no

    Returns:
        Cohen's kappa
    """
    a, b, c, d = contingency_table[0][0], contingency_table[0][1], contingency_table[1][0], contingency_table[1][1]
    n = a + b + c + d
    if n == 0:
        return 0.0

    # Observed agreement
    po = (a + d) / n

    # Expected agreement
    p1_yes = (a + b) / n
    p2_yes = (a + c) / n
    pe = p1_yes * p2_yes + (1 - p1_yes) * (1 - p2_yes)

    if pe == 1:
        return 1.0

    kappa = (po - pe) / (1 - pe)
    return kappa


def mcnemar_test(both_correct: int, rater1_only: int, rater2_only: int) -> dict[str, Any]:
    """
    McNemar's test for paired comparisons.

    Args:
        both_correct: Both raters agree on correct
        rater1_only: Rater1 says correct, rater2 says incorrect
        rater2_only: Rater1 says incorrect, rater2 says correct

    Returns:
        Dictionary with statistic, p-value, and significance
    """
    # Handle edge cases
    if rater1_only + rater2_only == 0:
        return {"statistic": 0.0, "p_value": 1.0, "significant": False}

    # McNemar's chi-square test
    chi2 = (abs(rater1_only - rater2_only) - 1) ** 2 / (rater1_only + rater2_only)
    p_value = stats.chi2.sf(chi2, 1)

    return {
        "statistic": chi2,
        "p_value": p_value,
        "significant": p_value < 0.05,
    }


def mixed_model_regression(
    data: list[dict],
    formula: str = "hallucination ~ register + domain + evidence_condition + model + register:evidence_condition + domain:evidence_condition + (1 | item)",
) -> dict[str, Any]:
    """
    Mixed-effects logistic regression.

    Args:
        data: List of dicts with keys matching formula variables
        formula: statsmodels formula string

    Returns:
        Dictionary with model results and convergence flag
    """
    try:
        model = mixedlm(formula, data, missing="drop")
        result = model.fit()

        return {
            "converged": result.converged,
            "aic": result.aic,
            "bic": result.bic,
            "llf": result.llf,
            "params": {k: v for k, v in zip(result.params.index, result.params)},
            "p_values": {k: v for k, v in zip(result.pvalues.index, result.pvalues)},
            "summary": result.summary().as_text(),
        }
    except Exception as e:
        return {
            "converged": False,
            "error": str(e),
            "fallback": True,
        }


def bootstrap_confidence_interval(
    values: list[float],
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
) -> dict[str, float]:
    """
    Compute bootstrap confidence interval for a statistic.

    Args:
        values: List of values to resample
        n_bootstrap: Number of bootstrap samples
        confidence_level: Confidence level (0.95 = 95% CI)

    Returns:
        Dictionary with mean, std, lower, upper
    """
    if not values:
        return {"mean": 0.0, "std": 0.0, "lower": 0.0, "upper": 0.0}

    bootstrap_means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(values, size=len(values), replace=True)
        bootstrap_means.append(np.mean(sample))

    lower = np.percentile(bootstrap_means, (1 - confidence_level) / 2 * 100)
    upper = np.percentile(bootstrap_means, (1 + confidence_level) / 2 * 100)
    mean = np.mean(bootstrap_means)
    std = np.std(bootstrap_means)

    return {
        "mean": float(mean),
        "std": float(std),
        "lower": float(lower),
        "upper": float(upper),
    }


def run_statistical_analysis(
    annotations_by_group: dict[str, list[dict]],
    formula: str | None = None,
) -> dict[str, Any]:
    """
    Run full statistical analysis pipeline.

    Args:
        annotations_by_group: Dict mapping group names to annotation lists
        formula: Custom regression formula (optional)

    Returns:
        Dictionary with all analysis results
    """
    results = {}

    # McNemar tests for paired comparisons (e.g., Standard Bangla vs Banglish)
    mcnemar_results = {}
    for group_name, group_data in annotations_by_group.items():
        # Create paired contingency table
        both_correct = 0
        rater1_only = 0
        rater2_only = 0

        for item_data in group_data:
            rater1 = item_data.get("rater1")
            rater2 = item_data.get("rater2")
            if rater1 is not None and rater2 is not None:
                if rater1 == "correct" and rater2 == "correct":
                    both_correct += 1
                elif rater1 == "correct" and rater2 == "incorrect":
                    rater1_only += 1
                elif rater1 == "incorrect" and rater2 == "correct":
                    rater2_only += 1

        mcnemar_results[group_name] = mcnemar_test(both_correct, rater1_only, rater2_only)

    results["mcnemar"] = mcnemar_results

    # Mixed model regression if data supports it
    if formula:
        # Flatten data for regression
        flat_data = []
        for group_name, group_data in annotations_by_group.items():
            for item_data in group_data:
                flat_data.append({
                    **item_data,
                    "group": group_name,
                    "register": item_data.get("register", "bn"),
                    "domain": item_data.get("domain", "general"),
                    "evidence_condition": item_data.get("condition", "C0"),
                    "model": item_data.get("model", "dummy"),
                })

        results["mixed_model"] = mixed_model_regression(flat_data, formula)

    return results