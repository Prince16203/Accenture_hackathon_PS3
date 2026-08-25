"""
scenario_3_sparse_history.py
DEMO SCENARIO: Sparse/newly-launched KPI handling.
Two real cases from the actual dataset:
  - Store 3 / Dept 83: 1 week of history -> cohort-proxy comparison
    against peer stores of the same Type.
  - Store 7 / Dept 99: 1 week of history, single test-batch pilot with
    NO valid peer cohort -> explicit ABSTAIN rather than a forced
    comparison against nothing.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "5_agent"))
sys.path.insert(0, str(ROOT / "2_signal_layer"))

from react_orchestrator import run_investigation
from sparse_history_fallback import evaluate_sparse_kpi


def run():
    print("=" * 70)
    print("SCENARIO: Sparse-History KPI Handling")
    print("=" * 70)

    print("\n--- Case A: Store 3 / Dept 83 (new department launch) ---")
    detail_a = evaluate_sparse_kpi(3, 83)
    print(f"Strategy: {detail_a['strategy']}")
    print(f"Verdict: {detail_a['verdict']}")
    if detail_a["verdict"] == "COHORT_COMPARISON":
        cohort = detail_a["cohort_result"]
        print(f"Compared against {cohort['peer_store_count']} peer stores of the same Type")
        print(f"Peer average weekly sales: ${cohort['peer_avg_weekly_sales']:,.2f}")
        print(f"Confidence cap applied: {detail_a['confidence_cap']} (cohort comparisons never reach full confidence)")

    print("\n--- Case B: Store 7 / Dept 99 (single test-batch pilot, no peer cohort) ---")
    detail_b = evaluate_sparse_kpi(7, 99)
    print(f"Strategy: {detail_b['strategy']}")
    print(f"Verdict: {detail_b['verdict']}")
    print(f"Reason: {detail_b['reason']}")
    print("\n(This is the honest path — no valid comparison exists, so the system says so")
    print(" instead of forcing a statistical test against nothing.)")

    full_state_a = run_investigation(3, dept=83)
    full_state_b = run_investigation(7, dept=99)

    return detail_a, detail_b, full_state_a, full_state_b


if __name__ == "__main__":
    run()