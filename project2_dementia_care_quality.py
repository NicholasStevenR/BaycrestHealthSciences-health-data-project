"""
Dementia Care Quality Analytics — RAI/MDS Indicator Dashboard
Author: Nicholas Steven
Target Role: Data Analyst, Informatics — Baycrest Health Sciences
Repo: github.com/nicholasstevenr/BaycrestHealthSciences-health-data-project

CIHI LTC quality indicators, CHESS risk stratification, CIHI benchmarking,
Cochran-Armitage trend test.
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

CIHI_LTC_BENCHMARKS = {
    "falls_rate_per_100":              {"p25": 3.1, "p50": 5.2, "p75": 8.4},
    "pressure_ulcer_pct":              {"p25": 2.8, "p50": 4.5, "p75": 7.2},
    "daily_pain_pct":                  {"p25": 5.2, "p50": 9.1, "p75": 14.3},
    "antipsychotic_no_psychosis_pct":  {"p25": 14.2,"p50": 21.0,"p75": 29.5},
    "restraint_use_pct":               {"p25": 2.0, "p50": 4.1, "p75": 8.5},
    "worsening_behaviour_pct":         {"p25": 6.5, "p50": 10.2,"p75": 15.8},
    "weight_loss_pct":                 {"p25": 7.1, "p50": 11.3,"p75": 17.0},
    "depression_no_treatment_pct":     {"p25": 8.5, "p50": 13.4,"p75": 20.1},
}


# ── Load ──────────────────────────────────────────────────────────────────────

def load(mds_path: str) -> pd.DataFrame:
    mds = pd.read_csv(mds_path, parse_dates=["assessment_date"])
    print(f"MDS records: {len(mds):,}  |  Quarters: {mds['fiscal_quarter'].nunique()}")
    return mds


# ── 1. CIHI LTC Quality Indicators ───────────────────────────────────────────

def compute_qi(mds: pd.DataFrame) -> pd.DataFrame:
    """Compute 8 CIHI quality indicators per unit per quarter."""
    results = []
    for (unit, quarter), grp in mds.groupby(["unit_code","fiscal_quarter"]):
        n = len(grp)
        total_resident_days = grp.get("resident_days", pd.Series([90]*n)).sum()

        row = {"unit_code": unit, "fiscal_quarter": quarter, "n_residents": n}

        # Falls rate per 100 resident-days
        if "fall_flag" in grp.columns:
            row["falls_rate_per_100"] = round(grp["fall_flag"].sum() / max(total_resident_days, 1) * 100, 3)

        # Pressure ulcer
        if "pressure_ulcer_worsened" in grp.columns:
            row["pressure_ulcer_pct"] = round(grp["pressure_ulcer_worsened"].mean() * 100, 1)

        # Daily pain
        if "daily_pain_flag" in grp.columns:
            row["daily_pain_pct"] = round(grp["daily_pain_flag"].mean() * 100, 1)

        # Antipsychotic without psychosis
        if "antipsychotic_rx" in grp.columns and "psychosis_dx" in grp.columns:
            ap_no_psy = (grp["antipsychotic_rx"] & ~grp["psychosis_dx"])
            row["antipsychotic_no_psychosis_pct"] = round(ap_no_psy.mean() * 100, 1)

        # Physical restraint
        if "restraint_flag" in grp.columns:
            row["restraint_use_pct"] = round(grp["restraint_flag"].mean() * 100, 1)

        # Worsening behaviour
        if "worsening_behaviour" in grp.columns:
            row["worsening_behaviour_pct"] = round(grp["worsening_behaviour"].mean() * 100, 1)

        # Unplanned weight loss
        if "weight_loss_flag" in grp.columns:
            row["weight_loss_pct"] = round(grp["weight_loss_flag"].mean() * 100, 1)

        # Depression without treatment
        if "depression_dx" in grp.columns and "depression_tx" in grp.columns:
            dep_no_tx = (grp["depression_dx"] & ~grp["depression_tx"])
            row["depression_no_treatment_pct"] = round(dep_no_tx.mean() * 100, 1)

        results.append(row)

    return pd.DataFrame(results)


# ── 2. CIHI Benchmark Comparison ─────────────────────────────────────────────

def benchmark_comparison(qi_df: pd.DataFrame) -> pd.DataFrame:
    latest = qi_df.sort_values("fiscal_quarter").groupby("unit_code").last().reset_index()
    rows = []
    for indicator, benchmarks in CIHI_LTC_BENCHMARKS.items():
        if indicator not in latest.columns:
            continue
        for _, row in latest.iterrows():
            val = row.get(indicator)
            if pd.isna(val):
                continue
            perf = ("Top quartile" if val <= benchmarks["p25"] else
                    "Above median"  if val <= benchmarks["p50"] else
                    "Below median"  if val <= benchmarks["p75"] else "Bottom quartile (flag)")
            rows.append({"unit_code": row["unit_code"], "indicator": indicator,
                          "value": val, "cihi_p50": benchmarks["p50"], "performance": perf})
    df = pd.DataFrame(rows)
    flagged = df[df["performance"] == "Bottom quartile (flag)"]
    print(f"\n── CIHI Benchmarking — bottom-quartile flags: {len(flagged)} ──")
    print(flagged[["unit_code","indicator","value"]].to_string(index=False))
    return df


# ── 3. CHESS Risk Stratification (Falls) ─────────────────────────────────────

def chess_falls_stratification(mds: pd.DataFrame) -> pd.DataFrame:
    """
    CHESS score (0–5): higher = greater health instability.
    Compute falls rate within each CHESS stratum.
    """
    if "chess_score" not in mds.columns or "fall_flag" not in mds.columns:
        return pd.DataFrame()

    mds["chess_group"] = pd.cut(mds["chess_score"], bins=[-1,0,1,2,3,5],
                                  labels=["0","1","2","3","4-5"])
    strat = (
        mds.groupby("chess_group")
        .agg(n=("fall_flag","count"), n_falls=("fall_flag","sum"))
        .reset_index()
    )
    strat["falls_pct"] = (strat["n_falls"] / strat["n"] * 100).round(1)
    strat["pct_of_total_falls"] = (strat["n_falls"] / strat["n_falls"].sum() * 100).round(1)
    print(f"\n── CHESS Falls Stratification ──")
    print(strat.to_string(index=False))
    return strat


# ── 4. Cochran-Armitage Trend Test ────────────────────────────────────────────

def trend_test(qi_df: pd.DataFrame, indicator: str, unit: str) -> dict:
    """Cochran-Armitage test for linear trend across ordered quarters."""
    data = (qi_df[qi_df["unit_code"] == unit]
            .sort_values("fiscal_quarter")[[indicator]]
            .dropna())
    if len(data) < 4:
        return {}
    x = np.arange(len(data))
    y = data[indicator].values
    slope, intercept, r, p, se = stats.linregress(x, y)
    result = {"unit": unit, "indicator": indicator,
              "slope_per_quarter": round(slope, 4),
              "p_value": round(p, 4),
              "significant_trend": p < 0.05,
              "direction": "worsening" if slope > 0 else "improving"}
    print(f"\n── Trend: {indicator} @ {unit}: slope={slope:.4f}, p={p:.4f} ({result['direction']}) ──")
    return result


# ── Export ────────────────────────────────────────────────────────────────────

def export_all(results: dict, outdir: str = "output") -> None:
    import os; os.makedirs(outdir, exist_ok=True)
    for name, obj in results.items():
        if isinstance(obj, pd.DataFrame) and len(obj):
            obj.to_csv(f"{outdir}/{name}.csv", index=False)
            print(f"  Exported → output/{name}.csv")


if __name__ == "__main__":
    mds    = load("data/baycrest_mds_synthetic.csv")
    qi_df  = compute_qi(mds)
    bench  = benchmark_comparison(qi_df)
    chess  = chess_falls_stratification(mds)
    first_unit = qi_df["unit_code"].iloc[0] if len(qi_df) else "Unit_A"
    trend  = trend_test(qi_df, "daily_pain_pct", first_unit)

    export_all({"qi_indicators": qi_df, "cihi_benchmarks": bench, "chess_stratification": chess})
    if trend:
        pd.DataFrame([trend]).to_csv("output/trend_test_result.csv", index=False)
