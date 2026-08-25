"""
scenario_5_clean_case.py
DEMO SCENARIO: Clean single-cause diagnosis.
Store 18, week of 2011-09-02 — a real -52.9% revenue drop driven by a
weather-related stockout. High confidence expected: evidence converges
clearly, numeric and qualitative signals align.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
for p in ["5_agent", "6_confidence_layer", "7_recommendation_engine", "8_narrative_layer", "11_telemetry"]:
    sys.path.insert(0, str(ROOT / p))

from react_orchestrator import run_investigation
from abstention_policy import decide_confidence
from filler import build_recommendation
from persona_narrator import generate_all_narratives


def run():
    print("=" * 70)
    print("SCENARIO: Clean Single-Cause Diagnosis")
    print("Store 18 — week of 2011-09-02 (real anomaly: -52.9%, $606,984)")
    print("=" * 70)

    state = run_investigation(18, target_date="2011-09-02")
    print(f"\n[1] Materiality: {state['materiality_verdict']}")
    print(f"[2] Concentration pattern: {state.get('concentration_pattern')}")
    print(f"[3] Evidence retrieved: {len(state.get('evidence', []))} tickets")

    confidence = decide_confidence(state)
    print(f"\n[4] Confidence tier: {confidence['confidence_tier']} (score: {confidence.get('confidence_score')})")
    print(f"    Agreement: {confidence['agreement']['agreement_level']}")
    print(f"    Match strength: {confidence['match_strength']['match_strength']}")
    print(f"    Self-consistency: {confidence['self_consistency']['consistency_score']}")

    recommendation = build_recommendation(state, confidence)
    print(f"\n[5] Recommendation:")
    print(f"    Driver: {recommendation.get('driver')}")
    print(f"    Action: {recommendation.get('action')}")
    print(f"    Owner: {recommendation.get('owner')}")

    narratives = generate_all_narratives(state, confidence, recommendation)
    print(f"\n[6] Persona narratives:")
    for persona, text in narratives.items():
        print(f"\n--- {persona.upper()} ---")
        print(text)

    return state, confidence, recommendation, narratives


if __name__ == "__main__":
    run()