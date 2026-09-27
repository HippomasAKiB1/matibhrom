"""
Evaluation module for Matibhrom.
"""

from .metrics import (
    compute_metrics,
    compute_metrics_by_group,
    compute_hallucination_rate,
    compute_coverage,
    compute_selective_accuracy,
    compute_unsupported_claim_rate,
    compute_abstention_rate,
    compute_tier2_abstention_rate,
    compute_retrieval_recall,
    generate_metrics_csv,
    generate_summary_markdown,
)
from .stats import (
    cohens_kappa,
    mcnemar_test,
    mixed_model_regression,
    bootstrap_confidence_interval,
    run_statistical_analysis,
)

__all__ = [
    "compute_metrics",
    "compute_metrics_by_group",
    "compute_hallucination_rate",
    "compute_coverage",
    "compute_selective_accuracy",
    "compute_unsupported_claim_rate",
    "compute_abstention_rate",
    "compute_tier2_abstention_rate",
    "compute_retrieval_recall",
    "generate_metrics_csv",
    "generate_summary_markdown",
    "cohens_kappa",
    "mcnemar_test",
    "mixed_model_regression",
    "bootstrap_confidence_interval",
    "run_statistical_analysis",
]