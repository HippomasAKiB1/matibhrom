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
        row["item_id"] = gen["item_id"]
        row["domain"] = item_domain.get(gen["item_id"], "unknown")
        row["condition"] = gen["condition"]
        row["language"] = gen["language"]
        row["model_id"] = gen["model_id"]
        joined.append(row)
    return joined


import json
from src.eval.stats import bootstrap_confidence_interval, mcnemar_test


def compute_bootstrap_cis(joined_records: list[dict], group_by: str) -> dict[str, dict[str, dict[str, float]]]:
    """Compute 95% bootstrap confidence intervals for hallucination rate and selective accuracy."""
    groups = defaultdict(list)
    for r in joined_records:
        groups[r.get(group_by, "unknown")].append(r)

    ci_results = {}
    for g, rows in groups.items():
        hallucination_vals = [
            1.0 if r.get("hallucination") == "yes" else 0.0
            for r in rows if r.get("hallucination") is not None
        ]
        correctness_vals = [
            1.0 if r.get("correctness") == "correct" else 0.0
            for r in rows if r.get("correctness") is not None
        ]
        ci_results[g] = {
            "hallucination": (
                bootstrap_confidence_interval(hallucination_vals)
                if hallucination_vals
                else {"mean": 0.0, "lower": 0.0, "upper": 0.0}
            ),
            "correctness": (
                bootstrap_confidence_interval(correctness_vals)
                if correctness_vals
                else {"mean": 0.0, "lower": 0.0, "upper": 0.0}
            ),
        }
    return ci_results


def compute_paired_comparisons(joined_records: list[dict]) -> dict[str, Any]:
    """Pairwise McNemar tests for register and evidence conditions."""
    by_item_model_cond = defaultdict(dict)
    for r in joined_records:
        key = (r.get("item_id"), r.get("model_id"), r.get("condition"))
        by_item_model_cond[key][r.get("language")] = r

    # 1. Standard Bangla vs Banglish on correctness
    both_correct, bn_only, bg_only = 0, 0, 0
    for key, langs in by_item_model_cond.items():
        if "bn" in langs and "banglish" in langs:
            bn_corr = langs["bn"].get("correctness") == "correct"
            bg_corr = langs["banglish"].get("correctness") == "correct"
            if bn_corr and bg_corr:
                both_correct += 1
            elif bn_corr and not bg_corr:
                bn_only += 1
            elif not bn_corr and bg_corr:
                bg_only += 1
    mcnemar_lang = mcnemar_test(both_correct, bn_only, bg_only)

    # 2. C0 vs C1 and C0 vs C2 on hallucination
    by_item_model_lang = defaultdict(dict)
    for r in joined_records:
        key = (r.get("item_id"), r.get("model_id"), r.get("language"))
        by_item_model_lang[key][r.get("condition")] = r

    def _paired_cond(c_a, c_b):
        both_c, a_only, b_only = 0, 0, 0
        for key, conds in by_item_model_lang.items():
            if c_a in conds and c_b in conds:
                a_no_hal = conds[c_a].get("hallucination") == "no"
                b_no_hal = conds[c_b].get("hallucination") == "no"
                if a_no_hal and b_no_hal:
                    both_c += 1
                elif a_no_hal and not b_no_hal:
                    a_only += 1
                elif not a_no_hal and b_no_hal:
                    b_only += 1
        return mcnemar_test(both_c, a_only, b_only)

    mcnemar_c0_c1 = _paired_cond("C0", "C1")
    mcnemar_c0_c2 = _paired_cond("C0", "C2")

    return {
        "bn_vs_banglish": mcnemar_lang,
        "c0_vs_c1_hallucination": mcnemar_c0_c1,
        "c0_vs_c2_hallucination": mcnemar_c0_c2,
    }


def compute_retrieval_diagnostics(retrieval_logs: list[dict], item_domain: dict[str, str]) -> dict[str, Any]:
    """Break down Recall@k and gold retrieval by language and domain."""
    by_lang = defaultdict(list)
    by_domain = defaultdict(list)

    for log in retrieval_logs:
        lang = log.get("language", "unknown")
        dom = item_domain.get(log.get("item_id"), "unknown")
        by_lang[lang].append(log)
        by_domain[dom].append(log)

    def _summarize_logs(logs):
        if not logs:
            return {"queries": 0, "recall_at_k": 0.0, "gold_retrieved_count": 0, "rank_1_rate": 0.0}
        n = len(logs)
        retrieved_cnt = sum(1 for l in logs if l.get("gold_retrieved"))
        rank_1_cnt = 0
        for l in logs:
            items = l.get("retrieved", [])
            if items and items[0].get("evidence_id") == l.get("gold_evidence_id"):
                rank_1_cnt += 1
        return {
            "queries": n,
            "gold_retrieved_count": retrieved_cnt,
            "recall_at_k": round(retrieved_cnt / n, 4),
            "rank_1_rate": round(rank_1_cnt / n, 4),
        }

    return {
        "overall": _summarize_logs(retrieval_logs),
        "by_language": {lang: _summarize_logs(logs) for lang, logs in by_lang.items()},
        "by_domain": {dom: _summarize_logs(logs) for dom, logs in by_domain.items()},
    }


def write_retrieval_report(diagnostics: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# Retrieval Diagnostic Report (§12)",
        "",
        "## Overall Retrieval Performance",
        f"- Total Retrieval Queries: {diagnostics['overall']['queries']}",
        f"- Gold Retrieved (Recall@k): {diagnostics['overall']['recall_at_k']:.2%}",
        f"- Gold at Rank 1: {diagnostics['overall']['rank_1_rate']:.2%}",
        "",
        "## Breakdown by Language",
        "| Language | Queries | Recall@k | Gold at Rank 1 |",
        "|----------|---------|----------|----------------|",
    ]
    for lang, s in diagnostics["by_language"].items():
        lines.append(f"| {lang} | {s['queries']} | {s['recall_at_k']:.2%} | {s['rank_1_rate']:.2%} |")

    lines.extend([
        "",
        "## Breakdown by Domain",
        "| Domain | Queries | Recall@k | Gold at Rank 1 |",
        "|--------|---------|----------|----------------|",
    ])
    for dom, s in diagnostics["by_domain"].items():
        lines.append(f"| {dom} | {s['queries']} | {s['recall_at_k']:.2%} | {s['rank_1_rate']:.2%} |")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_latex_table(
    metrics_by_group: dict[str, dict[str, float]],
    cis_by_group: dict[str, dict[str, dict[str, float]]] | None,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Group & Hallucination (95\% CI) & Coverage & Sel. Accuracy & Abstention \\",
        r"\midrule",
    ]
    for group, m in metrics_by_group.items():
        hr = m.get("hallucination_rate", 0)
        ci_str = ""
        if cis_by_group and group in cis_by_group:
            ci = cis_by_group[group].get("hallucination", {})
            ci_str = f" [{ci.get('lower', 0):.2f}, {ci.get('upper', 0):.2f}]"
        lines.append(
            f"{group} & {hr:.3f}{ci_str} & {m.get('coverage', 0):.3f} & "
            f"{m.get('selective_accuracy', 0):.3f} & {m.get('abstention_rate', 0):.3f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def append_stats_to_summary(
    summary_path: Path,
    cis: dict[str, dict[str, dict[str, float]]],
    paired: dict[str, Any],
    retrieval_diag: dict[str, Any] | None,
) -> None:
    content = summary_path.read_text(encoding="utf-8")
    extra = [
        "\n## Bootstrap 95% Confidence Intervals",
        "| Group | Hallucination 95% CI | Selective Accuracy 95% CI |",
        "|---|---|---|",
    ]
    for g, vals in cis.items():
        h = vals["hallucination"]
        c = vals["correctness"]
        extra.append(f"| {g} | [{h['lower']:.3f}, {h['upper']:.3f}] | [{c['lower']:.3f}, {c['upper']:.3f}] |")

    extra.extend([
        "\n## Paired Statistical Comparisons (McNemar Tests)",
        f"- **Standard Bangla vs Banglish**: chi2={paired['bn_vs_banglish']['statistic']:.3f}, p={paired['bn_vs_banglish']['p_value']:.4f} (significant={paired['bn_vs_banglish']['significant']})",
        f"- **C0 vs C1 (Oracle)**: chi2={paired['c0_vs_c1_hallucination']['statistic']:.3f}, p={paired['c0_vs_c1_hallucination']['p_value']:.4f} (significant={paired['c0_vs_c1_hallucination']['significant']})",
        f"- **C0 vs C2 (RAG)**: chi2={paired['c0_vs_c2_hallucination']['statistic']:.3f}, p={paired['c0_vs_c2_hallucination']['p_value']:.4f} (significant={paired['c0_vs_c2_hallucination']['significant']})",
    ])

    if retrieval_diag and retrieval_diag.get("overall", {}).get("queries", 0) > 0:
        extra.extend([
            "\n## Retrieval Diagnostics Overview",
            f"- Overall Recall@k: {retrieval_diag['overall']['recall_at_k']:.2%}",
            f"- Rank 1 Precision: {retrieval_diag['overall']['rank_1_rate']:.2%}",
        ])

    summary_path.write_text(content + "\n" + "\n".join(extra) + "\n", encoding="utf-8")


def build_token_counts_by_model_language(generations: list[dict]) -> dict[str, dict[str, float]]:
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

    item_domain = {}
    items_path = Path(args.items)
    if items_path.exists():
        item_domain = {i["item_id"]: i["domain"] for i in load_jsonl(items_path)}

    if annotations:
        joined = join_generations_and_annotations(generations, annotations, item_domain)
        metrics_by_group = compute_metrics_by_group(joined, args.group_by, retrieval_logs)
        cis_by_group = compute_bootstrap_cis(joined, args.group_by)
        paired_results = compute_paired_comparisons(joined)

        generate_metrics_csv(metrics_by_group, reports_dir / "metrics.csv")
        generate_summary_markdown(metrics_by_group, args.rq_findings, reports_dir / "summary.md")
        write_latex_table(metrics_by_group, cis_by_group, reports_dir / "tables" / "primary_metrics.tex")

        # Save paired comparisons JSON
        with open(reports_dir / "paired_comparisons.json", "w", encoding="utf-8") as f:
            json.dump(paired_results, f, indent=2)

        # Retrieval diagnostics
        retrieval_diag = None
        if retrieval_logs:
            retrieval_diag = compute_retrieval_diagnostics(retrieval_logs, item_domain)
            write_retrieval_report(retrieval_diag, reports_dir / "retrieval_diagnostics.md")

        append_stats_to_summary(reports_dir / "summary.md", cis_by_group, paired_results, retrieval_diag)

        plotted = write_plots(metrics_by_group, reports_dir / "plots")
        print(
            f"Wrote metrics.csv, summary.md (with bootstrap CIs & McNemar), "
            f"tables/primary_metrics.tex, retrieval_diagnostics.md, and plots/ to {reports_dir}"
        )
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
