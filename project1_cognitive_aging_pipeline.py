"""
Cognitive Aging Research Data Pipeline — Baycrest / Rotman Research Institute
Author: Nicholas Steven
Target Role: Data Analyst, Informatics — Baycrest Health Sciences
Repo: github.com/nicholasstevenr/BaycrestHealthSciences-health-data-project

Multi-wave harmonization, completeness matrix, composite scores,
practice effects (RM-ANOVA), and dropout analysis.
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")

STUDY_WAVES = ["baseline", "wave2_18mo", "wave3_36mo", "wave4_60mo"]

COGNITIVE_DOMAINS = {
    "episodic_memory":    ["rey_avlt_total", "cvlt_total_trials"],
    "executive_function": ["tmt_b_time",     "digit_span_backward"],
    "processing_speed":   ["digit_symbol",   "tmt_a_time"],
}

# Tests where higher = better vs. lower = better (for z-score direction)
LOWER_IS_BETTER = {"tmt_b_time", "tmt_a_time"}

MIN_WAVES_FOR_ANALYSIS = 2


# ── Load ──────────────────────────────────────────────────────────────────────

def load_waves(data_dir: str) -> dict:
    """Load one CSV per wave from REDCap exports."""
    import os
    waves = {}
    for wave in STUDY_WAVES:
        path = os.path.join(data_dir, f"{wave}_redcap_export.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["wave"] = wave
            waves[wave] = df
            print(f"  {wave}: {len(df):,} participants")
        else:
            # Demo: generate synthetic wave data
            waves[wave] = _synthetic_wave(wave)
    return waves


def _synthetic_wave(wave: str, n: int = 200) -> pd.DataFrame:
    np.random.seed(hash(wave) % 2**31)
    participant_ids = [f"P{i:04d}" for i in range(1, n+1)]
    df = pd.DataFrame({"participant_id": participant_ids, "wave": wave})
    all_tests = [t for tests in COGNITIVE_DOMAINS.values() for t in tests]
    for test in all_tests:
        scores = np.random.normal(50, 10, n)
        # Introduce ~15% missing
        missing_idx = np.random.choice(n, int(n * 0.15), replace=False)
        scores[missing_idx] = np.nan
        df[test] = scores.round(1)
    df["age_at_wave"]    = np.random.normal(72, 8, n).clip(55, 95).round(0)
    df["group"]          = np.random.choice(["healthy_control","MCI","SCD"], n, p=[0.5,0.3,0.2])
    df["protocol_deviation"] = np.random.choice([False, True], n, p=[0.9, 0.1])
    return df


# ── 1. Instrument Harmonization ───────────────────────────────────────────────

def harmonize_instruments(waves: dict) -> pd.DataFrame:
    """
    Combine all waves into long format; apply CVLT-II → CVLT-3 conversion if needed.
    Flag protocol deviations.
    """
    dfs = []
    for wave_name, df in waves.items():
        df = df.copy()
        # CVLT version conversion placeholder (wave4 uses CVLT-3, earlier waves CVLT-II)
        if wave_name == "wave4_60mo" and "cvlt_total_trials" in df.columns:
            # Published conversion: CVLT-3 = CVLT-II * 0.96 + 1.2 (illustrative)
            df["cvlt_total_trials"] = (df["cvlt_total_trials"] * 0.96 + 1.2).round(1)
            df["cvlt_version_flag"] = "CVLT-3_converted"
        dfs.append(df)
    combined = pd.concat(dfs, ignore_index=True)
    all_tests = [t for tests in COGNITIVE_DOMAINS.values() for t in tests]
    combined["n_tests_present"] = combined[
        [t for t in all_tests if t in combined.columns]
    ].notna().sum(axis=1)
    print(f"\n── Harmonized dataset: {len(combined):,} records across {combined['wave'].nunique()} waves ──")
    return combined


# ── 2. Completeness Matrix ────────────────────────────────────────────────────

def completeness_matrix(combined: pd.DataFrame) -> pd.DataFrame:
    """Participant × wave completeness; flag analysis-ready participants."""
    all_tests = [t for tests in COGNITIVE_DOMAINS.values() for t in tests]
    available_tests = [t for t in all_tests if t in combined.columns]

    def _complete(grp):
        return (grp[available_tests].notna().all(axis=1) &
                ~grp.get("protocol_deviation", pd.Series(False)).fillna(False)).any()

    wave_complete = (
        combined.groupby(["participant_id","wave"])
        .apply(_complete)
        .unstack(fill_value=False)
        .reset_index()
    )
    wave_complete["n_complete_waves"] = wave_complete[STUDY_WAVES].sum(axis=1, numeric_only=True)
    wave_complete["analysis_ready"]   = wave_complete["n_complete_waves"] >= MIN_WAVES_FOR_ANALYSIS

    n_ready = wave_complete["analysis_ready"].sum()
    n_total = len(wave_complete)
    print(f"\n── Completeness: {n_ready}/{n_total} participants analysis-ready (≥{MIN_WAVES_FOR_ANALYSIS} waves) ──")
    return wave_complete


# ── 3. Composite Score Computation ───────────────────────────────────────────

def compute_composites(combined: pd.DataFrame) -> pd.DataFrame:
    """Z-score each test within wave, average within domain."""
    combined = combined.copy()
    all_tests = [t for tests in COGNITIVE_DOMAINS.values() for t in tests]

    for test in all_tests:
        if test not in combined.columns:
            continue
        # Z-score within wave; flip sign for lower-is-better tests
        combined[f"z_{test}"] = combined.groupby("wave")[test].transform(
            lambda x: (x - x.mean()) / x.std()
        )
        if test in LOWER_IS_BETTER:
            combined[f"z_{test}"] *= -1

    for domain, tests in COGNITIVE_DOMAINS.items():
        z_cols = [f"z_{t}" for t in tests if f"z_{t}" in combined.columns]
        if z_cols:
            combined[f"composite_{domain}"] = combined[z_cols].mean(axis=1).round(3)

    return combined


# ── 4. Practice Effects (Repeated-Measures ANOVA) ────────────────────────────

def practice_effects(combined: pd.DataFrame) -> pd.DataFrame:
    """Test for significant practice effects in healthy controls using F-test (one-way ANOVA across waves)."""
    controls = combined[combined["group"] == "healthy_control"]
    results = []
    for domain, tests in COGNITIVE_DOMAINS.items():
        z_col = f"composite_{domain}"
        if z_col not in controls.columns:
            continue
        wave_groups = [controls[controls["wave"] == w][z_col].dropna().values
                       for w in STUDY_WAVES]
        wave_groups = [g for g in wave_groups if len(g) >= 10]
        if len(wave_groups) < 3:
            continue
        f, p = stats.f_oneway(*wave_groups)
        results.append({"domain": domain, "f_stat": round(f, 3),
                         "p_value": round(p, 4),
                         "practice_effect_flag": p < 0.05})
    df = pd.DataFrame(results)
    print(f"\n── Practice Effects (healthy controls) ──")
    print(df.to_string(index=False))
    return df


# ── 5. Dropout Analysis ───────────────────────────────────────────────────────

def dropout_analysis(combined: pd.DataFrame) -> dict:
    """Logistic regression: dropout by wave 3 ~ baseline cognitive + demographics."""
    baseline = combined[combined["wave"] == "baseline"].copy()
    wave3_ids = set(combined[combined["wave"] == "wave3_36mo"]["participant_id"])
    baseline["dropped_out_wave3"] = (~baseline["participant_id"].isin(wave3_ids)).astype(int)

    feature_cols = [c for c in ["age_at_wave","composite_episodic_memory","composite_executive_function"]
                    if c in baseline.columns]
    model_df = baseline[feature_cols + ["dropped_out_wave3"]].dropna()
    if len(model_df) < 30:
        return {"error": "Insufficient data"}

    X = StandardScaler().fit_transform(model_df[feature_cols].values)
    y = model_df["dropped_out_wave3"].values
    lr = LogisticRegression(max_iter=300, random_state=42)
    lr.fit(X, y)
    coef_df = pd.DataFrame({
        "feature":    feature_cols,
        "odds_ratio": np.exp(lr.coef_[0]).round(3),
    }).sort_values("odds_ratio", ascending=False)
    dropout_rate = model_df["dropped_out_wave3"].mean() * 100
    print(f"\n── Dropout by Wave 3: {dropout_rate:.1f}% ──")
    print(coef_df.to_string(index=False))
    return {"dropout_rate_pct": round(dropout_rate, 1), "predictors": coef_df}


# ── Export ────────────────────────────────────────────────────────────────────

def export_all(results: dict, outdir: str = "output") -> None:
    import os; os.makedirs(outdir, exist_ok=True)
    for name, obj in results.items():
        if isinstance(obj, pd.DataFrame) and len(obj):
            obj.to_csv(f"{outdir}/{name}.csv", index=False)
            print(f"  Exported → output/{name}.csv")


if __name__ == "__main__":
    waves    = load_waves("data/redcap_exports/")
    combined = harmonize_instruments(waves)
    comp_mat = completeness_matrix(combined)
    combined = compute_composites(combined)
    prac_df  = practice_effects(combined)
    drop_res = dropout_analysis(combined)

    export_all({"combined_harmonized": combined, "completeness_matrix": comp_mat,
                "practice_effects": prac_df})
    if isinstance(drop_res.get("predictors"), pd.DataFrame):
        drop_res["predictors"].to_csv("output/dropout_predictors.csv", index=False)
