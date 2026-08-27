"""
llm_vs_nonllm_ledger.py
The explicit breakdown the spec asks for: what ran as deterministic
logic/stats/SQL/retrieval vs. what ran as an LLM call, per investigation.
This is what lets you say, with a real audit trail, exactly how much
(or how little) of a diagnosis depended on an LLM.
"""

# Static registry of every step in the pipeline and its classification.
# Updated manually as new steps are added — deliberately explicit rather
# than inferred, since misclassifying a step here undermines the whole
# point of the ledger.
STEP_CLASSIFICATION = {
    "check_materiality": {"type": "deterministic_stats", "phase": "2_signal_layer"},
    "decompose": {"type": "deterministic_sql", "phase": "3_tools"},
    "retrieve_evidence": {"type": "retrieval_embedding", "phase": "4_rag_layer",
                           "note": "Uses a sentence-transformer embedding model for semantic search — "
                                   "not a generative LLM call, no text is generated."},
    "check_contradictions": {"type": "deterministic_heuristic", "phase": "4_rag_layer"},
    "build_hypotheses": {"type": "deterministic_logic", "phase": "5_agent"},
    "score_agreement": {"type": "deterministic_logic", "phase": "6_confidence_layer"},
    "score_match_strength": {"type": "deterministic_logic", "phase": "6_confidence_layer"},
    "check_self_consistency": {"type": "retrieval_embedding", "phase": "6_confidence_layer",
                                "note": "Re-runs retrieval (embedding-based), not an LLM generation call."},
    "match_template": {"type": "deterministic_logic", "phase": "7_recommendation_engine"},
    "fill_recommendation": {"type": "deterministic_templating", "phase": "7_recommendation_engine"},
    "narrate_personas": {"type": "deterministic_templating", "phase": "8_narrative_layer",
                          "note": "Currently template-based. LLM extension point exists but is not active — "
                                  "see persona_narrator.py docstring."},
    "narrate_store_manager": {"type": "generative_llm", "phase": "8_narrative_layer",
                               "note": "Phrases already-computed facts for the store manager persona. "
                                       "Falls back to deterministic template if LLM unavailable."},
    "narrate_regional_vp": {"type": "generative_llm", "phase": "8_narrative_layer",
                             "note": "Phrases already-computed facts for the regional VP persona. "
                                     "Falls back to deterministic template if LLM unavailable."},
}


def generate_ledger_report(steps_taken: list) -> dict:
    """
    Given a list of step names actually executed in an investigation
    (from InvestigationState['steps_taken']), classifies each and
    produces a summary showing the LLM vs. non-LLM breakdown.
    """
    classified = []
    llm_step_count = 0
    non_llm_step_count = 0

    for step in steps_taken:
        info = STEP_CLASSIFICATION.get(step, {"type": "unclassified", "phase": "unknown"})
        is_llm = info["type"] == "generative_llm"
        classified.append({"step": step, **info, "is_llm_call": is_llm})
        if is_llm:
            llm_step_count += 1
        else:
            non_llm_step_count += 1

    total = len(steps_taken)
    return {
        "total_steps": total,
        "llm_steps": llm_step_count,
        "non_llm_steps": non_llm_step_count,
        "llm_percentage": round((llm_step_count / total * 100), 1) if total else 0,
        "step_breakdown": classified,
        "summary_statement": (
            f"{non_llm_step_count} of {total} steps ({100 - round(llm_step_count/total*100,1) if total else 0}%) "
            f"in this investigation were deterministic (statistics, SQL, embedding-based retrieval, or "
            f"rule-based logic). {llm_step_count} step(s) involved a generative LLM call."
        ),
    }


if __name__ == "__main__":
    fake_steps = ["check_materiality", "decompose", "retrieve_evidence", "check_contradictions", "build_hypotheses"]
    report = generate_ledger_report(fake_steps)
    print(report["summary_statement"])
    print()
    for step in report["step_breakdown"]:
        print(f"  [{step['type']:22s}] {step['step']} ({step['phase']})")