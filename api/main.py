"""
main.py
FastAPI application tying together the full investigation pipeline
(Phases 2-8) plus feedback capture (Phase 9) and telemetry (Phase 11)
as HTTP endpoints. This is the layer a UI or external caller would
actually hit — everything underneath remains exactly the same
deterministic-first pipeline already validated via 12_scenarios/.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for p in ["2_signal_layer", "3_tools", "4_rag_layer", "5_agent",
          "6_confidence_layer", "7_recommendation_engine", "8_narrative_layer",
          "9_feedback_loop", "10_security", "11_telemetry"]:
    sys.path.insert(0, str(PROJECT_ROOT / p))

from routers import query, feedback, telemetry

app = FastAPI(
    title="KPI Intelligence-to-Action Engine API",
    description=(
        "Diagnoses KPI movements, ranks explanatory drivers, scores confidence, "
        "and generates persona-specific recommendations. Deterministic core "
        "(Phases 2-7) with optional LLM narrative synthesis (Phase 8)."
    ),
    version="1.0.0",
)

# Permissive CORS for local demo/dev use — a real deployment would
# restrict this to specific origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, prefix="/api", tags=["investigation"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(telemetry.router, prefix="/api", tags=["telemetry"])


@app.get("/")
def root():
    return {
        "service": "KPI Intelligence-to-Action Engine",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)