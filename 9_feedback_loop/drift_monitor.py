"""
drift_monitor.py
Analyzes accumulated overrides to check for signs of model/data drift —
specifically, whether override rates are creeping up for diagnoses the
system claimed HIGH confidence in. A rising override rate on HIGH-tier
diagnoses is the strongest possible drift signal: it means the system's
confidence calibration itself is becoming unreliable, not just that
individual answers are sometimes wrong.
"""

from pathlib import Path
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from override_capture import load_all_overrides

# If more than this fraction of HIGH-confidence diagnoses get overridden,
# flag it as a drift concern worth investigating.
HIGH_CONFIDENCE_OVERRIDE_ALERT_THRESHOLD = 0.20


def analyze_drift(total_investigations_run: int = None) -> dict:
    """
    Computes override statistics grouped by confidence tier. If
    total_investigations_run is provided, also computes an actual
    override RATE (overrides / total investigations at that tier) —
    without it, this can only report override COUNTS, which is a
    weaker signal (can't distinguish "10 overrides out of 10 HIGH
    diagnoses" from "10 overrides out of 1000").
    """
    overrides = load_all_overrides()

    if not overrides:
        return {
            "total_overrides": 0,
            "message": "No overrides recorded yet — drift cannot be assessed.",
        }

    by_tier = Counter(o.get("original_confidence_tier", "UNKNOWN") for o in overrides)

    driver_correction_pairs = defaultdict(Counter)
    for o in overrides:
        original_driver = o.get("original_diagnosis", {}).get("driver_type", "unknown")
        corrected = o.get("corrected_diagnosis", "unknown")
        driver_correction_pairs[original_driver][corrected] += 1

    result = {
        "total_overrides": len(overrides),
        "overrides_by_original_confidence_tier": dict(by_tier),
        "common_corrections": {
            original: dict(corrections)
            for original, corrections in driver_correction_pairs.items()
        },
    }

    high_tier_overrides = by_tier.get("HIGH", 0)
    if total_investigations_run:
        high_tier_rate = high_tier_overrides / total_investigations_run
        result["high_confidence_override_rate"] = round(high_tier_rate, 3)
        result["drift_alert"] = high_tier_rate > HIGH_CONFIDENCE_OVERRIDE_ALERT_THRESHOLD
        if result["drift_alert"]:
            result["drift_alert_message"] = (
                f"HIGH-confidence override rate ({high_tier_rate:.1%}) exceeds "
                f"alert threshold ({HIGH_CONFIDENCE_OVERRIDE_ALERT_THRESHOLD:.0%}) — "
                f"confidence calibration may need review."
            )
    else:
        result["note"] = (
            "total_investigations_run not provided — reporting counts only, "
            "not rates. Pass total investigation count for a real drift rate."
        )

    return result


if __name__ == "__main__":
    # With just the one simulated override from override_capture.py's
    # self-test, this demonstrates the reporting structure. In a real
    # demo, run several investigations first, override a couple, then
    # call this with the real total count.
    result = analyze_drift(total_investigations_run=10)
    print("Drift analysis:")
    for k, v in result.items():
        print(f"  {k}: {v}")