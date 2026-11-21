# TACL Guidelines, Editorial Policies, and Formatting Reference

## 1. Official Documentation & Retrieval Metadata
- **Journal:** Transactions of the Association for Computational Linguistics (TACL)
- **Publisher:** Association for Computational Linguistics (ACL) & MIT Press
- **Official URL:** `https://transacl.org/index.php/tacl/about/submissions`
- **Retrieval Date:** November 2026
- **Template Reference:** `tacl2021v1.sty` (ACL two-column A4 standard)
- **Review System:** Rolling monthly submissions (1st of every calendar month), double-blind peer review.

---

## 2. Core Submission Policies & Length Restrictions

| Dimension | TACL Requirement | Matibhrom Compliance Plan |
| :--- | :--- | :--- |
| **Page Limit (Main Content)** | **7 to 10 pages** of main body text, figures, and tables (excluding references and appendices). | Target $\approx 9.5$ pages of high-density main content. |
| **References** | **Unlimited** pages. Must use standard ACL Natbib citation format (`\citep`, `\citet`). | Complete BibTeX database with 29+ verified entries in `paper/references.bib`. |
| **Appendices Policy** | Regulated appendices: up to **5 pages** for technical/reproducibility details, proofs, pseudocode, and prompts; up to **3 pages** for supplementary tables/results. | Technical appendices covering Prompt Templates (Appendix A), Datasheet (Appendix B), Hyperparameters & Compute (Appendix C), and Codebook Guidelines (Appendix D). |
| **Double-Blind Anonymization** | Must not disclose author names, affiliations, lab names, funding sources, or identifiable repository URLs in submission mode. | `\author{\textbf{Anonymous TACL Submission}}` enabled in `paper/main.tex`. All links point to generic repositories or anonymous archives upon review. |
| **Format & Typography** | A4 paper format, two-column layout, 11pt Times Roman typeface, 2.0\,cm side margins, single-spaced. | Handled via `main.tex` geometry and `times` / `TeX Gyre Termes` fontspec. |
| **Dual Presentation Option** | Accepted TACL papers are eligible for oral/poster presentation at an upcoming major ACL conference (ACL, EMNLP, NAACL, EACL). | Research framed with top-tier conference impact and journal depth. |

---

## 3. Structural Conventions of Exemplar Published TACL Papers

To align Matibhrom with prevailing TACL publication conventions, we analyzed four benchmark and RAG papers published in TACL:

### 1. Park & Lee (TACL 2024, Vol. 12) — *Toward Robust RALMs*
- **Problem Formulation:** Dissects imperfect retrieval into unanswerable, adversarial, and conflicting documents.
- **Mathematical Presentation:** Concise display formulas with clear variable scoping. Wide equations are neatly factored into separate definitions rather than single massive fractions.
- **Structural Style:** Minimal bullet points; argumentative paragraphs with italicized topic sentences.
- **Takeaway for Matibhrom:** Model our 4 conditions ($C_0\text{--}C_3$) with compact operator notation and transition smoothly into empirical findings.

### 2. Katsis et al. (TACL 2025, Vol. 13) — *mtRAG*
- **Benchmark Architecture:** Clear multi-turn pipeline diagram detailing dataset curation, retrieval augmentation, and evaluation.
- **Appendix Standard:** Dedicates extensive appendices to verbatim prompt templates, user persona definitions, and full annotation rubrics.
- **Takeaway for Matibhrom:** Include full verbatim Bengali and Banglish prompts in Appendix A.

### 3. Goyal et al. (TACL 2022, Vol. 10) — *FLORES-101*
- **Multilingual Evaluation:** Explicitly reports subword fragmentation ratios, sentence length statistics across language families, and translation verification protocols.
- **Takeaway for Matibhrom:** Detail Bengali consonant conjunct (`যুক্তাক্ষর`) and vowel diacritic (`কার`) fragmentation ratios ($0.51\text{--}0.88$) in the main prose.

### 4. Clark et al. (TACL 2020, Vol. 8) — *TyDi QA*
- **Document Isolation & Leakage:** Proves that train, dev, and test sets share zero source documents, eliminating contamination.
- **Takeaway for Matibhrom:** Highlight our group-key passage-isolation protocol across the 1,800-passage corpus.

---

## 4. TACL Layout & Formatting Checklist

- [x] **Document Class:** `\documentclass[11pt,a4paper,twocolumn]{article}`
- [x] **Geometry:** Top/Bottom: 2.2\,cm, Left/Right: 2.0\,cm, Column separation: 0.6\,cm.
- [x] **Typography:** Times Roman primary font, Microtype enabled.
- [x] **Two-Column Column Width:** $\approx 3.2$\,in ($\approx 8.2$\,cm). All equations must not exceed this width or must be broken across multiple lines.
- [x] **Tables:** Professional `booktabs` (`\toprule`, `\midrule`, `\bottomrule`), no vertical bars (`|`), numbers formatted with consistent precision and aligned decimal points.
- [x] **Figures:** Vector or high-resolution ($\ge 300$\,DPI) raster graphics, readable fonts at actual printed size, complete captions explaining all sub-elements.
- [x] **Anonymity:** No mentions of "Team Turtlers", "ELITE Research Lab", or author names in text or metadata.
- [x] **Ethics & Limitations:** Dedicated sections addressing societal risks, dual-use implications, and research boundaries.
- [x] **Appendices:** Formal `\appendix` section starting after `\bibliography`, adhering to TACL content scope.
