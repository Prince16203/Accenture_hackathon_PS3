"""
sql_tool.py
Dimensional decomposition tool — the agent's primary tool for answering
"where inside this KPI movement is it actually coming from." Given a
store and a target week already confirmed MATERIAL by the signal layer,
breaks the store-level movement down by department.

This is deterministic pandas/SQL-style aggregation, not an LLM call —
the agent calls this tool and gets back numbers, not a generated guess.
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SALES_PATH = PROJECT_ROOT / "1_data_foundation" / "sources" / "pos_weekly" / "sales_data.csv"
STORES_DIM_PATH = PROJECT_ROOT / "1_data_foundation" / "dimensions" / "stores_dim.csv"
REGION_MAP_PATH = PROJECT_ROOT / "1_data_foundation" / "dimensions" / "store_region_mapping.csv"

_sales_cache = None


def _load_sales() -> pd.DataFrame:
    """Cached load — avoids re-reading the 13MB CSV on every tool call within one process."""
    global _sales_cache
    if _sales_cache is None:
        df = pd.read_csv(SALES_PATH)
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
        _sales_cache = df
    return _sales_cache


def _nearest_week(series_dates: pd.Series, target_date: pd.Timestamp) -> pd.Timestamp:
    """Find the closest actual date in the data to a requested target_date."""
    diffs = (series_dates - target_date).abs()
    return series_dates.loc[diffs.idxmin()]


def decompose_by_department(store: int, target_date: str) -> dict:
    """
    For a given store and week, returns each department's revenue this
    week vs. the prior week, sorted by dollar contribution to the
    store-level change. This is what localizes a store-level anomaly
    down to the specific department(s) driving it.
    """
    sales = _load_sales()
    target_date = pd.to_datetime(target_date)

    store_data = sales[sales["Store"] == store].copy()
    all_dates = store_data["Date"].drop_duplicates().sort_values()
    actual_target = _nearest_week(all_dates, target_date)

    prior_candidates = all_dates[all_dates < actual_target]
    if prior_candidates.empty:
        return {"error": "No prior week available for comparison — this is the first recorded week."}
    prior_date = prior_candidates.max()

    current_week = store_data[store_data["Date"] == actual_target][["Dept", "Weekly_Sales"]]
    prior_week = store_data[store_data["Date"] == prior_date][["Dept", "Weekly_Sales"]]

    merged = pd.merge(current_week, prior_week, on="Dept", how="outer",
                       suffixes=("_current", "_prior")).fillna(0)
    merged["dollar_change"] = merged["Weekly_Sales_current"] - merged["Weekly_Sales_prior"]
    merged["pct_change"] = merged.apply(
        lambda r: (r["dollar_change"] / r["Weekly_Sales_prior"]) if r["Weekly_Sales_prior"] != 0 else None,
        axis=1
    )
    merged = merged.sort_values("dollar_change")

    total_store_change = merged["dollar_change"].sum()

    return {
        "store": store,
        "evaluated_week": str(actual_target.date()),
        "compared_to_week": str(prior_date.date()),
        "total_store_dollar_change": round(total_store_change, 2),
        "department_breakdown": merged.round(4).to_dict(orient="records"),
        "top_declining_depts": merged.head(5).round(4).to_dict(orient="records"),
        "top_growing_depts": merged.tail(5).round(4).to_dict(orient="records"),
    }


def store_weekly_series(store: int, dept: int = None) -> pd.Series:
    """Returns the weekly revenue time series for a store (optionally filtered to one dept)."""
    sales = _load_sales()
    if dept is not None:
        filtered = sales[(sales["Store"] == store) & (sales["Dept"] == dept)]
    else:
        filtered = sales[sales["Store"] == store]
    return filtered.groupby("Date")["Weekly_Sales"].sum().sort_index()


def regional_rollup(target_date: str) -> dict:
    """
    Rolls store-level revenue up to region-level for a given week,
    using the store_region_mapping dimension. Used to check whether
    an anomaly is isolated to one store or part of a wider regional pattern.
    """
    sales = _load_sales()
    region_map = pd.read_csv(REGION_MAP_PATH)
    target_date = pd.to_datetime(target_date)

    all_dates = sales["Date"].drop_duplicates().sort_values()
    actual_target = _nearest_week(all_dates, target_date)

    week_data = sales[sales["Date"] == actual_target].groupby("Store")["Weekly_Sales"].sum().reset_index()
    week_data = week_data.merge(region_map, left_on="Store", right_on="store", how="left")

    regional = week_data.groupby("region")["Weekly_Sales"].sum().sort_values(ascending=False)

    return {
        "evaluated_week": str(actual_target.date()),
        "regional_totals": regional.round(2).to_dict(),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Store 18 department breakdown @ 2011-09-02")
    print("=" * 60)
    result = decompose_by_department(18, "2011-09-02")
    print(f"Total store change: ${result['total_store_dollar_change']:,.2f}")
    print(f"\nTop declining departments:")
    for d in result["top_declining_depts"]:
        print(f"  Dept {int(d['Dept']):3d}: ${d['dollar_change']:>12,.2f}  ({d['pct_change']})")

    print("\n" + "=" * 60)
    print("Store 27 department breakdown @ 2011-09-02")
    print("=" * 60)
    result2 = decompose_by_department(27, "2011-09-02")
    print(f"Total store change: ${result2['total_store_dollar_change']:,.2f}")
    print(f"\nTop declining departments:")
    for d in result2["top_declining_depts"]:
        print(f"  Dept {int(d['Dept']):3d}: ${d['dollar_change']:>12,.2f}  ({d['pct_change']})")

    print("\n" + "=" * 60)
    print("Regional rollup @ 2011-09-02")
    print("=" * 60)
    regional = regional_rollup("2011-09-02")
    for region, total in regional["regional_totals"].items():
        print(f"  {region:10s}: ${total:>15,.2f}")