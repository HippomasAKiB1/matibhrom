# Matibhrom TACL Manuscript: Baseline Audit Report

## 1. Executive Summary of Audit
This forensic baseline audit inspects the current state of the Matibhrom manuscript (`paper/main.tex`, `paper/main_modular.tex`, `paper/sections/`, `paper/tables/`, `paper/figures/`) against raw experimental artifacts (`outputs/test_publication_reports/`), official TACL submission guidelines, and supervisor feedback.

The audit confirms:
- **Core Research & Empirical Validity:** The experimental foundation is strong ($N = 4{,}560$ test-split generations across Qwen 2.5 1.7B and Gemma 3 4B, 4 evidence conditions, 2 registers, 3 domains, paired McNemar $\chi^2$ significance tests, and deterministic gold adjudication). All reported metrics match raw adjudication logs.
- **Structural & Stylistic Deficiencies:** The manuscript currently exhibits pervasive fragmentation with **21 list environments** (`enumerate`, `itemize`, numbered `\paragraph`s), primitive vector graphics in Figure 1, multiple wide display equations causing **two-column margin bleed and text/formula overlaps on Page 6**, an unconstrained and misaligned Table 2, fallback placeholder boxes (`\fbox{[Figure: ...]}`), and lack of required technical appendices.

---

## 2. Supervisor Feedback Dissection & Verification

| Supervisor Critique | Location(s) Found | Verified Defect Mechanism | Severity |
| :--- | :--- | :--- | :---: |
| **1. "Using too much bullet points and numberings. Keep them separate para... Way too much bullets."** | `00_abstract.tex` (L3), `01_introduction.tex` (L7, L15, L24), `03_matibhrom_benchmark.tex` (L6, L20, L29, L37), `04_methodology.tex` (L85, L91, L97, L103), `05_results.tex` (L63, L68), `06_error_taxonomy.tex` (L33, L46, L64), `07_eval_reliability.tex` (L33), `08_discussion.tex` (L6, L14), `09_conclusion.tex` (L7). | 21 distinct list blocks. Sections read like bulleted slide outlines or technical briefs rather than cohesive, flowing academic discourse. | **Major** |
| **2. "Figure 1 looks very poorly designed."** | `paper/sections/04_methodology_and_framework.tex` (L35--L75), `main.tex` (L300--L345). | Primitive TikZ boxes with basic rounded corners and pastel fills (`blue!5`, `teal!5`, `purple!5`). Clunky arrow routing with doglegs and crossing lines. Low informational density. | **Major** |
| **3. "Some overlaps between text and formula, such as in page 6."** | `04_methodology_and_framework.tex` (Eq 8, Eq 9, Eq 10, Eq 11), `05_empirical_results.tex` (Eq 12 on Page 6), `07_evaluation_reliability.tex` (Eq 13). | In a 2-column format (column width $\approx 3.2$\,in / 8\,cm), single-line display equations exceeding 60 characters or featuring wide fractions overlap adjacent text columns or equation numbers. Specifically, Eq 9 (Selective Accuracy, 287 chars) and Eq 12 ($\chi^2_{\text{Qwen vs Gemma (C3)}}$, 95 chars) overflow column width. | **Critical** |
| **4. "The table is not well aligned such as table 2."** | `paper/tables/table2_domain_disparity.tex`, `paper/main.tex`. | Table 2 uses `\begin{tabular}{llrrrr}` with 6 unconstrained columns. Columns bleed into margins. Numbers are presented as raw 3-decimal fractions (`0.625`) while Table 1 uses percentages (`96.5%`). Headers lack vertical hierarchy and text wrapping. | **Major** |
| **5. "Things that are not completed, there are placeholders."** | `paper/main.tex`, `paper/figures/`. | Two `\IfFileExists` calls default to literal `\fbox{\parbox{...}{[Figure: ...]}}` placeholder boxes if image paths fail. Ellipses in verbatim Bengali responses (`...`) omit full generational context. Complete absence of required technical appendices. | **Major** |
| **6. "Please complete the paper before asking review."** | Entire manuscript. | Paper lacks comprehensive technical appendices: verbatim prompt templates for all conditions ($C_0\text{--}C_3$) in both scripts, full annotation codebook rules, compute/environment specifications, and dataset datasheets. | **Major** |

---

## 3. Section-by-Section Forensic Audit

### Section 0: Abstract (`paper/sections/00_abstract.tex`)
- **Current Structure:** 1 opening paragraph followed by an enumerated list `\begin{enumerate} \item \textbf{Linguistic Register...} \dots \end{enumerate}` and a closing paragraph.
- **Defects:** Bulleted abstract violates standard TACL format (abstracts must be a single cohesive paragraph of 150--250 words).
- **Remedy:** Synthesize all 4 bullet points into a continuous, high-density abstract paragraph highlighting motivation, core results, scaling divergence, and evaluation reliability.

### Section 1: Introduction (`paper/sections/01_introduction.tex`)
- **Current Structure:** 3 major enumerated/itemized blocks:
  1. Lines 7--12: `\begin{enumerate}` for 4 Low-Resource Hurdles (Tokenization, Diglossia, Societal Risk, Grounding Dilemma).
  2. Lines 15--21: `\begin{itemize}` for 5 Research Questions (RQ1 to RQ5).
  3. Lines 24--30: `\begin{enumerate}` for 5 Contributions.
- **Defects:** Excessive enumeration disrupts narrative momentum and argumentative flow.
- **Remedy:** Convert the 4 Hurdles into thematic paragraphs with rich narrative transitions. Weave RQs naturally into the formulation of the Matibhrom benchmark. Integrate contributions into a unified, authoritative closing summary paragraph.

### Section 2: Related Work (`paper/sections/02_related_work.tex`)
- **Current Structure:** 4 subsections (Hallucination Benchmarks, Multilingual Disparities, Script Transliteration, RAG Vulnerability).
- **Defects:** Literature references are present, but comparative positioning against contemporary TACL RALM literature (Park & Lee 2024, Katsis et al. 2025) needs deeper narrative engagement.
- **Remedy:** Emphasize how Matibhrom bridges the gap between imperfect retrieval (unanswerable/adversarial scenarios) and typologically distinct, low-resource Brahmic scripts.

### Section 3: Matibhrom Benchmark Design (`paper/sections/03_matibhrom_benchmark.tex`)
- **Current Structure:** Domain descriptions and split allocations are formatted as fragmented lists (`\begin{enumerate}`, `\begin{itemize}`).
- **Defects:** List fatigue; lacks formal mathematical specification of passage provenance and document isolation guarantees.
- **Remedy:** Rewrite into cohesive paragraphs. Formally articulate the group-key document-isolation lemma preventing passage leakage across splits.

### Section 4: Methodology and Evaluation Framework (`paper/sections/04_methodology_and_framework.tex`)
- **Current Structure:** Condition definitions $C_0\text{--}C_3$, TikZ Figure 1, metric definitions with numbered paragraphs (`\paragraph{1. Hallucination Rate...}`), McNemar equation, and Algorithm 1.
- **Defects:**
  - **Figure 1:** Primitive layout, weak visual hierarchy, clunky lines.
  - **Equation 9 (Selective Accuracy):** Fraction numerator and denominator are 287 characters long, overflowing single-column width.
  - **Metric Paragraphs:** Numbered `\paragraph{1. ...}` adds to list clutter.
- **Remedy:**
  - Redesign Figure 1 into an elegant 4-stage pipeline diagram using professional styling.
  - Break Equation 9 using `aligned` or `split` so that numerator and denominator fit cleanly within 3.2 inches.
  - Replace numbered paragraphs with unnumbered, mathematically framed sub-headings.

### Section 5: Empirical Results and Analysis (`paper/sections/05_empirical_results.tex`)
- **Current Structure:** Table 1, analytical paragraphs, Figure 2, Table 3 (McNemar tests), bulleted register analysis, Table 2, Figure 3.
- **Defects:**
  - **Equation 12 (Page 6 Overlap):** `\chi^2_{\text{Qwen vs Gemma (C3)}} = 51.191, \quad p = 8.38 \times 10^{-13} < 0.001 \quad (***)` overflows the column margin and collides with text.
  - **Bulleted Results:** Register degradation and retrieval diagnostics are fragmented into itemized bullets.
  - **Table 2:** Unconstrained column widths, decimals instead of percentages, misaligned headers.
- **Remedy:** Reformat Eq 12; convert bulleted metrics into flowing empirical exposition; overhaul Table 2 with professional booktabs and percentage alignments.

### Section 6: Error Taxonomy & Case Studies (`paper/sections/06_error_taxonomy.tex`)
- **Current Structure:** Table 4 (Error taxonomy codebook), followed by 3 case studies formatted as nested itemized lists (`\item \textbf{Input Prompt...}`, `\item \textbf{Model Response...}`).
- **Defects:** Nested lists make case studies look like raw data dumps rather than qualitative scientific analysis.
- **Remedy:** Transform case studies into structured analytical vignettes with formal blockquotes, word-by-word glosses, and rich linguistic dissection.

### Section 7: Evaluation Reliability (`paper/sections/07_evaluation_reliability.tex`)
- **Current Structure:** LLM-as-a-judge empirical study ($\kappa \le 0.34$), Table 5, 3 enumerated failure modes, and deterministic gold adjudication protocol.
- **Defects:** Enumerated failure modes (L33--37); Equation 13 (`\kappa_{\text{raw}} \in \dots`) spans too wide for single-column width.
- **Remedy:** Format failure modes as coherent diagnostic paragraphs; reformat Eq 13 into compact display notation.

### Section 8: Discussion, Limitations, and Ethics (`paper/sections/08_discussion_limitations.tex`)
- **Current Structure:** Deployment implications (enumerated 1--3), Limitations (enumerated 1--3), Ethics statement.
- **Defects:** Fragmented lists.
- **Remedy:** Convert into cohesive analytical paragraphs addressing sociotechnical risks, low-resource deployment economics, and constitutional boundaries.

### Section 9: Conclusion (`paper/sections/09_conclusion.tex`)
- **Current Structure:** Summary paragraph followed by an enumerated list of 4 key takeaways.
- **Defects:** Enumerated list.
- **Remedy:** Re-write into an authoritative, forward-looking concluding narrative.

### Section 10: Missing Appendices (Critical Incompleteness)
- **Current State:** Completely absent from current manuscript.
- **Defects:** Reviewers and supervisors cannot audit prompt templates, data statements, or complete annotation rules.
- **Remedy:** Create comprehensive technical appendices:
  - **Appendix A:** Verbatim Prompt Specifications for $C_0, C_1, C_2, C_3$ across Standard Bangla and Banglish.
  - **Appendix B:** Benchmark Data Sheet & Corpus Provenance.
  - **Appendix C:** Compute Infrastructure, Hyperparameters, and Model Adapter Specifications.
  - **Appendix D:** Complete Annotation Codebook & Edge Case Guidelines.

---

## 4. Verification of Empirical Data Integrity
Every number reported in `Table 1`, `Table 2`, and throughout the text was cross-checked against `outputs/test_publication_reports/comprehensive_results_summary.md` and raw logs:
- $C_0$ Hallucination: Qwen 96.5% [0.95, 0.98], Gemma 89.4% [0.85, 0.94] — **VERIFIED MATCH**
- $C_1$ Hallucination: Qwen 64.4% [0.61, 0.67], Gemma 60.6% [0.54, 0.68] — **VERIFIED MATCH**
- $C_2$ Hallucination: Qwen 87.5% [0.85, 0.90], Gemma 78.9% [0.73, 0.85] — **VERIFIED MATCH**
- $C_3$ Hallucination: Qwen 37.5% [0.35, 0.41], Gemma 3.3% [0.01, 0.06] — **VERIFIED MATCH**
- Selective Accuracy: Qwen $C_3$ 9.8%, Gemma $C_3$ 53.8% — **VERIFIED MATCH**
- Abstention Rate: Qwen $C_3$ 58.4%, Gemma $C_3$ 92.8% — **VERIFIED MATCH**
- McNemar Tests: $C_2$ vs $C_3$ ($\chi^2 = 444.653$ for Qwen, $134.007$ for Gemma) — **VERIFIED MATCH**
- Cross-Model Significance: $\chi^2 = 51.191, p = 8.38 \times 10^{-13}$ — **VERIFIED MATCH**
- Domain Breakdown (Table 2): Qwen Legal 79.6%, Medical 72.3%, General 62.5%; Gemma Legal 69.6%, Medical 62.5%, General 42.1% — **VERIFIED MATCH**

All numbers are 100% faithful to the actual empirical test split.
