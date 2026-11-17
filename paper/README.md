# Matibhrom: Academic Paper Manuscript Source (LaTeX)

This directory contains the publication manuscript for **Matibhrom (\foreignlanguage{bengali}{মতিভ্রম}): A Fine-Grained Benchmark for Hallucination, Grounding, and Selective Abstention in Bengali LLMs**.

---

## 1. Directory Structure

```
paper/
├── .latexmkrc                  # Build configuration directing Overleaf / latexmk to use XeLaTeX
├── main.tex                    # Master LaTeX document (dual-engine: XeLaTeX & pdfLaTeX)
├── references.bib              # Complete BibTeX bibliography (24 verified Q1/ACL entries)
├── README.md                   # This documentation guide
├── fonts/                      # High-resolution publication fonts
│   └── NotoSerifBengali.ttf   # Bundled OpenType font for authentic Bengali complex script shaping
├── tables/                     # Publication tables (LaTeX booktabs format)
│   ├── table1_scaling_comparison.tex  # Table 1: Cross-Model 4-Condition Comparison (Authoritative Test Split)
│   └── table2_domain_disparity.tex    # Table 2: Domain Disparity Breakdown (General, Medical, Legal)
├── figures/                    # Publication figures and 300 DPI plots
│   ├── figure2_scaling_abstention.png # High-res scaling emergence plot (300 DPI)
│   ├── figure3_domain_register.png    # High-res domain and register degradation plot (300 DPI)
│   └── ...                            # Supplementary plots
└── sections/                   # Modular LaTeX sections
    ├── 00_abstract.tex         # Comprehensive abstract with empirical findings
    ├── 01_introduction.tex     # Motivation, linguistic hurdles, and 5 foundational RQs
    ├── 02_related_work.tex     # Systematic review of 4 major literature clusters
    ├── 03_matibhrom_benchmark.tex # Benchmark design, schemas, and 1,800-passage corpus
    ├── 04_methodology_and_framework.tex # C0-C3 formalization, metrics, equations, TikZ diagram & Algorithm 1
    ├── 05_empirical_results.tex # Cross-model findings, McNemar tests, Wilson CIs, retrieval diagnostics
    ├── 06_error_taxonomy.tex   # Fine-grained taxonomy (H1-H5, A, R) with verbatim Bengali case studies
    ├── 07_evaluation_reliability.tex # Failure of LLM-as-a-Judge (kappa <= 0.34) & gold adjudication
    ├── 08_discussion_limitations.tex # Deployment implications, limitations, and mandatory ACL ethics
    └── 09_conclusion.tex       # Summary of theoretical and empirical contributions
```

---

## 2. Compilation Instructions on Overleaf

The manuscript is configured with **dual-engine support**:

### Recommended (Best Typography & Native Script):
1. Import `matibhrom_manuscript.zip` into Overleaf.
2. The included `.latexmkrc` automatically configures Overleaf to use **XeLaTeX**.
3. If setting manually: click **Menu** (top-left) $\rightarrow$ set **Compiler** to **XeLaTeX**.
4. Click **Recompile**.
   - XeLaTeX automatically loads the bundled `fonts/NotoSerifBengali.ttf` font, rendering Bengali script conjuncts and diacritics natively with complex OpenType shaping.

### pdfLaTeX Fallback:
- If compiled with default `pdfLaTeX`, the embedded UTF-8 fallback table prevents compilation crashes and maps Bengali tokens safely.

---

## 3. Key Publication Highlights

* **Theoretical Framework:** Formulates 4 controlled grounding conditions: Closed-book ($C_0$), Oracle Grounding ($C_1$), Dense RAG with Distractors ($C_2$), and Selective Abstention ($C_3$).
* **Empirical Rigor:** Full paired McNemar significance tests with Edwards' continuity correction ($\chi^2$) and 95% Wilson score confidence intervals on all metrics across $N = 4{,}560$ test generations.
* **Core Discovery:** Model scaling from 1.7B to 4B parameters unlocks emergent selective abstention under noisy retrieval ($\chi^2 = 51.191, p = 8.38 \times 10^{-13}$), slashing hallucination from **37.5%** to **3.3%** with **92.8% abstention** and **53.8% selective accuracy**.
* **Linguistic Asymmetry:** Demonstrates that informal Latin transliteration (Banglish) slashes dense retriever recall by $55\%$ ($66.7\% \rightarrow 30.0\%$) and induces significant factual degradation ($\chi^2 \approx 26.8, p < 10^{-6}$).
* **Methodological Contribution:** Empirically demonstrates the failure of zero-shot LLM-as-a-judge evaluators in low-resource Bengali ($\kappa \le 0.34$), establishing the imperative for deterministic gold-evidence verification.
