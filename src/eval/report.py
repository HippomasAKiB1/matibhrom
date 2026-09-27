"""
Report generation for Matibhrom.
"""

from pathlib import Path
from typing import Any


def generate_tokenization_report(
    token_counts: dict[str, dict[str, float]],
    output_path: str | Path,
) -> None:
    """
    Generate a tokenization report showing Bangla vs Banglish token count ratios.

    Args:
        token_counts: Dict mapping model names to token count ratios
        output_path: Path to write the report
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Tokenization Report",
        "",
        "This report shows the ratio of Bangla (bn) to Banglish (banglish) token counts",
        "for each model on the same factual question. This ratio is critical for",
        "understanding model capacity differences across language registers.",
        "",
        "## Token Count Ratios",
        "",
        "| Model | Banglish Tokens | Bangla Tokens | Ratio (Banglish/Bangla) |",
        "|-------|----------------|---------------|------------------------|",
    ]

    for model, counts in token_counts.items():
        bn = counts.get("bn", 0)
        bg = counts.get("banglish", 0)
        ratio = bg / bn if bn > 0 else 0.0
        lines.append(f"| {model} | {bg:.0f} | {bn:.0f} | {ratio:.2f} |")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("A ratio > 1.0 indicates Banglish requires more tokens (higher entropy).")
    lines.append("A ratio < 1.0 indicates Bangla requires more tokens.")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_bibliography(
    sources: list[dict],
    output_path: str | Path,
) -> None:
    """
    Generate a bibliography from sources.

    Args:
        sources: List of source dicts with fields like title, authors, year, etc.
        output_path: Path to write the bibliography
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Bibliography", ""]

    for i, source in enumerate(sources, 1):
        ref = f"{i}. "

        # Authors
        if "authors" in source:
            authors = source["authors"]
            if isinstance(authors, list):
                ref += ", ".join(authors)
            else:
                ref += authors
            ref += ", "

        # Title
        if "title" in source:
            ref += f'"{source["title"]}", '

        # Publication info
        if "venue" in source:
            ref += f'{source["venue"]}, '
        if "year" in source:
            ref += f'{source["year"]}. '

        # Publisher/location
        if "publisher" in source:
            ref += f'{source["publisher"]}. '
        if "url" in source:
            ref += f'Available: {source["url"]}'

        lines.append(ref)

    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_limitations_document(
    limitations: list[str],
    output_path: str | Path,
) -> None:
    """
    Generate a document explaining limitations and caveats.

    Args:
        limitations: List of limitation descriptions
        output_path: Path to write the limitations document
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Limitations and Caveats",
        "",
        "The Matibhrom platform has several limitations that should be considered",
        "when interpreting results. These limitations are documented here for",
        "transparency and to guide future work.",
        "",
    ]

    for i, limitation in enumerate(limitations, 1):
        lines.append(f"{i}. {limitation}")

    lines.append("")
    lines.append("## Recommendations for Future Work")
    lines.append("")
    lines.append("1. Expand the distractor corpus to better match real-world retrieval scenarios.")
    lines.append("2. Include more models from different families (mistral, llama, etc.).")
    lines.append("3. Add domain-specific evaluation metrics for medical and legal accuracy.")
    lines.append("4. Expand to more dialects and registers beyond Standard Bangla and Banglish.")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_results_summary(
    metrics_by_group: dict[str, dict[str, float]],
    statistical_results: dict[str, Any],
    rq_findings: str,
    output_path: str | Path,
) -> None:
    """
    Generate a comprehensive results summary.

    Args:
        metrics_by_group: Metrics computed for each group
        statistical_results: Results from statistical tests
        rq_findings: Findings aligned with research questions
        output_path: Path to write the summary
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Matibhrom Experiment Results",
        "",
        "## Executive Summary",
        "",
        rq_findings,
        "",
        "## Key Metrics by Group",
        "",
        "| Group | Hallucination Rate | Coverage | Selective Accuracy |",
        "|-------|-------------------|----------|-------------------|",
    ]

    for group, metrics in metrics_by_group.items():
        hr = metrics.get("hallucination_rate", 0)
        cov = metrics.get("coverage", 0)
        sa = metrics.get("selective_accuracy", 0)
        lines.append(f"| {group} | {hr:.3f} | {cov:.3f} | {sa:.3f} |")

    lines.append("")
    lines.append("## Statistical Analysis")
    lines.append("")

    # Add McNemar test results if available
    if "mcnemar" in statistical_results:
        lines.append("### McNemar Tests (paired comparisons)")
        lines.append("")
        for group, result in statistical_results["mcnemar"].items():
            sig = "✓" if result.get("significant") else ""
            lines.append(f"- {group}: χ²={result.get('statistic', 0):.3f}, p={result.get('p_value', 1.0):.3f} {sig}")

    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    lines.append("Based on the results, the following recommendations are made:")
    lines.append("")
    lines.append("1. Register effects: The difference between Standard Bangla and Banglish")
    lines.append("   should be analyzed using the McNemar tests above.")
    lines.append("")
    lines.append("2. Evidence condition effects: Compare C0 vs C1, C1 vs C2, C2 vs C3")
    lines.append("   using paired tests where the same items are used.")
    lines.append("")
    lines.append("3. Model effects: Consider hierarchical models with random intercepts")
    lines.append("   for items to account for within-item correlations.")

    output_path.write_text("\n".join(lines), encoding="utf-8")