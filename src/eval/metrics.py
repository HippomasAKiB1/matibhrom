"""
Evaluation metrics for Matibhrom.
"""

import csv
from pathlib import Path
from typing import Any
from collections import defaultdict


def compute_hallucination_rate(annotations: list[dict]) -> float:
    """Fraction of annotations with hallucination=yes."""
    if not annotations:
        return 0.0
    hallucinations = sum(1 for a in annotations if a.get("hallucination") == "yes")
    return hallucinations / len(annotations)


def compute_coverage(annotations: list[dict]) -> float:
    """Fraction with a substantive (non-abstention, non-refusal) answer."""
    if not annotations:
        return 0.0
    substantive = sum(1 for a in annotations if a.get("abstention_status") == "none" and a.get("error_type") != "R")
    return substantive / len(annotations)


def compute_selective_accuracy(annotations: list[dict]) -> float:
    """Accuracy among answered/non-abstained cases."""
    answered = [a for a in annotations if a.get("abstention_status") == "none" and a.get("error_type") != "R"]
    if not answered:
        return 0.0
    correct = sum(1 for a in answered if a.get("correctness") == "correct")
    partially = sum(1 for a in answered if a.get("correctness") == "partially_correct")
    return (correct + 0.5 * partially) / len(answered)


def compute_unsupported_claim_rate(annotations: list[dict]) -> float:
    """Fraction with H2/H3 among partially correct."""
    partially_correct = [a for a in annotations if a.get("correctness") == "partially_correct"]
    if not partially_correct:
        return 0.0
    unsupported = sum(1 for a in partially_correct if a.get("error_type") in ("H2", "H3"))
    return unsupported / len(partially_correct)


def compute_abstention_rate(annotations: list[dict]) -> float:
    """Fraction with abstention_status != none."""
    if not annotations:
        return 0.0
    abstentions = sum(1 for a in annotations if a.get("abstention_status") != "none")
    return abstentions / len(annotations)


def compute_tier2_abstention_rate(annotations: list[dict]) -> float:
    """Fraction flagged as tier-2 abstention candidates."""
    if not annotations:
        return 0.0
    tier2 = sum(1 for a in annotations if a.get("tier2_abstention_candidate") == True)
    return tier2 / len(annotations)


def compute_retrieval_recall(retrieval_logs: list[dict]) -> float:
    """Fraction of items where gold evidence was retrieved."""
    if not retrieval_logs:
        return 0.0
    retrieved = sum(1 for r in retrieval_logs if r.get("gold_retrieved") == True)
    return retrieved / len(retrieval_logs)


def compute_metrics(
    annotations: list[dict],
    retrieval_logs: list[dict] | None = None,
) -> dict[str, float]:
    """
    Compute all primary metrics.

    Args:
        annotations: List of annotation dicts
        retrieval_logs: Optional list of retrieval log dicts

    Returns:
        Dictionary of metric names to values
    """
    metrics = {
        "hallucination_rate": compute_hallucination_rate(annotations),
        "coverage": compute_coverage(annotations),
        "selective_accuracy": compute_selective_accuracy(annotations),
        "unsupported_claim_rate": compute_unsupported_claim_rate(annotations),
        "abstention_rate": compute_abstention_rate(annotations),
        "tier2_abstention_rate": compute_tier2_abstention_rate(annotations),
    }

    if retrieval_logs:
        metrics["retrieval_recall_at_k"] = compute_retrieval_recall(retrieval_logs)

    return metrics


def compute_metrics_by_group(
    annotations: list[dict],
    group_key: str,
    retrieval_logs: list[dict] | None = None,
) -> dict[str, dict[str, float]]:
    """
    Compute metrics grouped by a key (e.g., domain, condition, language).

    Args:
        annotations: List of annotation dicts
        group_key: Field to group by
        retrieval_logs: Optional retrieval logs

    Returns:
        Dictionary mapping group values to metric dictionaries
    """
    groups = defaultdict(list)
    for a in annotations:
        group_val = a.get(group_key, "unknown")
        groups[group_val].append(a)

    results = {}
    for group_val, group_annotations in groups.items():
        results[group_val] = compute_metrics(group_annotations, retrieval_logs)

    return results


def generate_metrics_csv(
    metrics_by_group: dict[str, dict[str, float]],
    output_path: str | Path,
) -> None:
    """Write metrics to CSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["group"] + list(metrics_by_group.get(next(iter(metrics_by_group)), {}).keys()))
        for group, metrics in metrics_by_group.items():
            writer.writerow([group] + [metrics.get(m, "") for m in metrics.keys()])


def generate_summary_markdown(
    metrics_by_group: dict[str, dict[str, float]],
    rq_findings: str,
    output_path: str | Path,
) -> None:
    """Write summary markdown aligned with RQ1-RQ4."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Matibhrom Results Summary", "", "## Research Questions", ""]
    lines.append(rq_findings)
    lines.append("")
    lines.append("## Metrics by Group")
    lines.append("")
    lines.append("| Group | Hallucination Rate | Coverage | Selective Accuracy | Abstention Rate |")
    lines.append("|-------|-------------------|----------|-------------------|----------------|")

    for group, metrics in metrics_by_group.items():
        hr = metrics.get("hallucination_rate", 0)
        cov = metrics.get("coverage", 0)
        sa = metrics.get("selective_accuracy", 0)
        ab = metrics.get("abstention_rate", 0)
        lines.append(f"| {group} | {hr:.3f} | {cov:.3f} | {sa:.3f} | {ab:.3f} |")

    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")