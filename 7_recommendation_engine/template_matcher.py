"""
template_matcher.py
Matches a completed investigation's top hypothesis to its corresponding
action template. Only proceeds if confidence tier is HIGH or MEDIUM —
LOW/ABSTAIN diagnoses should not produce a confident-sounding action
recommendation, matching the spirit of the abstention policy upstream.
"""

import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_PATH = PROJECT_ROOT / "7_recommendation_engine" / "action_templates.yaml"

MIN_CONFIDENCE_FOR_ACTION = {"HIGH", "MEDIUM"}


def load_templates() -> dict:
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def match_template(state: dict, confidence_result: dict) -> dict:
    """
    Given a completed investigation state and its confidence verdict,
    returns the matched action template (unfilled) or a fallback
    message if confidence is too low to act on.
    """
    templates = load_templates()

    tier = confidence_result.get("confidence_tier")
    if tier not in MIN_CONFIDENCE_FOR_ACTION:
        return {
            "matched": False,
            "reason": templates["fallback"]["low_confidence"]["message"],
            "confidence_tier": tier,
        }

    hypotheses = state.get("hypotheses", [])
    positive_hyps = [h for h in hypotheses if h["net_support_score"] > 0]
    if not positive_hyps:
        return {
            "matched": False,
            "reason": "No positively-scoring hypothesis available to match against a template.",
            "confidence_tier": tier,
        }

    top_driver_type = sorted(positive_hyps, key=lambda h: h["net_support_score"], reverse=True)[0]["driver_type"]

    if top_driver_type not in templates["templates"]:
        return {
            "matched": False,
            "reason": f"No action template defined for driver_type '{top_driver_type}'.",
            "confidence_tier": tier,
        }

    return {
        "matched": True,
        "driver_type": top_driver_type,
        "template": templates["templates"][top_driver_type],
        "confidence_tier": tier,
    }


if __name__ == "__main__":
    fake_state = {
        "hypotheses": [
            {"driver_type": "supply_disruption", "net_support_score": 4.45},
        ]
    }
    fake_confidence = {"confidence_tier": "HIGH"}
    result = match_template(fake_state, fake_confidence)
    print(f"Matched: {result['matched']}")
    print(f"Driver type: {result.get('driver_type')}")
    print(f"Label: {result['template']['driver_label']}")