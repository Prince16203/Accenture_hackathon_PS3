"""
feedback.py
Exposes Phase 9's override capture and drift monitoring as endpoints —
lets a UI submit an analyst correction and view accumulated drift stats.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "9_feedback_loop"))

from override_capture import capture_override, load_all_overrides
from drift_monitor import analyze_drift

router = APIRouter()


class OverrideRequest(BaseModel):
    store: int
    dept: Optional[int] = None
    target_date: Optional[str] = None
    original_driver_type: str
    original_net_support_score: float
    original_confidence_tier: str
    corrected_diagnosis: str
    correction_reason: str
    analyst_id: str = "anonymous"


@router.post("/feedback/override")
def submit_override(request: OverrideRequest):
    try:
        record = capture_override(
            store=request.store,
            dept=request.dept,
            target_date=request.target_date,
            original_diagnosis={
                "driver_type": request.original_driver_type,
                "net_support_score": request.original_net_support_score,
            },
            original_confidence_tier=request.original_confidence_tier,
            corrected_diagnosis=request.corrected_diagnosis,
            correction_reason=request.correction_reason,
            analyst_id=request.analyst_id,
        )
        return {"captured": True, "record": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/feedback/overrides")
def list_overrides():
    return {"overrides": load_all_overrides()}


@router.get("/feedback/drift")
def drift_summary(total_investigations_run: Optional[int] = None):
    return analyze_drift(total_investigations_run=total_investigations_run)