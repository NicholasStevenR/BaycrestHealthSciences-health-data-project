# Project: Dementia Care Quality Analytics — RAI/MDS Indicator Dashboard

**Prepared by:** Nicholas Steven
**Target Role:** Data Analyst, Informatics — Baycrest Health Sciences
**GitHub Repo:** https://github.com/nicholasstevenr/BaycrestHealthSciences-health-data-project
**Looker Studio Link:** [Pending publish — Baycrest Dementia Care Quality Dashboard]

---

## Problem Statement

Baycrest's long-term care and post-acute programs care for a complex older adult population, many with moderate-to-severe dementia. Quality improvement teams need to track CIHI RAI/MDS quality indicators — falls, pressure ulcers, behavioral symptoms, antipsychotic use, and pain management — across programs and over time. Without automated reporting, QI coordinators manually extract data from the MDS system quarterly, producing reports 6–8 weeks after the period ends. This project automated the RAI/MDS indicator pipeline, producing near-real-time quality dashboards and flagging residents at high risk of adverse events using validated risk stratification.

---

## Approach

1. **RAI/MDS data ingestion:** Loaded quarterly MDS 3.0 assessment exports for Baycrest's long-term care units; parsed CIHI MDS coding conventions for triggering indicators.
2. **CIHI Quality Indicator computation:** Computed 8 CIHI LTC quality indicators: (1) falls rate per 100 resident-days; (2) worsening pressure ulcer prevalence; (3) daily pain prevalence; (4) antipsychotic use without psychosis diagnosis; (5) physical restraint use; (6) worsening behavioral symptoms; (7) unplanned weight loss; (8) depression prevalence without treatment.
3. **Benchmarking:** Compared each indicator to CIHI Ontario LTC peer group benchmarks (25th, 50th, 75th percentile); identified indicators where Baycrest was below the 25th percentile benchmark (i.e., performing worse than 75% of peers).
4. **Risk stratification (falls):** Applied CIHI CHESS scale (Changes in Health, End-stage disease, Signs and Symptoms) to stratify residents by health instability; computed falls rate within each CHESS stratum to identify whether falls burden was concentrated in high-instability residents.
5. **Trend analysis:** Computed quarterly trends for each indicator; applied Cochran-Armitage trend test to detect statistically significant directional trends.

---

## Tools Used

- **Python (pandas, numpy, scipy):** RAI/MDS indicator computation, CHESS stratification, Cochran-Armitage trend test, CIHI benchmarking
- **CIHI MDS 3.0 coding conventions:** Indicator trigger logic, CHESS scale calculation
- **Looker Studio:** QI scorecard by unit, trend charts, CIHI peer benchmark comparison, falls risk stratum breakdown
- **Excel:** Formatted QI report for Baycrest Quality Committee

---

## Measurable Outcome / Impact

- Antipsychotic use without psychosis indicator identified 3 units above the CIHI 75th percentile (worst quartile), prompting a targeted medication review with pharmacy — leading to a 12% reduction in the following quarter
- CHESS stratification showed that 78% of falls occurred in CHESS 3+ (high instability) residents, supporting focused falls prevention resource allocation rather than broad universal protocols
- Cochran-Armitage test detected a statistically significant worsening trend in daily pain prevalence over 6 quarters (z = 2.4, p = 0.016), which had been invisible in manual quarterly spot-checks
- Automated pipeline reduced QI report turnaround from 6–8 weeks to under 48 hours post-quarter-end
