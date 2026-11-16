# Matibhrom: Academic Paper Manuscript Source (LaTeX)

This directory contains the publication manuscript for **Matibhrom (\foreignlanguage{bengali}{মতিভ্রম}): A Fine-Grained Benchmark for Hallucination, Grounding, and Selective Abstention in Bengali LLMs**.

---

## 1. Directory Structure

```
paper/
├── main.tex                    # Master LaTeX document
├── references.bib              # Complete BibTeX bibliography (24 verified Q1/ACL entries)
├── README.md                   # This documentation guide
├── tables/                     # Publication tables (LaTeX booktabs format)
│   ├── table1_scaling_comparison.tex  # Table 1: Cross-Model 4-Condition Comparison (N=480)
│   └── table2_domain_disparity.tex    # Table 2: Domain Disparity Breakdown (General, Medical, Legal)
├── figures/                    # Publication figures and plots
│   ├── abstention_rate.png
│   ├── coverage.png
│   ├── hallucination_rate.png
│   ├── retrieval_recall_at_k.png
│   ├── selective_accuracy.png
│   ├── tier2_abstention_rate.png
│   └── unsupported_claim_rate.png
└── sections/                   # Modular LaTeX sections
    ├── 00_abstract.tex         # Comprehensive abstract with empirical findings
    ├── 01_introduction.tex     # Motivation, linguistic hurdles, and 5 foundational RQs
    ├── 02_related_work.tex     # Systematic review of 4 major literature clusters
    ├── 03_matibhrom_benchmark.tex # Benchmark design, schemas, and 1,800-passage corpus
    ├── 04_methodology_and_framework.tex # C0-C3 formalization, metrics, equations, TikZ diagram & Algorithm 1
    ├── 05_empirical_results.tex # Cross-model findings, McNemar tests, bootstrap CIs, retrieval diagnostics
    ├── 06_error_taxonomy.tex   # Fine-grained taxonomy (H1-H5, A, R) with verbatim Bengali case studies
    ├── 07_evaluation_reliability.tex # Failure of LLM-as-a-Judge (kappa <= 0.34) & gold adjudication
    ├── 08_discussion_limitations.tex # Deployment implications, limitations, and mandatory ACL ethics
    └── 09_conclusion.tex       # Summary of theoretical and empirical contributions
```

---

## 2. Compilation Instructions

The project is designed for **100% engine portability** (supporting standard `pdflatex`, `xelatex`, `lualatex`, or Overleaf).

### On Overleaf:
1. Zip the contents of the `paper/` folder.
2. Create a "New Project" $\rightarrow$ "Upload Project" on Overleaf.
3. Select `main.tex` as the main document.
4. Click **Recompile** (compatible with default pdfLaTeX or XeLaTeX compiler).

### Local CLI Compilation:
Using TeX Live or MiKTeX:
```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

---

## 3. Key Publication Highlights

* **Theoretical Framework:** Formulates the 4 controlled grounding conditions: Closed-book ($C_0$), Oracle Grounding ($C_1$), Dense RAG with Distractors ($C_2$), and Selective Abstention ($C_3$).
* **Empirical Rigor:** Full paired McNemar significance tests with Edwards' continuity correction ($\chi^2$) and 1,000-sample bootstrap 95% confidence intervals on every metric.
* **Core Discovery:** Model scaling from 1.7B to 4B parameters unlocks emergent selective abstention under noisy retrieval ($p = 0.0004$), reducing hallucination rate to **1.7%** with **90.0% selective accuracy**.
* **Linguistic Asymmetry:** Demonstrates that informal Latin transliteration (Banglish) slashes dense retriever recall from 66.7% to 30.0% and induces a 3.27-fold surge in generative hallucination ($p < 0.001$).
* **Methodological Contribution:** Empirically demonstrates the failure of zero-shot LLM-as-a-judge evaluators in low-resource Bengali ($\kappa \le 0.34$), establishing the imperative for deterministic gold-evidence verification.
