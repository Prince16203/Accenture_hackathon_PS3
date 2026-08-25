"""
react_orchestrator.py
The LangGraph state machine tying together Phases 2-5: materiality
check -> decomposition -> evidence retrieval -> contradiction check
-> hypothesis generation. Each node is deterministic (no LLM calls) —
this is intentional. The agent's "reasoning" here is control flow:
deciding whether to keep investigating or stop early, based on what
each tool returns. LLM-based narrative synthesis is Phase 8's job,
built on top of this structured output, not mixed into it.

Each node is timed via @timed_step (Phase 11 telemetry) so latency
per step is logged automatically without cluttering the orchestration
logic itself.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "2_signal_layer"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "3_tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "4_rag_layer"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "11_telemetry"))

from langgraph.graph import StateGraph, END

from state import InvestigationState
from multi_hypothesis_tracker import (
    generate_hypotheses_from_evidence,
    attach_numeric_contribution,
    rank_hypotheses,
    hypotheses_to_dicts,
)

from materiality_gate import evaluate_materiality
from contribution_ranker import rank_contributions
from hybrid_retriever import HybridRetriever
from contradiction_detector import detect_contradictions
from latency_logger import timed_step, InvestigationTimer

_retriever_cache = None


def _get_retriever() -> HybridRetriever:
    global _retriever_cache
    if _retriever_cache is None:
        _retriever_cache = HybridRetriever()
    return _retriever_cache


# ============================================================
# Nodes
# ============================================================

@timed_step("check_materiality")
def node_check_materiality(state: InvestigationState) -> InvestigationState:
    result = evaluate_materiality(state["store"], state.get("dept"), target_date=state.get("target_date"))
    state["materiality_result"] = result
    state["materiality_verdict"] = result["materiality_verdict"]
    state.setdefault("steps_taken", []).append("check_materiality")
    return state


def route_after_materiality(state: InvestigationState) -> str:
    verdict = state["materiality_verdict"]
    if verdict in ("NOT_MATERIAL",):
        return "stop_not_material"
    if verdict == "ABSTAIN":
        return "stop_abstain"
    if verdict == "COHORT_COMPARISON":
        # Sparse-history path — still worth surfacing evidence, but skip numeric decomposition
        # since a single-department sparse KPI has no meaningful sub-decomposition.
        return "retrieve_evidence"
    return "decompose"  # MATERIAL


@timed_step("decompose")
def node_decompose(state: InvestigationState) -> InvestigationState:
    result = rank_contributions(state["store"], state.get("target_date"))
    state["decomposition_result"] = result
    state["concentration_pattern"] = result.get("concentration_pattern", "unknown")
    state.setdefault("steps_taken", []).append("decompose")
    return state


@timed_step("retrieve_evidence")
def node_retrieve_evidence(state: InvestigationState) -> InvestigationState:
    retriever = _get_retriever()
    # Build a query from what we know so far — driver-type-agnostic,
    # store-filtered so we only pull relevant tickets.
    query = "revenue drop anomaly cause explanation"
    evidence = retriever.search(query, top_k=8, filters={"store": state["store"]})
    state["evidence"] = evidence
    state.setdefault("steps_taken", []).append("retrieve_evidence")
    return state


@timed_step("check_contradictions")
def node_check_contradictions(state: InvestigationState) -> InvestigationState:
    result = detect_contradictions(state.get("evidence", []))
    state["contradiction_result"] = result
    state.setdefault("steps_taken", []).append("check_contradictions")
    return state


def route_after_contradiction_check(state: InvestigationState) -> str:
    result = state["contradiction_result"]
    if result["recommendation"] == "ABSTAIN_OR_FLAG_LOW_CONFIDENCE":
        return "stop_contradicted"
    return "build_hypotheses"


@timed_step("build_hypotheses")
def node_build_hypotheses(state: InvestigationState) -> InvestigationState:
    hyps = generate_hypotheses_from_evidence(state.get("evidence", []))
    hyps = attach_numeric_contribution(hyps, state.get("decomposition_result", {}))
    hyps = rank_hypotheses(hyps)
    state["hypotheses"] = hypotheses_to_dicts(hyps)
    state["status"] = "completed"
    state.setdefault("steps_taken", []).append("build_hypotheses")
    return state


def node_stop_not_material(state: InvestigationState) -> InvestigationState:
    state["status"] = "abstained"
    state["stop_reason"] = "Movement did not meet materiality thresholds — not statistically or business significant."
    state.setdefault("steps_taken", []).append("stop_not_material")
    return state


def node_stop_abstain(state: InvestigationState) -> InvestigationState:
    state["status"] = "abstained"
    state["stop_reason"] = state["materiality_result"].get("detail", {}).get(
        "reason", "Insufficient history to evaluate this KPI."
    )
    state.setdefault("steps_taken", []).append("stop_abstain")
    return state


def node_stop_contradicted(state: InvestigationState) -> InvestigationState:
    state["status"] = "abstained"
    state["stop_reason"] = "Retrieved evidence contains contradictory or insufficient signals — cannot confidently attribute a cause."
    state.setdefault("steps_taken", []).append("stop_contradicted")
    return state


# ============================================================
# Graph assembly
# ============================================================

def build_graph():
    graph = StateGraph(InvestigationState)

    graph.add_node("check_materiality", node_check_materiality)
    graph.add_node("decompose", node_decompose)
    graph.add_node("retrieve_evidence", node_retrieve_evidence)
    graph.add_node("check_contradictions", node_check_contradictions)
    graph.add_node("build_hypotheses", node_build_hypotheses)
    graph.add_node("stop_not_material", node_stop_not_material)
    graph.add_node("stop_abstain", node_stop_abstain)
    graph.add_node("stop_contradicted", node_stop_contradicted)

    graph.set_entry_point("check_materiality")

    graph.add_conditional_edges("check_materiality", route_after_materiality, {
        "stop_not_material": "stop_not_material",
        "stop_abstain": "stop_abstain",
        "retrieve_evidence": "retrieve_evidence",
        "decompose": "decompose",
    })

    graph.add_edge("decompose", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "check_contradictions")

    graph.add_conditional_edges("check_contradictions", route_after_contradiction_check, {
        "stop_contradicted": "stop_contradicted",
        "build_hypotheses": "build_hypotheses",
    })

    graph.add_edge("build_hypotheses", END)
    graph.add_edge("stop_not_material", END)
    graph.add_edge("stop_abstain", END)
    graph.add_edge("stop_contradicted", END)

    return graph.compile()


def run_investigation(store: int, dept: int = None, target_date: str = None) -> dict:
    """Main entry point — runs the full investigation graph for a given store/dept/week."""
    with InvestigationTimer(f"store_{store}" + (f"_dept_{dept}" if dept else "")):
        app = build_graph()
        initial_state: InvestigationState = {
            "store": store, "dept": dept, "target_date": target_date,
            "steps_taken": [],
        }
        final_state = app.invoke(initial_state)
    return final_state


if __name__ == "__main__":
    print("=" * 70)
    print("INVESTIGATION: Store 18 @ 2011-09-02 (expect: completed, supply_disruption)")
    print("=" * 70)
    result = run_investigation(18, target_date="2011-09-02")
    print(f"Status: {result['status']}")
    print(f"Steps taken: {result['steps_taken']}")
    if result["status"] == "completed":
        for h in result["hypotheses"]:
            print(f"  {h['driver_type']:25s} score={h['net_support_score']:.2f}  evidence={h['supporting_ticket_ids']}")
    else:
        print(f"Stop reason: {result.get('stop_reason')}")

    print("\n" + "=" * 70)
    print("INVESTIGATION: Store 27 @ 2011-09-02 (expect: completed, multiple hypotheses)")
    print("=" * 70)
    result2 = run_investigation(27, target_date="2011-09-02")
    print(f"Status: {result2['status']}")
    print(f"Steps taken: {result2['steps_taken']}")
    if result2["status"] == "completed":
        for h in result2["hypotheses"]:
            print(f"  {h['driver_type']:25s} score={h['net_support_score']:.2f}  evidence={h['supporting_ticket_ids']}")
    else:
        print(f"Stop reason: {result2.get('stop_reason')}")

    print("\n" + "=" * 70)
    print("INVESTIGATION: Store 17 @ 2011-04-29 (expect: abstained, contradiction)")
    print("=" * 70)
    result3 = run_investigation(17, target_date="2011-04-29")
    print(f"Status: {result3['status']}")
    print(f"Steps taken: {result3['steps_taken']}")
    print(f"Stop reason: {result3.get('stop_reason')}")

    print("\n" + "=" * 70)
    print("INVESTIGATION: Store 7 / Dept 99 (expect: abstained, sparse no-baseline)")
    print("=" * 70)
    result4 = run_investigation(7, dept=99)
    print(f"Status: {result4['status']}")
    print(f"Steps taken: {result4['steps_taken']}")
    print(f"Stop reason: {result4.get('stop_reason')}")