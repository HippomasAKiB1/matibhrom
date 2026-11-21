# Revision Changelog: TACL Manuscript Quality Audit & Overhaul

**Target:** Transactions of the Association for Computational Linguistics (TACL)  
**Date:** November 21, 2026  
**Repository:** [https://github.com/HippomasAKiB1/matibhrom](https://github.com/HippomasAKiB1/matibhrom)  

---

## 1. Summary of Modifications

This changelog records the complete set of structural, typographical, scientific, and formatting modifications applied to the Matibhrom academic manuscript in response to supervisor feedback, TACL publication guidelines, and independent multi-agent peer reviews.

---

## 2. File-by-File Detailed Changelog

### `paper/sections/00_abstract.tex`
- Converted a 4-item bulleted summary into a cohesive, flowing narrative abstract.
- Integrated problem motivation, 4-condition framework, key empirical findings ($N=4,560$), and the scale-dependent emergence of selective abstention ($p < 10^{-12}$).
- Eliminated all list environments.

### `paper/sections/01_introduction.tex`
- Converted four bulleted systemic hurdles into four rich, interconnected academic narrative paragraphs.
- Integrated the five research questions (RQ1--RQ5) directly into continuous prose within the problem statement.
- Restructured the five itemized contributions into an organic scholarly synthesis of empirical, methodological, and infrastructural contributions.
- Removed all `\begin{enumerate}` and `\begin{itemize}` blocks.

### `paper/sections/02_related_work.tex`
- Expanded the discussion on multilingual evaluation and regional disparities (Section 2.2).
- Added an explicit technical explanation (REC-01) for why cross-lingual English-pivot retrieval strategies fail on localized Bangladeshi statutory and clinical domains due to zero representation in English web corpora.
- Cited recent TACL and multilingual benchmarks (\citet{park2024robust}, \citet{katsis2025mtrag}, \citet{goyal2022flores}, \citet{clark2020tydi}, \citet{laban2022summac}).

### `paper/sections/03_matibhrom_benchmark.tex`
- Converted domain taxonomy lists into continuous descriptive prose.
- Restructured the prompt construction and dataset split descriptions from itemized lists into formal, flowing mathematical paragraphs.
- Formalized the document-isolation lemma: $\operatorname{DocGroup}(i) \cap \operatorname{DocGroup}(j) = \emptyset$ for $i \neq j$.

### `paper/sections/04_methodology_and_framework.tex`
- Replaced the primitive Figure 1 diagram with a publication-grade, modern TikZ 4-stage scientific pipeline vector architecture.
- Factored Equation 9 (Selective Accuracy) over the answered query index set $\mathcal{S}_{\text{ans}}$, eliminating wide display equation overflow.
- Clarified the sequential passage concatenation syntax with explicit newline delimiters in Condition $C_2$ (REC-03).
- Added a theoretical justification for using Wilson score confidence intervals over normal (Wald) approximations near extreme proportions ($p \to 0$) (REC-02), citing \citet{wilson1927probable} and \citet{brown2001interval}.
- Converted numbered paragraph headings into natural academic section headers.

### `paper/sections/05_empirical_results.tex`
- Split Equation 12 ($\chi^2_{\text{C3}}$ cross-model scaling test) across multiple lines using `split`, resolving the text/formula overlap on Page 6.
- Converted linguistic register degradation and dense retrieval analysis from bullet points to analytical prose.
- Added a calibrated conservatism discussion (REC-04) analyzing Gemma 3 4B's 92.8% abstention under noisy distractors in Condition $C_3$, highlighting the 4.4-fold selective accuracy increase (53.8%).

### `paper/tables/table1_scaling_comparison.tex` & `table2_domain_disparity.tex`
- Redesigned Table 1 and Table 2 using formal `booktabs` typography (`\toprule`, `\midrule`, `\bottomrule`).
- Table 2 overhauled with explicit column width constraints (`\tabcolsep{3.5pt}`), unified aligned percentage displays, and directional delta indicators ($\downarrow, \uparrow$).
- Aligned all metric headers and eradicated margin bleed.

### `paper/sections/06_error_taxonomy.tex`
- Converted all three case studies from nested bulleted lists into formatted qualitative vignettes.
- Embedded verbatim Bangla prompt queries and model generation outputs, eliminating placeholder ellipses.

### `paper/sections/07_evaluation_reliability.tex`
- Transformed failure modes of automated evaluators into diagnostic paragraphs.
- Preserved Table 5 agreement matrix with standardized `booktabs` formatting.

### `paper/sections/08_discussion_limitations.tex`
- Converted deployment implications (Edge vs. Cloud RAG, Negative Constraint Guardrails) and research limitations into continuous, reflective paragraphs.

### `paper/sections/09_conclusion.tex`
- Replaced a 5-item enumerated conclusion with a forward-looking, comprehensive synthesis.

### `paper/sections/10_appendix.tex`
- Created a comprehensive 4-part technical appendix:
  1. **Appendix A: Verbatim Prompt Templates (Table 6):** Exact prompt structures for Conditions $C_0$--$C_3$.
  2. **Appendix B: Dataset Datasheet & Provenance:** Distribution of items across domains, sources, and document groups.
  3. **Appendix C: Compute Infrastructure & Hyperparameters:** Exact hardware specs, greedy decoding configurations, and batching limits.
  4. **Appendix D: Annotation Codebook & Edge-Case Rubric:** Human adjudication protocols and resolution rules.

### `paper/references.bib`
- Added missing bibliographic entries for \citet{brown2001interval} and \citet{wilson1927probable}.
- Verified all 31 cited entries against standard publication metadata.

### `paper/main_modular.tex` & `paper/main.tex`
- Created unified master documents with dual-engine compilation support (XeLaTeX and pdfLaTeX).
- Integrated `scripts/build_paper_and_qa.py` to compile `main.tex` as a 100% self-contained standalone document.

### `paper/matibhrom_manuscript.zip`
- Repackaged the complete Overleaf bundle (1,079,314 bytes) containing all 28 project assets.

---

## 3. Verification Metrics Summary

- **Total Lists in Main Text:** 0 (down from 21)
- **Placeholders / `\fbox` Remaining:** 0
- **Missing Citations:** 0
- **Undefined Cross-References:** 0
- **Overleaf Build Status:** Ready for XeLaTeX / pdfLaTeX compilation
