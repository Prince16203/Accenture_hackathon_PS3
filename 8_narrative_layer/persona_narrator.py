"""
persona_narrator.py
Generates persona-specific narratives from the same underlying
investigation + confidence + recommendation data. Deterministic
templating for now — the LLM's role (once configured) would be
limited to smoothing the phrasing of these already-correct,
already-computed facts, never deciding what to say.

Two personas minimum, per spec: store_manager (operational) and
regional_vp (strategic/financial). Same facts, different framing.
"""

import yaml
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONA_PATH = PROJECT_ROOT / "8_narrative_layer" / "persona_profiles.yaml"

sys.path.insert(0, str(PROJECT_ROOT / "5_agent"))
sys.path.insert(0, str(PROJECT_ROOT / "6_confidence_layer"))
sys.path.insert(0, str(PROJECT_ROOT / "7_recommendation_engine"))


def load_personas() -> dict:
    with open(PERSONA_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["personas"]


def _check_recurring_pattern(state: dict, evidence: list) -> str:
    """
    Lightweight recurrence check: does the evidence set for this store
    reference a prior/recurring version of the same issue? Looks for
    explicit language in the retrieved tickets rather than querying
    historical incident records (which this prototype doesn't track
    separately) — a real production system would check an incident log.
    """
    recurrence_keywords = ["second", "again", "recurring", "consecutive", "third"]
    for ticket in evidence:
        text_lower = ticket.get("text", "").lower()
        if any(kw in text_lower for kw in recurrence_keywords):
            return (
                f"Note: evidence references a recurring or ongoing pattern "
                f"(see ticket {ticket['ticket_id']}) — may warrant escalation "
                f"beyond a single-week response."
            )
    return "No indication in current evidence that this is a recurring pattern."


def narrate_for_store_manager(state: dict, confidence_result: dict, recommendation: dict) -> str:
    """Short, action-first narrative for the store manager persona."""
    store = state.get("store")

    if not recommendation.get("recommendation_available"):
        return (
            f"Store {store}: this week's movement could not be confidently attributed "
            f"to a specific cause. {recommendation.get('reason', '')} "
            f"No action is recommended until more evidence is available."
        )

    return (
        f"Store {store} — Action Needed\n"
        f"What: {recommendation['action']}\n"
        f"Owner: {recommendation['owner']}\n"
        f"Track: {recommendation['monitoring_plan']}"
    )


def narrate_for_regional_vp(state: dict, confidence_result: dict, recommendation: dict, evidence: list) -> str:
    """Strategic, impact-framed narrative for the regional VP persona."""
    store = state.get("store")
    tier = confidence_result.get("confidence_tier", "N/A")

    if not recommendation.get("recommendation_available"):
        return (
            f"Store {store}: revenue movement flagged, but diagnosis confidence "
            f"was insufficient to attribute a clear cause "
            f"(status: {tier}). Recommend holding off on resource allocation "
            f"until follow-up evidence resolves the ambiguity."
        )

    recurrence_note = _check_recurring_pattern(state, evidence)

    return (
        f"Store {store} — {recommendation['driver']}\n"
        f"Impact: {recommendation['expected_impact']}\n"
        f"Confidence: {tier}\n"
        f"{recurrence_note}"
    )


def generate_all_narratives(state: dict, confidence_result: dict, recommendation: dict) -> dict:
    """
    Main entry point. Returns narratives for every defined persona,
    keyed by persona id. This is what a downstream API/UI layer would
    call to render persona-specific views of the same investigation.
    """
    evidence = state.get("evidence", [])

    return {
        "store_manager": narrate_for_store_manager(state, confidence_result, recommendation),
        "regional_vp": narrate_for_regional_vp(state, confidence_result, recommendation, evidence),
    }


if __name__ == "__main__":
    from react_orchestrator import run_investigation
    from abstention_policy import decide_confidence
    from filler import build_recommendation

    print("=" * 70)
    print("PERSONAS: Store 18 @ 2011-09-02")
    print("=" * 70)
    state1 = run_investigation(18, target_date="2011-09-02")
    conf1 = decide_confidence(state1)
    rec1 = build_recommendation(state1, conf1)
    narratives1 = generate_all_narratives(state1, conf1, rec1)
    for persona, text in narratives1.items():
        print(f"\n--- {persona.upper()} ---")
        print(text)

    print("\n\n" + "=" * 70)
    print("PERSONAS: Store 27 @ 2011-09-02")
    print("=" * 70)
    state2 = run_investigation(27, target_date="2011-09-02")
    conf2 = decide_confidence(state2)
    rec2 = build_recommendation(state2, conf2)
    narratives2 = generate_all_narratives(state2, conf2, rec2)
    for persona, text in narratives2.items():
        print(f"\n--- {persona.upper()} ---")
        print(text)

    print("\n\n" + "=" * 70)
    print("PERSONAS: Store 17 @ 2011-04-29 (abstained — expect graceful handling)")
    print("=" * 70)
    state3 = run_investigation(17, target_date="2011-04-29")
    conf3 = decide_confidence(state3)
    rec3 = build_recommendation(state3, conf3)
    narratives3 = generate_all_narratives(state3, conf3, rec3)
    for persona, text in narratives3.items():
        print(f"\n--- {persona.upper()} ---")
        print(text)