"""
contribution_ranker.py
Takes the department-level breakdown from sql_tool.py and ranks each
department by its PERCENTAGE CONTRIBUTION to the total store-level
change — not just raw dollars. A dept that dropped $50k in a $100k
total decline contributed 50%; this is what disentangles multi-factor
movements into ranked, attributable drivers.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sql_tool import decompose_by_department


def rank_contributions(store: int, target_date: str, top_n: int = 5) -> dict:
    """
    Ranks departments by their share of the total store-level dollar
    change. Positive contribution = made the decline worse (or drove
    growth, if total change is positive); negative contribution =
    partially offset the movement.
    """
    breakdown = decompose_by_department(store, target_date)
    if "error" in breakdown:
        return breakdown

    total_change = breakdown["total_store_dollar_change"]
    depts = breakdown["department_breakdown"]

    if total_change == 0:
        return {"error": "No net change at store level — nothing to attribute."}

    for d in depts:
        d["contribution_pct"] = round((d["dollar_change"] / total_change) * 100, 2) if total_change != 0 else 0

    ranked = sorted(depts, key=lambda d: abs(d["contribution_pct"]), reverse=True)

    # Determine concentration: is this driven by 1-2 depts (single-cause-like)
    # or spread across many (genuinely multi-factor)?
    top_contributors = ranked[:top_n]
    top_n_contribution_sum = sum(abs(d["contribution_pct"]) for d in top_contributors)

    if len(ranked) > 0 and abs(ranked[0]["contribution_pct"]) >= 60:
        concentration = "single_dominant_driver"
    elif top_n_contribution_sum >= 80:
        concentration = "few_dominant_drivers"
    else:
        concentration = "distributed_multi_factor"

    return {
        "store": store,
        "evaluated_week": breakdown["evaluated_week"],
        "total_store_dollar_change": total_change,
        "concentration_pattern": concentration,
        "ranked_contributors": ranked[:top_n],
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Store 18 — contribution ranking @ 2011-09-02")
    print("=" * 60)
    result = rank_contributions(18, "2011-09-02")
    print(f"Pattern: {result['concentration_pattern']}")
    for d in result["ranked_contributors"]:
        print(f"  Dept {int(d['Dept']):3d}: {d['contribution_pct']:>7.2f}% of total change  (${d['dollar_change']:,.2f})")

    print("\n" + "=" * 60)
    print("Store 27 — contribution ranking @ 2011-09-02")
    print("=" * 60)
    result2 = rank_contributions(27, "2011-09-02")
    print(f"Pattern: {result2['concentration_pattern']}")
    for d in result2["ranked_contributors"]:
        print(f"  Dept {int(d['Dept']):3d}: {d['contribution_pct']:>7.2f}% of total change  (${d['dollar_change']:,.2f})")