"""
scenario_2_low_confidence.py
DEMO SCENARIO: Low-confidence / abstention.
Store 17, week of 2011-04-29 — a real -23.9% drop where retrieved
evidence directly contradicts itself (one ticket claims a stockout-like
shortage, another explicitly says inventory audit showed full stock).
The system must recognize this and ABSTAIN rather than force an answer.
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
    print("SCENARIO: Low-Confidence — Contradictory Evidence Triggers Abstention")
    print("Store 17 — week of 2011-04-29 (real anomaly: -23.9%, $253,791)")
    print("=" * 70)

    state = run_investigation(17, target_date="2011-04-29")
    print(f"\n[1] Materiality: {state['materiality_verdict']} (statistically real — seasonal residual outlier)")

    print(f"\n[2] Evidence retrieved: {len(state.get('evidence', []))} tickets")
    contradiction = state.get("contradiction_result", {})
    print(f"[3] Contradiction check: has_contradiction={contradiction.get('has_contradiction')}")
    for pair in contradiction.get("flagged_pairs", []):
        print(f"    CONFLICT: {pair['ticket_a']} vs {pair['ticket_b']} — {pair['reason']}")

    print(f"\n[4] Investigation status: {state['status'].upper()}")
    print(f"    Stop reason: {state.get('stop_reason')}")

    confidence = decide_confidence(state)
    print(f"\n[5] Confidence tier: {confidence.get('confidence_tier')}")
    print(f"    (Investigation halted BEFORE hypothesis-building — correctly cheaper than forcing a wrong answer)")

    recommendation = build_recommendation(state, confidence)
    print(f"\n[6] Recommendation available: {recommendation.get('recommendation_available')}")
    print(f"    {recommendation.get('reason')}")

    narratives = generate_all_narratives(state, confidence, recommendation)
    print(f"\n[7] What each persona sees instead of a false answer:")
    for persona, text in narratives.items():
        print(f"\n--- {persona.upper()} ---")
        print(text)

    return state, confidence, recommendation, narratives


if __name__ == "__main__":
    run()