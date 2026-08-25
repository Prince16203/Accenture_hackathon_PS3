"""
scenario_1_multifactor.py
DEMO SCENARIO: Multi-factor KPI movement with disentangled drivers.
Store 27, week of 2011-09-02 — a real -25.7% drop where marketing pause,
staffing gaps, and a competitor entry all appear as candidate causes,
but the system correctly identifies promotional_visibility as dominant
while explicitly REFUTING the supply_disruption hypothesis (a ticket
confirms inventory was normal, ruling out a stockout explanation).
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
for p in ["5_agent", "6_confidence_layer", "7_recommendation_engine", "8_narrative_layer"]:
    sys.path.insert(0, str(ROOT / p))

from react_orchestrator import run_investigation
from abstention_policy import decide_confidence
from filler import build_recommendation
from persona_narrator import generate_all_narratives


def run():
    print("=" * 70)
    print("SCENARIO: Multi-Factor Movement — Disentangling Competing Drivers")
    print("Store 27 — week of 2011-09-02 (real anomaly: -25.7%, $522,683)")
    print("=" * 70)

    state = run_investigation(27, target_date="2011-09-02")
    print(f"\n[1] Materiality: {state['materiality_verdict']}")
    print(f"[2] Concentration pattern: {state.get('concentration_pattern')}")

    print(f"\n[3] All hypotheses considered (not just the winner):")
    for h in state.get("hypotheses", []):
        flag = "✓ SUPPORTED" if h["net_support_score"] > 0 else "✗ REFUTED"
        print(f"    {h['driver_type']:25s} score={h['net_support_score']:>6.2f}  [{flag}]")
        if h["contradicting_ticket_ids"]:
            print(f"      contradicted by: {h['contradicting_ticket_ids']}")

    confidence = decide_confidence(state)
    print(f"\n[4] Confidence tier: {confidence['confidence_tier']} (score: {confidence.get('confidence_score')})")

    recommendation = build_recommendation(state, confidence)
    print(f"\n[5] Recommendation (based on winning hypothesis only):")
    print(f"    Driver: {recommendation.get('driver')}")
    print(f"    Action: {recommendation.get('action')}")

    narratives = generate_all_narratives(state, confidence, recommendation)
    print(f"\n[6] VP narrative (includes recurrence check):")
    print(narratives["regional_vp"])

    return state, confidence, recommendation, narratives


if __name__ == "__main__":
    run()