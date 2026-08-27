"""
query.py
The core investigation endpoint. Wraps run_investigation() through
decide_confidence() through build_recommendation() through
generate_all_narratives() into a single HTTP call, plus a role-scoped
variant that applies Phase 10 security filtering.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "5_agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "6_confidence_layer"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "7_recommendation_engine"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "8_narrative_layer"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "10_security"))

from react_orchestrator import run_investigation
from abstention_policy import decide_confidence
from filler import build_recommendation
from persona_narrator import generate_all_narratives
from access_enforcer import check_query_authorization, filter_evidence_by_access

router = APIRouter()


class InvestigationRequest(BaseModel):
    store: int
    dept: Optional[int] = None
    target_date: Optional[str] = None
    use_llm: bool = True


class SecureInvestigationRequest(InvestigationRequest):
    role: str
    user_region: Optional[str] = None
    user_store: Optional[int] = None


@router.post("/investigate")
def investigate(request: InvestigationRequest):
    """
    Runs the full pipeline for a given store/dept/week and returns the
    complete investigation result: materiality, hypotheses, confidence,
    recommendation, and persona narratives.
    """
    try:
        state = run_investigation(request.store, dept=request.dept, target_date=request.target_date)
        confidence = decide_confidence(state)
        recommendation = build_recommendation(state, confidence)
        narratives = generate_all_narratives(state, confidence, recommendation, use_llm=request.use_llm)

        return {
            "store": request.store,
            "dept": request.dept,
            "target_date": request.target_date,
            "status": state["status"],
            "materiality": state.get("materiality_result", {}),
            "steps_taken": state.get("steps_taken", []),
            "concentration_pattern": state.get("concentration_pattern"),
            "hypotheses": state.get("hypotheses", []),
            "stop_reason": state.get("stop_reason"),
            "confidence": confidence,
            "recommendation": recommendation,
            "narratives": narratives,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/investigate/secure")
def investigate_secure(request: SecureInvestigationRequest):
    """
    Role-scoped version of /investigate. Checks authorization BEFORE
    running the pipeline; if authorized, filters retrieved evidence
    (and therefore hypotheses/recommendations derived from it) to only
    what the requesting role is entitled to see.
    """
    auth = check_query_authorization(
        request.role, store=request.store,
        user_region=request.user_region, user_store=request.user_store,
    )
    if not auth["authorized"]:
        raise HTTPException(status_code=403, detail=auth["reason"])

    try:
        state = run_investigation(request.store, dept=request.dept, target_date=request.target_date)

        if state.get("evidence"):
            access_result = filter_evidence_by_access(state["evidence"], request.role)
            state["evidence"] = access_result["filtered_evidence"]
            state["withheld_evidence_count"] = access_result["withheld_count"]

        confidence = decide_confidence(state)
        recommendation = build_recommendation(state, confidence)
        narratives = generate_all_narratives(state, confidence, recommendation, use_llm=request.use_llm)

        return {
            "authorized": True,
            "role": request.role,
            "store": request.store,
            "withheld_evidence_count": state.get("withheld_evidence_count", 0),
            "status": state["status"],
            "hypotheses": state.get("hypotheses", []),
            "confidence": confidence,
            "recommendation": recommendation,
            "narratives": narratives,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/stores")
def list_known_scenario_stores():
    """Convenience endpoint listing the stores with known, validated demo scenarios — useful for a UI dropdown."""
    return {
        "scenarios": [
            {"store": 18, "target_date": "2011-09-02", "label": "Clean single-cause (weather stockout)"},
            {"store": 27, "target_date": "2011-09-02", "label": "Multi-factor (marketing/staffing/competitor)"},
            {"store": 17, "target_date": "2011-04-29", "label": "Low-confidence (contradictory evidence)"},
            {"store": 3, "dept": 83, "target_date": None, "label": "Sparse history (cohort comparison)"},
            {"store": 7, "dept": 99, "target_date": None, "label": "Sparse history (no baseline, abstain)"},
            {"store": 41, "target_date": None, "label": "Security scenario (HR-restricted evidence)"},
        ]
    }