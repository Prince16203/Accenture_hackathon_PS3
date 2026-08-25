"""
latency_logger.py
Times each step of an investigation and logs latency. Wraps
react_orchestrator's node functions via a decorator so timing is
captured automatically without cluttering the orchestration logic
itself with manual start/stop calls.
"""

import time
import functools
import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TELEMETRY_LOG_PATH = PROJECT_ROOT / "11_telemetry" / "telemetry.log"


def _ensure_log_exists():
    TELEMETRY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not TELEMETRY_LOG_PATH.exists():
        TELEMETRY_LOG_PATH.touch()


def log_latency_event(step_name: str, duration_ms: float, metadata: dict = None):
    """Appends one timing event to the telemetry log as a JSON line."""
    _ensure_log_exists()
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "latency",
        "step_name": step_name,
        "duration_ms": round(duration_ms, 2),
        "metadata": metadata or {},
    }
    with open(TELEMETRY_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    return event


def timed_step(step_name: str):
    """
    Decorator — wraps a function, times its execution, logs the result,
    and returns the original result unchanged. Use on any node function
    in react_orchestrator.py to get automatic per-step latency tracking.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            log_latency_event(step_name, duration_ms)
            return result
        return wrapper
    return decorator


class InvestigationTimer:
    """
    Context manager for timing an entire investigation run as one unit,
    in addition to per-step timing captured via @timed_step on individual
    nodes. Use around the top-level run_investigation() call.
    """
    def __init__(self, label: str):
        self.label = label
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start) * 1000
        log_latency_event(f"full_investigation:{self.label}", duration_ms)


def get_recent_latency_summary(n: int = 20) -> dict:
    """Reads the last n latency events and summarizes by step_name."""
    _ensure_log_exists()
    with open(TELEMETRY_LOG_PATH, "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]

    latency_events = [e for e in lines if e["event_type"] == "latency"][-n:]

    by_step = {}
    for e in latency_events:
        step = e["step_name"]
        by_step.setdefault(step, []).append(e["duration_ms"])

    summary = {}
    for step, durations in by_step.items():
        summary[step] = {
            "count": len(durations),
            "avg_ms": round(sum(durations) / len(durations), 2),
            "max_ms": round(max(durations), 2),
        }
    return summary


if __name__ == "__main__":
    with InvestigationTimer("test_run"):
        time.sleep(0.05)  # simulate work

    log_latency_event("fake_step_a", 12.3)
    log_latency_event("fake_step_a", 15.1)
    log_latency_event("fake_step_b", 200.0)

    print("Recent latency summary:")
    for step, stats in get_recent_latency_summary().items():
        print(f"  {step}: {stats}")