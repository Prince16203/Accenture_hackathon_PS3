"""
materiality_gate.py
The single entry point for Phase 2. Decides whether a KPI movement is
"material" — statistically real AND business-significant enough to
proceed to investigation. Combines control_limits, seasonal_decompose,
and sparse_history_fallback, reading thresholds from kpi_contract.yaml
so nothing is duplicated or hardcoded here.

Supports evaluating a specific historical week (target_date) as well
as the latest available week — needed since our scenario anchors are
specific past weeks, not necessarily the most recent one in the dataset.
"""

import pandas as pd
import yaml
from pathlib import Path
import sys

# Ensure this folder is on sys.path so sibling imports work regardless
# of the current working directory this script is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from control_limits import check_breach, has_sufficient_history
from seasonal_decompose import can_run_seasonal_decompose, decompose, flag_residual_outliers
from sparse_history_fallback import evaluate_sparse_kpi, check_sparse_by_threshold, load_registry

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = PROJECT_ROOT / "1_data_foundation" / "kpi_contract.yaml"
SALES_PATH = PROJECT_ROOT / "1_data_foundation" / "sources" / "pos_weekly" / "sales_data.csv"


def load_contract() -> dict:
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_kpi_thresholds(kpi_id: str, contract: dict) -> dict:
    for kpi in contract["kpis"]:
        if kpi["id"] == kpi_id:
            return kpi["materiality"]
    raise ValueError(f"KPI '{kpi_id}' not found in contract.")


def evaluate_materiality(store: int, dept=None, kpi_id: str = "total_weekly_revenue", target_date=None) -> dict:
    """
    Main entry point. Given a store (and optionally a dept), decides
    whether the movement in the given KPI at target_date is material.
    If target_date is None, evaluates the latest available week.
    """
    contract = load_contract()
    thresholds = get_kpi_thresholds(kpi_id, contract)
    sales = pd.read_csv(SALES_PATH)
    sales["Date"] = pd.to_datetime(sales["Date"], format="%d/%m/%Y")

    # --- Step 1: sparse-history check first (cheapest disqualifier) ---
    if dept is not None:
        registry = load_registry()
        if check_sparse_by_threshold(store, dept, sales, registry):
            sparse_result = evaluate_sparse_kpi(store, dept)
            return {
                "kpi_id": kpi_id, "store": store, "dept": dept,
                "path": "sparse_history_fallback",
                "materiality_verdict": sparse_result.get("verdict", "ABSTAIN"),
                "detail": sparse_result,
            }

    # --- Step 2: build the series for standard statistical checks ---
    if dept is not None:
        filtered = sales[(sales["Store"] == store) & (sales["Dept"] == dept)]
    else:
        filtered = sales[sales["Store"] == store]

    series = filtered.groupby("Date")["Weekly_Sales"].sum().sort_index()

    if not has_sufficient_history(series, window=8):
        return {
            "kpi_id": kpi_id, "store": store, "dept": dept,
            "path": "insufficient_history_not_in_registry",
            "materiality_verdict": "ABSTAIN",
            "detail": "Fewer than 8 weeks of history and not flagged in sparse registry — flag for registry update.",
        }

    # --- Step 3: control limits (always runs) ---
    control_result = check_breach(series, window=8, k=2.0)

    # --- Locate the target week's row position ---
    # If a target_date was given, find it (or the nearest available week)
    # in the series index. Otherwise default to the most recent week.
    if target_date is not None:
        target_date = pd.to_datetime(target_date)
        if target_date not in series.index:
            nearest_idx = series.index.get_indexer([target_date], method="nearest")[0]
            target_date = series.index[nearest_idx]
        row_position = series.index.get_loc(target_date)
    else:
        row_position = len(series) - 1
        target_date = series.index[row_position]

    latest = control_result.iloc[row_position]
    control_breach = bool(latest["breached"])

    # --- Step 4: seasonal decomposition (runs if enough history) ---
    seasonal_breach = None
    if can_run_seasonal_decompose(series):
        series_regular = series.asfreq("W-FRI").interpolate()
        decomposed = decompose(series_regular)
        flagged = flag_residual_outliers(decomposed)
        if target_date in flagged.index:
            seasonal_breach = bool(flagged.loc[target_date, "is_outlier"])

    # --- Step 5: business impact check, relative to the PRIOR week ---
    prev_value = series.iloc[row_position - 1] if row_position >= 1 else None
    current_value = series.iloc[row_position]
    pct_change = None
    dollar_impact = None
    if prev_value:
        pct_change = (current_value - prev_value) / prev_value
        dollar_impact = abs(current_value - prev_value)

    is_statistically_flagged = control_breach or (seasonal_breach is True)
    is_business_material = (
        pct_change is not None and
        abs(pct_change) >= thresholds["min_pct_change"] and
        dollar_impact >= thresholds["min_dollar_impact"]
    )

    verdict = "MATERIAL" if (is_statistically_flagged and is_business_material) else "NOT_MATERIAL"

    return {
        "kpi_id": kpi_id, "store": store, "dept": dept,
        "path": "standard",
        "evaluated_week": str(target_date.date()),
        "materiality_verdict": verdict,
        "detail": {
            "control_limit_breach": control_breach,
            "seasonal_breach": seasonal_breach,
            "pct_change": round(pct_change, 4) if pct_change is not None else None,
            "dollar_impact": round(dollar_impact, 2) if dollar_impact is not None else None,
            "thresholds_used": thresholds,
        },
    }


if __name__ == "__main__":
    test_cases = [
        (18, None, "2011-09-02"),   # clean single-cause scenario
        (27, None, "2011-09-02"),   # multi-factor scenario
        (3, 83, None),
        (7, 99, None),
        (17, None, "2011-04-29"),   # low-confidence scenario
    ]

    for store, dept, target_date in test_cases:
        result = evaluate_materiality(store, dept, target_date=target_date)
        print(f"\n{'='*60}")
        label = f"Store {store}" + (f" / Dept {dept}" if dept else "")
        label += f" @ {target_date}" if target_date else " (latest)"
        print(label)
        print(f"  Path: {result['path']}")
        print(f"  Verdict: {result['materiality_verdict']}")
        print(f"  Detail: {result['detail']}")