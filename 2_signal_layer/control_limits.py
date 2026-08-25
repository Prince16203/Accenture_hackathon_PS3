"""
control_limits.py
Statistical process control check — the cheapest, fastest materiality
test. Flags a data point as anomalous if it falls outside a trailing
mean +/- k*std band, using only prior weeks (never the current one)
to avoid the current anomaly inflating its own bounds.
"""

import pandas as pd
from pathlib import Path

# Resolve project root regardless of current working directory —
# this file lives in 2_signal_layer/, so root is one level up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SALES_PATH = PROJECT_ROOT / "1_data_foundation" / "sources" / "pos_weekly" / "sales_data.csv"


def compute_trailing_bounds(series: pd.Series, window: int = 8, k: float = 2.0):
    trailing_mean = series.shift(1).rolling(window=window, min_periods=window).mean()
    trailing_std = series.shift(1).rolling(window=window, min_periods=window).std()

    return pd.DataFrame({
        "value": series,
        "trailing_mean": trailing_mean,
        "trailing_std": trailing_std,
        "lower_bound": trailing_mean - k * trailing_std,
        "upper_bound": trailing_mean + k * trailing_std,
    })


def check_breach(series: pd.Series, window: int = 8, k: float = 2.0) -> pd.DataFrame:
    bounds = compute_trailing_bounds(series, window=window, k=k)
    bounds["breached"] = (
        (bounds["value"] < bounds["lower_bound"]) |
        (bounds["value"] > bounds["upper_bound"])
    ).fillna(False)
    return bounds


def has_sufficient_history(series: pd.Series, window: int = 8) -> bool:
    return series.dropna().shape[0] >= window


if __name__ == "__main__":
    sales = pd.read_csv(SALES_PATH)
    sales["Date"] = pd.to_datetime(sales["Date"], format="%d/%m/%Y")

    store_28 = sales[sales["Store"] == 28].groupby("Date")["Weekly_Sales"].sum().sort_index()

    if has_sufficient_history(store_28):
        result = check_breach(store_28)
        breaches = result[result["breached"]]
        print(f"Store 28 — {len(breaches)} control-limit breaches found out of {len(result)} weeks")
        print(breaches.tail(5))
    else:
        print("Not enough history for control limits.")