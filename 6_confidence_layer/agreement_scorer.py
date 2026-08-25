"""
agreement_scorer.py
Checks whether the EVIDENCE ITSELF converges on a clear answer — i.e.
whether one hypothesis clearly outscores its alternatives, versus
several hypotheses being genuinely comparable (real ambiguity).

Note: this deliberately does NOT compare against the department-level
concentration_pattern from Phase 3. That numeric pattern answers "which
departments moved" — a different question from "which CAUSE explains
it." A single root cause (e.g. a store-wide weather disruption) can
legitimately produce a distributed department-level impact while still
having one clear causal hypothesis — that's not a contradiction, it's
the expected shape of a store-wide event. Treating those two axes as
required to match was a design error in an earlier version of this file.
"""


def score_agreement(decomposition_result: dict, hypotheses: list) -> dict:
    if not hypotheses:
        return {
            "agreement_level": "none",
            "reasoning": "No hypotheses generated — nothing to assess.",
            "score": 0.0,
        }

    valid_hyps = [h for h in hypotheses if h["net_support_score"] > 0]
    if not valid_hyps:
        return {
            "agreement_level": "none",
            "reasoning": "All hypotheses were net-refuted by evidence — no positive-scoring driver remains.",
            "score": 0.0,
        }

    sorted_hyps = sorted(valid_hyps, key=lambda h: h["net_support_score"], reverse=True)
    top_score = sorted_hyps[0]["net_support_score"]
    second_score = sorted_hyps[1]["net_support_score"] if len(sorted_hyps) > 1 else 0

    margin_ratio = (top_score - second_score) / top_score if top_score > 0 else 0
    has_clear_winner = margin_ratio >= 0.4 or len(sorted_hyps) == 1

    if has_clear_winner:
        agreement_level = "high"
        score = 1.0
        reasoning = (
            f"Evidence converges clearly on '{sorted_hyps[0]['driver_type']}' "
            f"(margin over runner-up: {margin_ratio:.0%})."
        )
    else:
        agreement_level = "low"
        score = 0.3
        reasoning = (
            f"Evidence is split between comparable hypotheses "
            f"('{sorted_hyps[0]['driver_type']}' vs '{sorted_hyps[1]['driver_type']}', "
            f"margin only {margin_ratio:.0%}) — no clear single winner."
        )

    concentration = decomposition_result.get("concentration_pattern", "unknown") if decomposition_result else "unknown"

    return {
        "agreement_level": agreement_level,
        "score": score,
        "reasoning": reasoning,
        "top_hypothesis": sorted_hyps[0]["driver_type"],
        "margin_ratio": round(margin_ratio, 3),
        "numeric_concentration_context": concentration,  # informational only, not scored
    }


if __name__ == "__main__":
    # Store 18 style: one clear hypothesis — should be HIGH agreement now
    result1 = score_agreement(
        {"concentration_pattern": "distributed_multi_factor"},
        [{"driver_type": "supply_disruption", "net_support_score": 4.45}]
    )
    print("Store 18 test:", result1)

    # Store 27 style: two comparable-but-distinguishable hypotheses
    result2 = score_agreement(
        {"concentration_pattern": "distributed_multi_factor"},
        [
            {"driver_type": "promotional_visibility", "net_support_score": 2.0},
            {"driver_type": "supply_disruption", "net_support_score": -0.43},
        ]
    )
    print("Store 27 test:", result2)