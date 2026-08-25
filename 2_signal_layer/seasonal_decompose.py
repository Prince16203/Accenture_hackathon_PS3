"""
seasonal_decompose.py
Decomposes a weekly revenue series into trend + seasonal + residual
components. A large residual (after removing expected seasonal pattern)
is a stronger anomaly signal than a raw control-limit breach, because
it already accounts for predictable holiday/seasonal swings.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.seasonal import STL

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SALES_PATH = PROJECT_ROOT / "1_data_foundation" / "sources" / "pos_weekly" / "sales_data.csv"

MIN_WEEKS_FOR_STL = 104  # need ~2 years of weekly data for a 52-week seasonal cycle


def can_run_seasonal_decompose(series: pd.Series) -> bool:
    return series.dropna().shape[0] >= MIN_WEEKS_FOR_STL


def decompose(series: pd.Series, period: int = 52):
    if not can_run_seasonal_decompose(series):
        raise ValueError(
            f"Insufficient history for STL: {series.dropna().shape[0]} weeks, "
            f"need at least {MIN_WEEKS_FOR_STL}."
        )

    stl = STL(series, period=period, robust=True)
    result = stl.fit()

    return pd.DataFrame({
        "value": series,
        "trend": result.trend,
        "seasonal": result.seasonal,
        "resid": result.resid,
    })


def flag_residual_outliers(decomposed: pd.DataFrame, k: float = 2.0) -> pd.DataFrame:
    resid_std = decomposed["resid"].std()
    decomposed = decomposed.copy()
    decomposed["resid_zscore"] = decomposed["resid"] / resid_std
    decomposed["is_outlier"] = decomposed["resid_zscore"].abs() > k
    return decomposed


if __name__ == "__main__":
    sales = pd.read_csv(SALES_PATH)
    sales["Date"] = pd.to_datetime(sales["Date"], format="%d/%m/%Y")

    store_28 = sales[sales["Store"] == 28].groupby("Date")["Weekly_Sales"].sum().sort_index()
    store_28 = store_28.asfreq("W-FRI").interpolate()

    if can_run_seasonal_decompose(store_28):
        decomposed = decompose(store_28)
        flagged = flag_residual_outliers(decomposed)
        outliers = flagged[flagged["is_outlier"]]
        print(f"Store 28 — {len(outliers)} seasonal-adjusted anomalies found")
        print(outliers[["value", "resid", "resid_zscore"]].tail(5))
    else:
        n = store_28.dropna().shape[0]
        print(f"Store 28 has only {n} weeks — not enough for STL (need {MIN_WEEKS_FOR_STL}). "
              f"Falls back to control_limits.py only.")