"""
sparse_history_fallback.py
Handles KPIs flagged in sparse_history_registry.yaml — Store x Dept
combinations with too little history for control_limits or
seasonal_decompose to be statistically meaningful. Routes to a
cohort-proxy comparison instead, or to explicit abstention if no
valid cohort exists.
"""

import pandas as pd
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "1_data_foundation" / "sparse_history_registry.yaml"
SALES_PATH = PROJECT_ROOT / "1_data_foundation" / "sources" / "pos_weekly" / "sales_data.csv"
STORES_DIM_PATH = PROJECT_ROOT / "1_data_foundation" / "dimensions" / "stores_dim.csv"


def load_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_flagged_sparse(store: int, dept: int, registry: dict):
    for combo in registry.get("flagged_combinations", []):
        if combo["store"] == store and combo["dept"] == dept:
            return combo
    return None


def check_sparse_by_threshold(store: int, dept: int, sales: pd.DataFrame, registry: dict) -> bool:
    threshold = registry["global_thresholds"]["sparse_flag_threshold"]
    n_weeks = sales[(sales["Store"] == store) & (sales["Dept"] == dept)].shape[0]
    return n_weeks < threshold


def cohort_proxy_baseline(store: int, dept: int, sales: pd.DataFrame, stores_dim: pd.DataFrame,
                           match_on: list) -> dict:
    this_store_info = stores_dim[stores_dim["Store"] == store].iloc[0]

    peer_stores = stores_dim.copy()
    for dim in match_on:
        peer_stores = peer_stores[peer_stores[dim] == this_store_info[dim]]
    peer_store_ids = peer_stores["Store"].tolist()

    peer_dept_sales = sales[
        (sales["Store"].isin(peer_store_ids)) &
        (sales["Dept"] == dept) &
        (sales["Store"] != store)
    ]

    if peer_dept_sales.empty:
        return {
            "baseline_available": False,
            "reason": f"No peer stores of matching {match_on} have Dept {dept} data.",
        }

    return {
        "baseline_available": True,
        "peer_store_count": peer_dept_sales["Store"].nunique(),
        "peer_avg_weekly_sales": round(peer_dept_sales["Weekly_Sales"].mean(), 2),
        "peer_store_ids": peer_store_ids,
    }


def evaluate_sparse_kpi(store: int, dept: int) -> dict:
    registry = load_registry()
    sales = pd.read_csv(SALES_PATH)
    stores_dim = pd.read_csv(STORES_DIM_PATH)

    flagged_entry = is_flagged_sparse(store, dept, registry)

    if flagged_entry is None:
        if not check_sparse_by_threshold(store, dept, sales, registry):
            return {"is_sparse": False, "message": "Sufficient history — use standard signal layer."}
        return {
            "is_sparse": True,
            "in_registry": False,
            "action": "route_to_fallback_and_log_for_registry_update",
        }

    strategy = flagged_entry["fallback_strategy"]

    if strategy == "no_baseline_available":
        return {
            "is_sparse": True,
            "in_registry": True,
            "strategy": strategy,
            "verdict": "ABSTAIN",
            "reason": flagged_entry["cohort_definition"]["description"],
        }

    cohort = cohort_proxy_baseline(
        store, dept, sales, stores_dim,
        match_on=flagged_entry["cohort_definition"]["match_on"]
    )

    return {
        "is_sparse": True,
        "in_registry": True,
        "strategy": strategy,
        "verdict": "COHORT_COMPARISON" if cohort["baseline_available"] else "ABSTAIN",
        "cohort_result": cohort,
        "confidence_cap": "reduced",
    }


if __name__ == "__main__":
    for store, dept in [(3, 83), (7, 99), (14, 43)]:
        result = evaluate_sparse_kpi(store, dept)
        print(f"\nStore {store} / Dept {dept}:")
        for k, v in result.items():
            print(f"  {k}: {v}")