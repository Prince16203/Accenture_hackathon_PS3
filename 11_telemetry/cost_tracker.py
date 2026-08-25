"""
cost_tracker.py
Tracks token usage and estimated cost — currently at zero across the
board, since Phases 2-10 make no LLM calls. This file is the honest
record of that fact, and the extension point for once an LLM API key
is wired up (e.g. for richer Phase 8 narrative generation).
"""

import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TELEMETRY_LOG_PATH = PROJECT_ROOT / "11_telemetry" / "telemetry.log"

# Rough per-1K-token pricing for reference, in case/when an LLM call
# is added — update to match whichever model actually gets wired in.
PRICING_PER_1K_TOKENS = {
    "claude-haiku": {"input": 0.0008, "output": 0.004},
    "claude-sonnet": {"input": 0.003, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}


def _ensure_log_exists():
    TELEMETRY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not TELEMETRY_LOG_PATH.exists():
        TELEMETRY_LOG_PATH.touch()


def log_llm_call(model: str, input_tokens: int, output_tokens: int, step_name: str):
    """
    Records an actual LLM call's token usage and estimated cost.
    Not called anywhere yet in this codebase — Phases 2-10 have zero
    LLM calls by design. This exists as the instrumentation point for
    whenever one is added (e.g. richer narrative generation).
    """
    _ensure_log_exists()
    pricing = PRICING_PER_1K_TOKENS.get(model, {"input": 0, "output": 0})
    cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "llm_call",
        "step_name": step_name,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": round(cost, 6),
    }
    with open(TELEMETRY_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    return event


def get_cost_summary() -> dict:
    """Summarizes total LLM cost/tokens across all logged calls."""
    _ensure_log_exists()
    with open(TELEMETRY_LOG_PATH, "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]

    llm_events = [e for e in lines if e["event_type"] == "llm_call"]

    if not llm_events:
        return {
            "total_llm_calls": 0,
            "total_cost_usd": 0.0,
            "message": "No LLM calls have been made — all diagnosis logic in this pipeline is deterministic (Phases 2-10).",
        }

    total_input = sum(e["input_tokens"] for e in llm_events)
    total_output = sum(e["output_tokens"] for e in llm_events)
    total_cost = sum(e["estimated_cost_usd"] for e in llm_events)

    return {
        "total_llm_calls": len(llm_events),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": round(total_cost, 6),
    }


if __name__ == "__main__":
    print("Cost summary (expect zero — no LLM calls made yet):")
    print(get_cost_summary())