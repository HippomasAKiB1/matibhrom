"""
Join generations + annotations and export the publication artifacts described
in README §16:

- outputs/{run_id}/reports/metrics.csv
- outputs/{run_id}/reports/tables/primary_metrics.tex
- outputs/{run_id}/reports/summary.md
- outputs/{run_id}/reports/tokenization_report.md

Usage:
    python scripts/export_tables.py --run-id main_v1 --group-by condition
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.metrics import compute_metrics_by_group, generate_metrics_csv, generate_summary_markdown
from src.eval.report import generate_tokenization_report
from src.validate_data import load_jsonl


def join_generations_and_annotations(
    generations: list[dict], annotations: list[dict], item_domain: dict[str, str] | None = None
) -> list[dict]:
    """Join annotation records onto their generation's metadata (domain,
    condition, language, model_id) by generation_id, keeping the
    adjudicated/human label when both an LLM pre-label and a human label
    exist for the same generation.

    `Generation` records don't carry `domain` directly (only `item_id`), so
    `item_domain` (item_id -> domain, built from items.jsonl) is used to
    attach it; without it, domain-based grouping falls back to "unknown".
    """
    item_domain = item_domain or {}
    gen_by_id = {g["generation_id"]: g for g in generations}

    # Prefer verified/human labels over unverified LLM pre-labels for the
    # same generation_id.
    best: dict[str, dict] = {}
    for ann in annotations:
        gid = ann["generation_id"]
        if gid not in gen_by_id:
            continue
        existing = best.get(gid)
        if existing is None:
            best[gid] = ann
            continue
        existing_rank = 1 if existing.get("verified_by_human") or existing.get("labeler_type") == "human" else 0
        new_rank = 1 if ann.get("verified_by_human") or ann.get("labeler_type") == "human" else 0
        if new_rank > existing_rank:
            best[gid] = ann

    joined = []
    for gid, ann in best.items():
        gen = gen_by_id[gid]
        row = dict(ann)
        row["domain"] = item_domain.get(gen["item_id"], "unknown")
        row["condition"] = gen["condition"]
        row["language"] = gen["language"]
        row["model_id"] = gen["model_id"]
        joined.append(row)
    return joined


def write_latex_table(metrics_by_group: dict[str, dict[str, float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Group & Hallucination & Coverage & Sel. Accuracy & Abstention \\",
        r"\midrule",
    ]
    for group, m in metrics_by_group.items():
        lines.append(
            f"{group} & {m.get('hallucination_rate', 0):.3f} & {m.get('coverage', 0):.3f} & "
            f"{m.get('selective_accuracy', 0):.3f} & {m.get('abstention_rate', 0):.3f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_token_counts_by_model_language(generations: list[dict]) -> dict[str, dict[str, float]]:
    """Average prompt_tokens per model, split by bn/banglish, for the
    tokenization report (README §7.1 / §16 P0 fix)."""
    sums: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for g in generations:
        sums[g["model_id"]][g["language"]].append(g.get("prompt_tokens", 0))

    result = {}
    for model_id, by_lang in sums.items():
        result[model_id] = {
            lang: (sum(vals) / len(vals) if vals else 0.0) for lang, vals in by_lang.items()
        }
    return result


def write_plots(metrics_by_group: dict[str, dict[str, float]], plots_dir: Path) -> list[str]:
    """Bar chart per metric across groups (README §16). Returns the list of
    metric names actually plotted (skips a metric if no group has it)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plots_dir.mkdir(parents=True, exist_ok=True)
    groups = list(metrics_by_group.keys())
    if not groups:
        return []

    metric_names = sorted({m for g in metrics_by_group.values() for m in g.keys()})
    plotted = []
    for metric in metric_names:
        values = [metrics_by_group[g].get(metric, 0.0) for g in groups]
        fig, ax = plt.subplots(figsize=(max(4, len(groups) * 0.8), 4))
        ax.bar(groups, values, color="#3b6ea5")
        ax.set_ylabel(metric.replace("_", " "))
        ax.set_title(metric.replace("_", " ").title())
        ax.set_ylim(0, max(1.0, max(values, default=1.0) * 1.1))
        plt.xticks(rotation=30, ha="right")
        fig.tight_layout()
        fig.savefig(plots_dir / f"{metric}.png", dpi=150)
        plt.close(fig)
        plotted.append(metric)
    return plotted


def main() -> None:
    parser = argparse.ArgumentParser(description="Export metrics tables and reports for a run")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--items", default="data/dummy/items.jsonl", help="items.jsonl, used to attach domain")
    parser.add_argument("--output-dir", default="outputs", help="Base output directory")
    parser.add_argument("--group-by", default="condition", choices=["condition", "domain", "language", "model_id"])
    parser.add_argument(
        "--rq-findings",
        default="See generations/annotations for this run; findings pending qualitative write-up.",
    )
    args = parser.parse_args()

    run_dir = Path(args.output_dir) / args.run_id
    generations_path = run_dir / "generations" / "generations.jsonl"
    annotations_path = run_dir / "annotations" / "annotations.jsonl"
    retrieval_logs_path = run_dir / "retrieval" / "retrieval_logs.jsonl"

    if not generations_path.exists():
        print(f"No generations found at {generations_path}", file=sys.stderr)
        sys.exit(1)

    generations = load_jsonl(generations_path)
    annotations = load_jsonl(annotations_path) if annotations_path.exists() else []
    retrieval_logs = load_jsonl(retrieval_logs_path) if retrieval_logs_path.exists() else []

    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if annotations:
        item_domain = {}
        items_path = Path(args.items)
        if items_path.exists():
            item_domain = {i["item_id"]: i["domain"] for i in load_jsonl(items_path)}
        joined = join_generations_and_annotations(generations, annotations, item_domain)
        metrics_by_group = compute_metrics_by_group(joined, args.group_by, retrieval_logs)

        generate_metrics_csv(metrics_by_group, reports_dir / "metrics.csv")
        generate_summary_markdown(metrics_by_group, args.rq_findings, reports_dir / "summary.md")
        write_latex_table(metrics_by_group, reports_dir / "tables" / "primary_metrics.tex")
        plotted = write_plots(metrics_by_group, reports_dir / "plots")
        print(f"Wrote metrics.csv, summary.md, tables/primary_metrics.tex, and plots/{{{','.join(plotted)}}}.png to {reports_dir}")
    else:
        print(
            f"No annotations found at {annotations_path} — skipping metrics.csv/summary.md/"
            f"primary_metrics.tex (they require annotated generations). "
            f"Run scripts/sample_for_annotation.py and annotate first."
        )

    token_counts = build_token_counts_by_model_language(generations)
    generate_tokenization_report(token_counts, reports_dir / "tokenization_report.md")
    print(f"Wrote tokenization_report.md to {reports_dir}")


if __name__ == "__main__":
    main()
