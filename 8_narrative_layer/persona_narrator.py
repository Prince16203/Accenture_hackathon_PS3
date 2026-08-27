"""
persona_narrator.py
Generates persona-specific narratives from the same underlying
investigation + confidence + recommendation data.

Two-tier approach:
  1. If an LLM is available (ANTHROPIC_API_KEY set), uses it to phrase
     the already-computed facts naturally — the LLM does NOT decide
     anything, it only rephrases what Phases 2-7 already determined.
  2. If no LLM is available, or the call fails for any reason, falls
     back to the original deterministic template narrative. The demo
     never breaks because of this layer.

This is the ONLY place in the entire codebase where a generative LLM
call happens. Every other phase remains fully deterministic — see
11_telemetry/llm_vs_nonllm_ledger.py for the live proof.
"""

import yaml
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONA_PATH = PROJECT_ROOT / "8_narrative_layer" / "persona_profiles.yaml"

sys.path.insert(0, str(PROJECT_ROOT / "5_agent"))
sys.path.insert(0, str(PROJECT_ROOT / "6_confidence_layer"))
sys.path.insert(0, str(PROJECT_ROOT / "7_recommendation_engine"))
sys.path.insert(0, str(PROJECT_ROOT / "8_narrative_layer"))
sys.path.insert(0, str(PROJECT_ROOT / "11_telemetry"))

from llm_client import generate_persona_narrative, is_llm_available
from cost_tracker import log_llm_call
from latency_logger import log_latency_event


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


# ============================================================
# Template-based narratives (deterministic fallback / default)
# ============================================================

def _template_store_manager(state: dict, confidence_result: dict, recommendation: dict) -> str:
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


def _template_regional_vp(state: dict, confidence_result: dict, recommendation: dict, evidence: list) -> str:
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


# ============================================================
# LLM-based narratives — phrases the SAME facts, doesn't decide them
# ============================================================

STORE_MANAGER_SYSTEM_PROMPT = """You write short, direct operational messages for retail store managers.
You are given a set of ALREADY-DECIDED facts: a diagnosis, a recommended action, an owner, and a monitoring plan.
Your only job is to phrase these facts as a clear, natural, action-first message under 80 words.

STRICT RULES:
- Do not add any fact, number, cause, or recommendation not given to you.
- Do not soften, hedge, or change the confidence level stated.
- Do not invent additional context, causes, or next steps.
- If told there is no recommendation available, say so plainly and do not suggest an action anyway.
- Write only the message itself, no preamble like "Here is the message:"."""

REGIONAL_VP_SYSTEM_PROMPT = """You write short, business-impact-framed summaries for a retail regional VP.
You are given ALREADY-DECIDED facts: a diagnosis, its financial impact, a confidence tier, and a recurrence note.
Your only job is to phrase these facts as a clear, concise strategic summary under 100 words.

STRICT RULES:
- Do not add any fact, number, cause, or recommendation not given to you.
- Do not soften, hedge, or change the confidence level or dollar figures stated.
- Do not invent additional financial context or strategic implications beyond what's given.
- If told confidence was insufficient, say so plainly and do not offer a diagnosis anyway.
- Write only the summary itself, no preamble like "Here is the summary:"."""


def _llm_store_manager(state: dict, confidence_result: dict, recommendation: dict) -> tuple[str, dict]:
    """Returns (narrative_text, llm_call_metadata). Falls back to template on any failure."""
    store = state.get("store")

    if not recommendation.get("recommendation_available"):
        facts = f"Store: {store}\nStatus: No confident diagnosis available.\nReason: {recommendation.get('reason', '')}"
    else:
        facts = (
            f"Store: {store}\n"
            f"Recommended action: {recommendation['action']}\n"
            f"Owner: {recommendation['owner']}\n"
            f"Monitoring plan: {recommendation['monitoring_plan']}"
        )

    result = generate_persona_narrative(STORE_MANAGER_SYSTEM_PROMPT, facts, step_name="narrate_store_manager")

    if result["success"]:
        return result["text"], result
    else:
        return _template_store_manager(state, confidence_result, recommendation), result


def _llm_regional_vp(state: dict, confidence_result: dict, recommendation: dict, evidence: list) -> tuple[str, dict]:
    """Returns (narrative_text, llm_call_metadata). Falls back to template on any failure."""
    store = state.get("store")
    tier = confidence_result.get("confidence_tier", "N/A")

    if not recommendation.get("recommendation_available"):
        facts = f"Store: {store}\nStatus: Confidence insufficient to attribute a cause.\nConfidence tier: {tier}"
    else:
        recurrence_note = _check_recurring_pattern(state, evidence)
        facts = (
            f"Store: {store}\n"
            f"Diagnosis: {recommendation['driver']}\n"
            f"Financial impact: {recommendation['expected_impact']}\n"
            f"Confidence tier: {tier}\n"
            f"Recurrence note: {recurrence_note}"
        )

    result = generate_persona_narrative(REGIONAL_VP_SYSTEM_PROMPT, facts, step_name="narrate_regional_vp")

    if result["success"]:
        return result["text"], result
    else:
        return _template_regional_vp(state, confidence_result, recommendation, evidence), result


def _log_llm_result(metadata: dict, step_name: str):
    """Logs telemetry for an LLM call attempt — cost/tokens if it succeeded, latency either way."""
    log_latency_event(step_name, metadata.get("latency_ms", 0),
                       metadata={"success": metadata.get("success", False)})
    if metadata.get("success"):
        log_llm_call(
            model="claude-haiku-4-5",
            input_tokens=metadata.get("input_tokens", 0),
            output_tokens=metadata.get("output_tokens", 0),
            step_name=step_name,
        )


# ============================================================
# Main entry point
# ============================================================

def generate_all_narratives(state: dict, confidence_result: dict, recommendation: dict,
                             use_llm: bool = True) -> dict:
    """
    Main entry point. Returns narratives for every defined persona,
    keyed by persona id, plus metadata on whether the LLM or the
    template fallback was actually used for each.

    use_llm=True (default): attempts the LLM call, falls back to
    template automatically on any failure — safe default for the demo.
    use_llm=False: skips the LLM entirely, always uses templates —
    useful for testing the deterministic path in isolation.
    """
    evidence = state.get("evidence", [])

    if use_llm and is_llm_available():
        sm_text, sm_meta = _llm_store_manager(state, confidence_result, recommendation)
        _log_llm_result(sm_meta, "narrate_store_manager")

        vp_text, vp_meta = _llm_regional_vp(state, confidence_result, recommendation, evidence)
        _log_llm_result(vp_meta, "narrate_regional_vp")

        return {
            "store_manager": sm_text,
            "regional_vp": vp_text,
            "_meta": {
                "store_manager_source": "llm" if sm_meta["success"] else "template_fallback",
                "regional_vp_source": "llm" if vp_meta["success"] else "template_fallback",
            },
        }

    return {
        "store_manager": _template_store_manager(state, confidence_result, recommendation),
        "regional_vp": _template_regional_vp(state, confidence_result, recommendation, evidence),
        "_meta": {
            "store_manager_source": "template",
            "regional_vp_source": "template",
        },
    }


if __name__ == "__main__":
    from react_orchestrator import run_investigation
    from abstention_policy import decide_confidence
    from filler import build_recommendation

    print(f"LLM available: {is_llm_available()}\n")

    print("=" * 70)
    print("PERSONAS: Store 18 @ 2011-09-02")
    print("=" * 70)
    state1 = run_investigation(18, target_date="2011-09-02")
    conf1 = decide_confidence(state1)
    rec1 = build_recommendation(state1, conf1)
    narratives1 = generate_all_narratives(state1, conf1, rec1)
    print(f"Sources used: {narratives1['_meta']}\n")
    for persona in ["store_manager", "regional_vp"]:
        print(f"--- {persona.upper()} ---")
        print(narratives1[persona])
        print()

    print("\n" + "=" * 70)
    print("PERSONAS: Store 27 @ 2011-09-02")
    print("=" * 70)
    state2 = run_investigation(27, target_date="2011-09-02")
    conf2 = decide_confidence(state2)
    rec2 = build_recommendation(state2, conf2)
    narratives2 = generate_all_narratives(state2, conf2, rec2)
    print(f"Sources used: {narratives2['_meta']}\n")
    for persona in ["store_manager", "regional_vp"]:
        print(f"--- {persona.upper()} ---")
        print(narratives2[persona])
        print()

    print("\n" + "=" * 70)
    print("PERSONAS: Store 17 @ 2011-04-29 (abstained)")
    print("=" * 70)
    state3 = run_investigation(17, target_date="2011-04-29")
    conf3 = decide_confidence(state3)
    rec3 = build_recommendation(state3, conf3)
    narratives3 = generate_all_narratives(state3, conf3, rec3)
    print(f"Sources used: {narratives3['_meta']}\n")
    for persona in ["store_manager", "regional_vp"]:
        print(f"--- {persona.upper()} ---")
        print(narratives3[persona])
        print()