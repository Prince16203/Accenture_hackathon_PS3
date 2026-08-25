"""
state.py
Defines the shared state object that flows through the LangGraph
investigation loop. Every node reads from and writes to this — it's
the single source of truth for "what has this investigation found
so far," used to decide what to do next and what to return at the end.
"""

from typing import TypedDict, Optional


class InvestigationState(TypedDict, total=False):
    # --- Input ---
    store: int
    dept: Optional[int]
    target_date: Optional[str]

    # --- Step 1: Materiality (Phase 2) ---
    materiality_result: dict
    materiality_verdict: str          # MATERIAL / NOT_MATERIAL / ABSTAIN / COHORT_COMPARISON

    # --- Step 2: Decomposition (Phase 3) ---
    decomposition_result: dict
    concentration_pattern: str        # single_dominant_driver / few_dominant_drivers / distributed_multi_factor

    # --- Step 3: Evidence retrieval (Phase 4) ---
    evidence: list
    contradiction_result: dict

    # --- Step 4: Hypotheses (Phase 5) ---
    hypotheses: list

    # --- Control flow / bookkeeping ---
    status: str                       # in_progress / abstained / completed
    stop_reason: Optional[str]
    steps_taken: list                 # audit trail of which nodes ran, in order — feeds telemetry later    