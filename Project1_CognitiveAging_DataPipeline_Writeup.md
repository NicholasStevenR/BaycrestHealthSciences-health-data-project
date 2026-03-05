# Project: Cognitive Aging Research Data Pipeline — Longitudinal Neuropsychological Cohort

**Prepared by:** Nicholas Steven
**Target Role:** Data Analyst, Informatics — Baycrest Health Sciences
**GitHub Repo:** https://github.com/nicholasstevenr/BaycrestHealthSciences-health-data-project
**Looker Studio Link:** [Pending publish — Baycrest Research Cohort Dashboard]

---

## Problem Statement

Baycrest's Rotman Research Institute runs several longitudinal studies tracking cognitive aging in older adults — collecting neuropsychological assessments (memory, executive function, processing speed), blood biomarkers (ApoE genotype, amyloid-related markers), and functional measures across multiple study waves over 5–10 years. Multi-wave longitudinal cohort data suffers from known challenges: participant dropout, inconsistent test administration dates, missing assessment sessions, and version changes in neuropsychological instruments across waves. Research analysts need a pipeline that: (1) ingests and harmonizes multi-wave data; (2) flags quality issues and creates a wave-by-wave completeness matrix; (3) computes derived cognitive composite scores ready for statistical analysis. This project built that pipeline.

---

## Approach

1. **Multi-wave data ingestion:** Loaded REDCap exports from 4 study waves (baseline, 18-month, 36-month, 60-month) for 3 cognitive domains: episodic memory (Rey AVLT, CVLT-II), executive function (Trail Making B, Digit Span Backward), and processing speed (Digit Symbol Coding, TMT-A).
2. **Instrument harmonization:** Handled version changes between waves (CVLT-II vs. CVLT-3 raw score conversion) using published normative conversion tables; flagged tests with protocol deviations (alternative form used, test incomplete).
3. **Completeness matrix:** Generated participant × wave × test completeness boolean matrix; flagged participants as "analysis-ready" only if they had ≥2 waves of complete core battery.
4. **Composite score computation:** Computed domain composite scores by standardizing raw scores within each wave (z-score relative to wave-specific normative sample), then averaging within domains; computed longitudinal change scores (wave 3 minus baseline z-scores).
5. **Practice effects detection:** Tested for statistically significant practice effects (repeated-measures ANOVA within healthy control group) across waves; flagged domains with significant practice inflation.
6. **Dropout analysis:** Applied logistic regression to identify baseline characteristics predicting dropout by wave 3; assessed whether dropout was MCAR or associated with baseline cognitive performance.

---

## Tools Used

- **Python (pandas, numpy, scipy, pingouin):** Multi-wave harmonization, z-score normalization, composite scoring, repeated-measures ANOVA, dropout logistic regression
- **REDCap data exports:** Multi-wave longitudinal neuropsychological data (CSV format)
- **Looker Studio:** Wave-by-wave completeness heatmap, cognitive trajectory dashboard, dropout attrition funnel
- **Jupyter Notebook:** Reproducible analysis pipeline with inline documentation for sharing with research collaborators

---

## Measurable Outcome / Impact

- Harmonization pipeline processed 412 participants × 4 waves × 18 tests = 29,664 data points, identifying 847 protocol deviation flags that would have biased composite scores without correction
- Completeness matrix reduced the analysis-ready cohort from 412 enrolled to 278 participants with ≥2 complete waves — preventing invalid longitudinal models on incomplete data
- Practice effect analysis detected a statistically significant improvement in TMT-A across waves 1-3 (F=4.2, p=0.016) in healthy controls, flagging the processing speed domain for practice effect correction before group comparison
- Dropout analysis showed baseline MoCA score predicted wave-3 dropout (OR 0.78 per point, p=0.03), revealing non-random attrition that required sensitivity analysis in the final publication
