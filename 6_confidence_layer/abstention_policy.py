"""
abstention_policy.py
The final confidence decision — combines agreement_scorer, match_strength,
and self_consistency_check into one tier (HIGH / MEDIUM / LOW / ABSTAIN),
applying the sparse-history confidence ceiling where relevant. This is
the last node before an investigation's result gets handed to the
narrative layer — LOW/ABSTAIN results should be surfaced as-is, not
smoothed over by a confident-sounding LLM writeup later.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agreement_scorer import score_agreement
from match_strength import score_match_strength
from self_consistency_check import check_self_consistency


def decide_confidence(state: dict) -> dict:
    """
    Main entry point. Takes a completed investigation state (from
    react_orchestrator.run_investigation) and produces a final
    confidence verdict. Only called when status == 'completed' —
    states that already stopped at abstain/not_material bypass this
    (they're already a form of abstention, just decided earlier/cheaper).
    """
    if state.get("status") != "completed":
        return {
            "confidence_tier": "N/A",
            "reasoning": f"Investigation already stopped: {state.get('stop_reason')}",
        }

    hypotheses = state.get("hypotheses", [])
    decomposition_result = state.get("decomposition_result", {})
    evidence = state.get("evidence", [])
    materiality_path = state.get("materiality_result", {}).get("path", "standard")

    agreement = score_agreement(decomposition_result, hypotheses)
    match = score_match_strength(evidence, materiality_path=materiality_path)
    consistency = check_self_consistency(state["store"], decomposition_result)

    # Weighted combination — agreement and consistency matter most (they
    # catch fragile/mismatched answers), match_strength is a supporting signal.
    raw_score = (0.4 * agreement["score"]) + (0.25 * match["score"]) + (0.35 * consistency["consistency_score"])
    final_score = min(raw_score, match["confidence_ceiling"])

    if final_score >= 0.75:
        tier = "HIGH"
    elif final_score >= 0.5:
        tier = "MEDIUM"
    elif final_score >= 0.3:
        tier = "LOW"
    else:
        tier = "ABSTAIN"

    result = {
        "confidence_tier": tier,
        "confidence_score": round(final_score, 3),
        "agreement": agreement,
        "match_strength": match,
        "self_consistency": consistency,
    }

    if tier in ("LOW", "ABSTAIN"):
        result["what_would_help"] = _suggest_resolution(agreement, match, consistency)

    return result


def _suggest_resolution(agreement: dict, match: dict, consistency: dict) -> str:
    """Generates a concrete note on what additional data/evidence would raise confidence."""
    reasons = []
    if agreement["agreement_level"] == "low":
        reasons.append("numeric decomposition and evidence-based hypotheses disagree on the pattern shape")
    if match["match_strength"] in ("weak", "none"):
        reasons.append("retrieved evidence is thin or weakly relevant — more field reports for this store/week would help")
    if not consistency["is_consistent"]:
        reasons.append("the top hypothesis changes depending on how the question is phrased, suggesting a fragile conclusion")
    return "; ".join(reasons) if reasons else "Multiple weak signals combined below threshold."


if __name__ == "__main__":
    from pathlib import Path as P
    sys.path.insert(0, str(P(__file__).resolve().parent.parent / "5_agent"))
    from react_orchestrator import run_investigation

    print("=" * 70)
    print("CONFIDENCE: Store 18 @ 2011-09-02 (expect HIGH)")
    print("=" * 70)
    state1 = run_investigation(18, target_date="2011-09-02")
    conf1 = decide_confidence(state1)
    print(f"Tier: {conf1['confidence_tier']}  Score: {conf1.get('confidence_score')}")
    print(f"Agreement: {conf1['agreement']['agreement_level']}")
    print(f"Match: {conf1['match_strength']['match_strength']}")
    print(f"Consistency: {conf1['self_consistency']['consistency_score']}")

    print("\n" + "=" * 70)
    print("CONFIDENCE: Store 27 @ 2011-09-02 (expect MEDIUM — multi-factor, real but nuanced)")
    print("=" * 70)
    state2 = run_investigation(27, target_date="2011-09-02")
    conf2 = decide_confidence(state2)
    print(f"Tier: {conf2['confidence_tier']}  Score: {conf2.get('confidence_score')}")
    print(f"Agreement: {conf2['agreement']['agreement_level']}")
    print(f"Match: {conf2['match_strength']['match_strength']}")
    print(f"Consistency: {conf2['self_consistency']['consistency_score']}")
    if conf2.get("what_would_help"):
        print(f"What would help: {conf2['what_would_help']}")

    print("\n" + "=" * 70)
    print("CONFIDENCE: Store 17 @ 2011-04-29 (expect N/A — already abstained upstream)")
    print("=" * 70)
    state3 = run_investigation(17, target_date="2011-04-29")
    conf3 = decide_confidence(state3)
    print(conf3)