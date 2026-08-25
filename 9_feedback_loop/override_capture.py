"""
override_capture.py
Captures analyst/business-user overrides of a diagnosis or
recommendation. Logs not just THAT an override happened, but what it
was corrected to and why — this is what makes the feedback loop useful
for learning, versus just a disagreement counter.

Stored as JSON Lines (one override per line) in feedback_store/ —
simple, append-only, human-readable, no DB dependency for a prototype.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEEDBACK_STORE_PATH = PROJECT_ROOT / "9_feedback_loop" / "feedback_store" / "overrides.jsonl"


def _ensure_store_exists():
    FEEDBACK_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not FEEDBACK_STORE_PATH.exists():
        FEEDBACK_STORE_PATH.touch()


def capture_override(
    store: int,
    dept: int | None,
    target_date: str | None,
    original_diagnosis: dict,
    corrected_diagnosis: str,
    correction_reason: str,
    analyst_id: str = "anonymous",
    original_confidence_tier: str = None,
) -> dict:
    """
    Records a single override event. Called when an analyst/business
    user disagrees with the system's top hypothesis and provides a
    correction.

    original_diagnosis: the system's original hypothesis dict (driver_type,
        net_support_score, etc.) — kept in full so the correction can be
        compared against exactly what was overridden.
    corrected_diagnosis: free-text or structured label for what the
        analyst believes the actual cause was.
    correction_reason: WHY they're overriding — this is the field that
        actually makes the log useful for learning, not just disagreement.
    """
    _ensure_store_exists()

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "store": store,
        "dept": dept,
        "target_date": target_date,
        "original_diagnosis": original_diagnosis,
        "original_confidence_tier": original_confidence_tier,
        "corrected_diagnosis": corrected_diagnosis,
        "correction_reason": correction_reason,
        "analyst_id": analyst_id,
    }

    with open(FEEDBACK_STORE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def load_all_overrides() -> list:
    """Reads every recorded override — used by drift_monitor.py."""
    _ensure_store_exists()
    records = []
    with open(FEEDBACK_STORE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


if __name__ == "__main__":
    # Simulate a real override — an analyst reviewing Store 27's
    # promotional_visibility diagnosis, but believing it was actually
    # driven more by the road closure than marketing (a story only
    # the analyst would know, not present in the tickets).
    record = capture_override(
        store=27,
        dept=None,
        target_date="2011-09-02",
        original_diagnosis={"driver_type": "promotional_visibility", "net_support_score": 2.0},
        original_confidence_tier="HIGH",
        corrected_diagnosis="regional_road_closure",
        correction_reason=(
            "Regional manager confirmed a road closure near Store 27 during this "
            "period limited delivery access — this wasn't captured in field reports "
            "but is a more direct cause than the marketing pause, which was a planned, "
            "pre-approved budget reallocation and not itself unusual."
        ),
        analyst_id="regional_manager_east_02",
    )
    print("Override captured:")
    for k, v in record.items():
        print(f"  {k}: {v}")

    print(f"\nTotal overrides on file: {len(load_all_overrides())}")