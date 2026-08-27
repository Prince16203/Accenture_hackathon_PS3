"""
telemetry.py
Exposes Phase 11's latency, cost, and LLM-vs-non-LLM ledger as
endpoints — the transparency layer a judge or UI could inspect to
verify the system's own claims about determinism and cost.
"""

from fastapi import APIRouter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "11_telemetry"))

from latency_logger import get_recent_latency_summary
from cost_tracker import get_cost_summary
from llm_vs_nonllm_ledger import generate_ledger_report, STEP_CLASSIFICATION

router = APIRouter()


@router.get("/telemetry/latency")
def latency_summary(n: int = 20):
    return get_recent_latency_summary(n=n)


@router.get("/telemetry/cost")
def cost_summary():
    return get_cost_summary()


@router.get("/telemetry/ledger")
def ledger_summary():
    """Returns the static step classification — what's deterministic vs. LLM across the whole pipeline."""
    return {"step_classification": STEP_CLASSIFICATION}


@router.post("/telemetry/ledger/report")
def ledger_report(steps_taken: list[str]):
    """Given a list of steps from a specific investigation, returns the LLM-vs-non-LLM breakdown for that run."""
    return generate_ledger_report(steps_taken)