"""
filler.py
Fills the matched action template's placeholder slots ({store},
{dollar_impact}, {pct_change_abs}, {region}) with actual numbers from
the investigation state. This is DETERMINISTIC string formatting, not
an LLM call — the LLM's role (when configured) would be limited to
rephrasing this already-computed, already-correct content into more
natural prose, never deciding the numbers or the action itself.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from template_matcher import match_template


def _extract_slot_values(state: dict) -> dict:
    """Pulls the raw numbers needed for template slots out of investigation state."""
    materiality_detail = state.get("materiality_result", {}).get("detail", {})
    pct_change = materiality_detail.get("pct_change")
    dollar_impact = materiality_detail.get("dollar_impact")

    region = "unknown"
    evidence = state.get("evidence", [])
    if evidence:
        region = evidence[0].get("region", "unknown")

    return {
        "store": state.get("store"),
        "region": region,
        "pct_change_abs": round(abs(pct_change) * 100, 1) if pct_change is not None else "N/A",
        "dollar_impact": f"{dollar_impact:,.2f}" if dollar_impact is not None else "N/A",
    }


def build_recommendation(state: dict, confidence_result: dict) -> dict:
    """
    Main entry point. Returns a fully-filled recommendation dict:
    driver, lever, action, expected_impact, owner, confidence, monitoring_plan.
    Returns a fallback dict (not an exception) if no template matched.
    """
    match_result = match_template(state, confidence_result)

    if not match_result["matched"]:
        return {
            "recommendation_available": False,
            "reason": match_result["reason"],
            "confidence_tier": match_result["confidence_tier"],
        }

    template = match_result["template"]
    slots = _extract_slot_values(state)

    try:
        action = template["action_template"].format(**slots).strip()
        expected_impact = template["expected_impact_template"].format(**slots).strip()
        monitoring_plan = template["monitoring_plan"].format(**slots).strip()
    except KeyError as e:
        return {
            "recommendation_available": False,
            "reason": f"Template slot filling failed — missing key {e}.",
            "confidence_tier": match_result["confidence_tier"],
        }

    return {
        "recommendation_available": True,
        "driver": template["driver_label"],
        "controllable_lever": template["controllable_lever"],
        "action": action,
        "expected_impact": expected_impact,
        "owner": template["default_owner"],
        "confidence": match_result["confidence_tier"],
        "monitoring_plan": monitoring_plan,
    }


if __name__ == "__main__":
    from pathlib import Path as P
    sys.path.insert(0, str(P(__file__).resolve().parent.parent / "5_agent"))
    sys.path.insert(0, str(P(__file__).resolve().parent.parent / "6_confidence_layer"))
    from react_orchestrator import run_investigation
    from abstention_policy import decide_confidence

    print("=" * 70)
    print("RECOMMENDATION: Store 18 @ 2011-09-02 (expect: supply_disruption action)")
    print("=" * 70)
    state1 = run_investigation(18, target_date="2011-09-02")
    conf1 = decide_confidence(state1)
    rec1 = build_recommendation(state1, conf1)
    for k, v in rec1.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 70)
    print("RECOMMENDATION: Store 27 @ 2011-09-02 (expect: promotional_visibility action)")
    print("=" * 70)
    state2 = run_investigation(27, target_date="2011-09-02")
    conf2 = decide_confidence(state2)
    rec2 = build_recommendation(state2, conf2)
    for k, v in rec2.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 70)
    print("RECOMMENDATION: Store 17 @ 2011-04-29 (expect: no recommendation, already abstained)")
    print("=" * 70)
    state3 = run_investigation(17, target_date="2011-04-29")
    conf3 = decide_confidence(state3)
    rec3 = build_recommendation(state3, conf3)
    for k, v in rec3.items():
        print(f"{k}: {v}")