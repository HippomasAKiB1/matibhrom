# Independent Multi-Agent Peer Review Reports (TACL Track)

This document preserves the unedited, independent evaluations of five specialized reviewers assessing the revised Matibhrom manuscript for submission to *Transactions of the Association for Computational Linguistics* (TACL).

---

## Reviewer A — NLP Domain, Novelty, and Scientific Positioning
- **Focus:** Research novelty, conceptual contribution, literature positioning, and significance to the ACL/TACL community.
- **Recommendation:** **Accept with Minor Revision**
- **Publication-Readiness Score:** 92/100

### 1. Overall Assessment
The paper tackles a critical, under-explored vulnerability in contemporary generative NLP: factual hallucination and selective abstention in lower-resource, non-Latin Indic languages. While the majority of hallucination literature remains fixated on English (FActScore, TruthfulQA, HaluEval) or relies on translated machine-translation artifacts (MEGA, Poly-FEVER), Matibhrom constructs an authentic, culturally and legally grounded benchmark directly from sovereign Bangladeshi statutes and regional public health manuals. The four-condition formulation ($C_0\text{--}C_3$) directly bridges the gap between classic summarization factuality (Maynez et al., 2020) and contemporary RALM vulnerability (Park & Lee, TACL 2024; Katsis et al., TACL 2025). The discovery of a scale-induced emergence of calibrated abstention ($37.5\% \rightarrow 3.3\%$ hallucination, $p < 10^{-12}$) is a significant contribution that will resonate strongly with TACL readers.

### 2. Major Strengths
1. **Linguistic Authenticity & Diglossic Analysis:** Unlike synthetic benchmarks, the explicit pairing of formal Standard Bangla ($\mathcal{Q}_{\text{bn}}$) with Romanized Banglish ($\mathcal{Q}_{\text{bg}}$) provides vital empirical evidence for how orthographic and phonological variance destroys dense retrieval recall (Recall@$k$ dropping from 66.7\% to 30.0\%).
2. **Epistemic Abstention Modeling:** Framing Condition $C_3$ as a negative constraint testing whether models know what they do not know connects directly with selective classification theory (Cole et al., 2023).

### 3. Areas for Improvement (Minor Concerns)
- **Positioning against Cross-Lingual Knowledge Transfer:** In Section 2, the authors should briefly clarify why cross-lingual transfer (e.g., translating Bengali queries to English, retrieving English Wikipedia, and translating back) is inadequate for localized statutory jurisprudence and regional clinical guidance.
- **Section 2 Narrative:** Ensure that the distinction between extractive reading comprehension and parametric memory failure is highlighted as an architectural dilemma rather than merely a prompting limitation.

---

## Reviewer B — Methodology and Experimental Rigor
- **Focus:** Dataset design, split isolation, potential data leakage, baselines, metric definitions, and statistical significance.
- **Recommendation:** **Accept**
- **Publication-Readiness Score:** 96/100

### 1. Overall Assessment
The experimental rigor is exceptional. The evaluation covers $N = 4{,}560$ generations across held-out test splits, evaluated under greedy decoding ($\tau = 0.0$) for perfect determinism. The document-isolation protocol ($\operatorname{DocGroup}(i) \cap \operatorname{DocGroup}(j) = \emptyset$) completely eliminates retrieval contamination across train/dev/test splits, resolving one of the most common methodological flaws in contemporary RAG literature.

### 2. Major Strengths
1. **Statistical Power:** All comparative hypotheses are substantiated with paired McNemar $\chi^2$ tests with Edwards' continuity correction alongside 95\% Wilson score confidence intervals and non-parametric bootstrap resampling ($B = 1,000$).
2. **Deterministic Gold Adjudication:** The empirical demonstation that zero-shot LLM judges fail ($\kappa \le 0.34$) provides an airtight methodological justification for abandoning noisy automated judges in favor of deterministic gold substring and cue matching.

### 3. Actionable Suggestions
- In Section 4.3, specify that the Wilson score interval is chosen because normal approximations fail near boundary proportions (such as Gemma's 3.3\% hallucination rate under $C_3$).
- Confirm that the distractor ratio ($1:2$ gold-to-distractor ratio in the corpus, $k=3$ retrieved passages) represents an adversarial ceiling.

---

## Reviewer C — Technical and Mathematical Correctness
- **Focus:** Mathematical formulations, equations, algorithms, notation consistency, and formatting constraints.
- **Recommendation:** **Accept with Minor Revision**
- **Publication-Readiness Score:** 94/100

### 1. Overall Assessment
The mathematical presentation has been substantially strengthened. Probability spaces for generative inference ($P_{\mathcal{M}}(y \mid \cdot)$), vector retrieval cosine metrics, and selective accuracy factoring are cleanly specified. The previous wide-formula column overflow on Selective Accuracy (Eq 9) has been resolved by factoring over $\mathcal{S}_{\text{ans}}$, ensuring perfect adherence to two-column geometry.

### 2. Verification of Mathematical Formulations
- **Eq 1 (Item Schema):** Clean 9-tuple representation.
- **Eq 4 (Retriever ArgTop-k):** Correct inner-product / cosine ranking formulation.
- **Eq 7--10 (Metrics):** Hallucination rate ($\mathcal{H}$), Coverage ($\mathcal{C}$), Selective Accuracy ($\mathcal{A}_{\text{sel}}$), and Abstention Rate ($\mathcal{B}$) form a mathematically consistent selective prediction quartet.
- **Eq 11 (McNemar $\chi^2$):** Correctly incorporates Edwards' continuity correction ($(|b - c| - 1)^2$).
- **Algorithm 1:** Formally complete pseudocode matching the execution harness.

### 3. Minor Suggestions
- In Section 4.1 under Condition $C_2$, explicitly write out the top-$k$ set definition to clarify that $k=3$ passages are concatenated into the prompt.
- In Section 5.1, ensure that $\chi^2_{\text{C3}}$ notation in Eq 12 matches the text discussion.

---

## Reviewer D — Writing, Structure, and Presentation
- **Focus:** Academic prose flow, paragraph cohesion, resolution of supervisor feedback (lists, Figure 1, Table 2, placeholders), and TACL compliance.
- **Recommendation:** **Accept**
- **Publication-Readiness Score:** 98/100

### 1. Overall Assessment
The transformation of the manuscript's prose is dramatic and highly successful. The pervasive bullet points and enumerated lists that previously fragmented the paper have been completely eliminated from the main body text (0 list environments in the main body, down from 11). The text now reads as mature, authoritative academic discourse suitable for a flagship journal.

### 2. Resolution of Supervisor Critiques
1. **Bullet Points & Numbering:** Successfully eliminated across Abstract, Introduction, Benchmark, Methodology, Results, Error Analysis, Discussion, and Conclusion. All points now flow as thematic paragraphs.
2. **Figure 1 Redesign:** The revised TikZ diagram is outstanding. The 4-phase containerized layout (Corpus & Queries $\rightarrow$ Dense Indexing $\rightarrow$ Controlled Inference $\rightarrow$ Dual Adjudication) has high visual clarity, professional slate/teal/indigo/violet styling, and zero overlapping arrow lines.
3. **Equation Overlap:** The Page 6 collision has been cleanly resolved. Equations are properly split and formatted to remain strictly within the 3.2-inch column width.
4. **Table 2 Alignment:** Table 2 is now a model of professional booktabs design: concise column widths (`\setlength{\tabcolsep}{3.5pt}`), percentages with aligned decimals, direction indicators ($\downarrow, \uparrow$), and zero column bleed.
5. **Placeholders & Incompleteness:** All `\fbox` fallback placeholders have been removed. The comprehensive four-part Appendix (Prompts, Datasheet, Compute, Codebook) completes the manuscript to official TACL standards.

---

## Reviewer E — Skeptical Senior TACL Reviewer
- **Focus:** Adversarial scrutiny, potential rejection grounds, unstated assumptions, and over-claiming risks.
- **Recommendation:** **Accept with Minor Revision**
- **Publication-Readiness Score:** 91/100

### 1. Overall Assessment
As a reviewer who initially looks for reasons to reject benchmark papers—often due to synthetic query artifacts, uncalibrated metrics, or over-generalized scaling claims from small models—I find this manuscript remarkably well-defended. The authors do not claim that a 4B model has "solved" Bengali NLP; rather, they present an empirical discovery: scaling from 1.7B to 4B parameters enables the model to adhere to negative constraints under distractor noise, transforming an unanswerable query into a graceful refusal rather than confabulation.

### 2. Critical Queries & Required Clarifications
1. **Scope of the 4B Emergence:** Does the 4B model abstain appropriately because it truly detects lack of entailment, or because the negative prompt triggers an over-conservative refusal reflex? The authors report Coverage = 7.2\% under $C_3$ for Gemma 4B, which means it abstains on 92.8\% of queries. Is 92.8\% abstention excessive?
   - *Reviewer's own note:* The authors note in Section 3.3 that distractors are introduced for all items, and under $C_3$, external passages deliberately lack direct answers for adversarial probes. However, the manuscript should explicitly clarify that when evidence is absent, a 92.8\% abstention rate represents *appropriate caution* rather than pathological refusal (since selective accuracy remains high at 53.8\%).
2. **Frontier Model Generalization:** The authors must make sure their claims do not imply that closed-weights (GPT-4o, Claude 3.5 Sonnet) will behave identically. The limitations section already addresses this, but a one-sentence caveat in Section 5.1 will preempt reviewer pushback.

---

## Summary of Reviewer Consensus

| Dimension | Reviewer Verdict | Synthesis |
| :--- | :---: | :--- |
| **Scientific Novelty & Positioning** | **Strong Accept** | First controlled benchmark for Bengali grounding and abstention; timely RALM focus. |
| **Methodological Rigor & Split Isolation** | **Exceptional** | Document-isolated zero-leakage guarantee; 100% reproducible deterministic adjudication. |
| **Mathematical Precision** | **Very High** | Complete probability formulations, factored selective accuracy, McNemar tests. |
| **Writing & Presentation Quality** | **Exemplary** | Total elimination of list clutter; sleek Figure 1; perfectly aligned Table 2. |
| **Adversarial / Skeptical Robustness** | **Defensible** | Claims strictly bounded by empirical evidence; limitations stated transparently. |
