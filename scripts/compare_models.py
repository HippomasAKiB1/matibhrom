"""
Cross-Model Comparative Evaluation for Matibhrom.
Compares two experimental runs (e.g. Qwen 1.7B vs Gemma 4B) across conditions,
domains, and registers to produce publication-grade comparative LaTeX tables
and statistical tests (McNemar, Paired Differences).
"""
import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np

# Add repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.stats import mcnemar_test, bootstrap_confidence_interval
from src.validate_data import load_jsonl


def load_run_data(run_dir: Path):
    gen_p = run_dir / "generations" / "generations.jsonl"
    ann_p = run_dir / "annotations" / "annotations.jsonl"
    if not gen_p.exists() or not ann_p.exists():
        raise FileNotFoundError(f"Missing generations or annotations in {run_dir}")
    gens = {g["generation_id"]: g for g in load_jsonl(gen_p)}
    anns = {a["generation_id"]: a for a in load_jsonl(ann_p)}
    
    joined = []
    for gid, g in gens.items():
        if gid in anns:
            row = dict(g)
            row.update(anns[gid])
            joined.append(row)
    return joined


def compute_metrics(rows):
    n = len(rows)
    if n == 0:
        return {"n": 0, "hallucination": 0.0, "coverage": 0.0, "selective_accuracy": 0.0, "abstention": 0.0}
    
    n_abstain = sum(1 for r in rows if r.get("abstention_status") in ("explicit_refusal", "unsupported_claim", "abstain"))
    n_answered = n - n_abstain
    n_correct = sum(1 for r in rows if r.get("correctness") == "correct")
    n_hal = sum(1 for r in rows if r.get("hallucination") == "yes")
    
    hal_rate = n_hal / n
    coverage = n_answered / n
    sel_acc = n_correct / n_answered if n_answered > 0 else 0.0
    abstention_rate = n_abstain / n
    
    hal_vals = [1.0 if r.get("hallucination") == "yes" else 0.0 for r in rows]
    hal_ci = bootstrap_confidence_interval(hal_vals) if hal_vals else {"lower": 0.0, "upper": 0.0}
    
    return {
        "n": n,
        "hallucination": hal_rate,
        "hallucination_ci": hal_ci,
        "coverage": coverage,
        "selective_accuracy": sel_acc,
        "abstention": abstention_rate,
    }


def main():
    parser = argparse.ArgumentParser(description="Compare two Matibhrom runs")
    parser.add_argument("--run-1", required=True, help="First run ID (e.g. Qwen 1.7B)")
    parser.add_argument("--run-2", required=True, help="Second run ID (e.g. Gemma 4B)")
    parser.add_argument("--output-dir", default="outputs", help="Outputs base directory")
    args = parser.parse_args()

    base_out = Path(args.output_dir)
    dir_1 = base_out / args.run_1
    dir_2 = base_out / args.run_2

    rows_1 = load_run_data(dir_1)
    rows_2 = load_run_data(dir_2)

    model_1_name = rows_1[0].get("model_id", args.run_1)
    model_2_name = rows_2[0].get("model_id", args.run_2)

    comp_dir = base_out / f"comparison_{args.run_1}_vs_{args.run_2}"
    comp_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = comp_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    conditions = ["C0", "C1", "C2", "C3"]
    
    # 1. By Condition Comparison
    latex_lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Model & Cond. & Hallucination (95\% CI) & Coverage & Sel. Accuracy & Abstention \\",
        r"\midrule",
    ]

    for model_name, rows in [(model_1_name, rows_1), (model_2_name, rows_2)]:
        latex_lines.append(f"\\multirow{{4}}{{*}}{{{model_name}}} ")
        for c in conditions:
            c_rows = [r for r in rows if r.get("condition") == c]
            m = compute_metrics(c_rows)
            ci = m["hallucination_ci"]
            latex_lines.append(
                f"& {c} & {m['hallucination']:.3f} [{ci['lower']:.2f}, {ci['upper']:.2f}] & "
                f"{m['coverage']:.3f} & {m['selective_accuracy']:.3f} & {m['abstention']:.3f} \\\\"
            )
        latex_lines.append(r"\midrule")

    latex_lines[-1] = r"\bottomrule"
    latex_lines.append(r"\end{tabular}")
    latex_lines.append(r"\caption{Cross-Model Comparison across Grounding Conditions.}")
    latex_lines.append(r"\label{tab:model_scaling_comparison}")
    latex_lines.append(r"\end{table*}")

    tex_path = tables_dir / "model_scaling_comparison.tex"
    tex_path.write_text("\n".join(latex_lines), encoding="utf-8")
    print(f"Wrote comparative LaTeX table to {tex_path}")

    # 2. Paired McNemar between Model 1 and Model 2 (matching item_id, language, condition)
    map_1 = {(r["item_id"], r["language"], r["condition"]): r for r in rows_1}
    map_2 = {(r["item_id"], r["language"], r["condition"]): r for r in rows_2}
    common_keys = set(map_1.keys()) & set(map_2.keys())

    both_no_hal, m1_only_no_hal, m2_only_no_hal = 0, 0, 0
    both_correct, m1_only_corr, m2_only_corr = 0, 0, 0

    for k in common_keys:
        r1 = map_1[k]
        r2 = map_2[k]
        
        # Hallucination
        h1 = r1.get("hallucination") == "no"
        h2 = r2.get("hallucination") == "no"
        if h1 and h2:
            both_no_hal += 1
        elif h1 and not h2:
            m1_only_no_hal += 1
        elif not h1 and h2:
            m2_only_no_hal += 1
            
        # Correctness
        c1 = r1.get("correctness") == "correct"
        c2 = r2.get("correctness") == "correct"
        if c1 and c2:
            both_correct += 1
        elif c1 and not c2:
            m1_only_corr += 1
        elif not c1 and c2:
            m2_only_corr += 1

    mcnemar_hal = mcnemar_test(both_no_hal, m1_only_no_hal, m2_only_no_hal)
    mcnemar_corr = mcnemar_test(both_correct, m1_only_corr, m2_only_corr)

    summary_md = [
        f"# Cross-Model Comparison: {model_1_name} vs. {model_2_name}",
        "",
        f"**Sample Size Evaluated in Common:** {len(common_keys)} matched generations",
        "",
        "## Paired McNemar Statistical Significance Tests",
        f"- **Hallucination Resilience ({model_1_name} vs {model_2_name})**: chi2={mcnemar_hal['statistic']:.3f}, p={mcnemar_hal['p_value']:.4f} (significant={mcnemar_hal['significant']})",
        f"- **Overall Correctness ({model_1_name} vs {model_2_name})**: chi2={mcnemar_corr['statistic']:.3f}, p={mcnemar_corr['p_value']:.4f} (significant={mcnemar_corr['significant']})",
        "",
        "## Overview Table",
        "| Model | Hallucination Rate | Coverage | Selective Accuracy | Abstention Rate |",
        "|---|---|---|---|---|",
    ]

    for model_name, rows in [(model_1_name, rows_1), (model_2_name, rows_2)]:
        m = compute_metrics(rows)
        summary_md.append(f"| {model_name} | {m['hallucination']:.3f} | {m['coverage']:.3f} | {m['selective_accuracy']:.3f} | {m['abstention']:.3f} |")

    summary_path = comp_dir / "summary_comparison.md"
    summary_path.write_text("\n".join(summary_md), encoding="utf-8")
    print(f"Wrote comparative summary to {summary_path}")


if __name__ == "__main__":
    main()
