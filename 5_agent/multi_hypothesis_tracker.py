"""
multi_hypothesis_tracker.py
Generates and ranks candidate hypotheses from decomposition + evidence,
instead of collapsing to the first plausible ticket. Each hypothesis
is grounded in either a numeric driver (contribution ranking) or a
qualitative one (a ticket category), and is scored by how much
corroborating evidence supports it — this is what handles genuinely
multi-factor movements without picking a single answer prematurely.

A ticket can also REFUTE a hypothesis rather than support it — e.g. an
'inventory' category ticket that explicitly says stock was normal
argues AGAINST a supply_disruption hypothesis, not for one. Refutation
is detected via keyword phrases and tracked separately, so a
hypothesis's score reflects net evidence, not just category volume.
"""

from dataclasses import dataclass, field
from collections import defaultdict


CATEGORY_TO_DRIVER_TYPE = {
    "stockout": "supply_disruption",
    "supply_chain": "supply_disruption",
    "marketing": "promotional_visibility",
    "staffing": "operational_capacity",
    "competitor": "competitive_pressure",
    "customer_complaint": "supply_disruption",
    "customer_feedback": "promotional_visibility",
    "inventory": "supply_disruption",   # can support OR refute — see REFUTATION_PHRASES
    "resolution": "supply_disruption",
    "vague": "unclassified",
    "contradicted": "unclassified",
}

# Phrases that indicate a ticket is arguing AGAINST its category's default
# hypothesis (e.g. an "inventory" ticket saying stock was fine refutes
# a supply_disruption hypothesis rather than supporting one).
REFUTATION_PHRASES = [
    "no stockout", "inventory levels normal", "stock levels maintained",
    "no shortage", "received on schedule", "received in full",
    "full stock", "on time", "no delays",
]


@dataclass
class Hypothesis:
    driver_type: str
    supporting_ticket_ids: list = field(default_factory=list)
    contradicting_ticket_ids: list = field(default_factory=list)
    supporting_dept_contribution_pct: float = 0.0
    evidence_count: int = 0

    def net_support_score(self) -> float:
        """Supporting evidence adds, contradicting evidence subtracts, numeric contribution adds a bonus."""
        base = self.evidence_count - (1.0 * len(self.contradicting_ticket_ids))
        return base + (self.supporting_dept_contribution_pct / 20.0)


def _is_refutation(text: str) -> bool:
    """Checks if a ticket's text contains language that refutes its category's default hypothesis."""
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in REFUTATION_PHRASES)


def generate_hypotheses_from_evidence(evidence: list) -> list:
    grouped = defaultdict(list)
    refuting = defaultdict(list)

    for ticket in evidence:
        driver_type = CATEGORY_TO_DRIVER_TYPE.get(ticket["category"], "unclassified")
        if driver_type == "unclassified":
            continue

        ticket_text = ticket.get("text", "")

        if _is_refutation(ticket_text):
            refuting[driver_type].append(ticket)
        else:
            grouped[driver_type].append(ticket)

    # sorted() forces deterministic order regardless of PYTHONHASHSEED —
    # without this, ties in net_support_score resolve differently
    # between separate process runs.
    all_driver_types = sorted(set(list(grouped.keys()) + list(refuting.keys())))

    hypotheses = []
    for driver_type in all_driver_types:
        supporting_tickets = grouped.get(driver_type, [])
        refuting_tickets = refuting.get(driver_type, [])

        hyp = Hypothesis(
            driver_type=driver_type,
            supporting_ticket_ids=[t["ticket_id"] for t in supporting_tickets],
            contradicting_ticket_ids=[t["ticket_id"] for t in refuting_tickets],
            evidence_count=len(supporting_tickets),
        )
        hypotheses.append(hyp)

    return hypotheses



def attach_numeric_contribution(hypotheses: list, decomposition_result: dict) -> list:
    """
    If decomposition shows a concentrated driver (single_dominant_driver
    or few_dominant_drivers), boosts hypotheses that plausibly align
    with a supply/operational explanation, since a concentrated numeric
    pattern is more consistent with one specific department issue than
    a broad marketing/staffing story.
    """
    if not decomposition_result or "ranked_contributors" not in decomposition_result:
        return hypotheses

    top_contribution = abs(decomposition_result["ranked_contributors"][0]["contribution_pct"]) \
        if decomposition_result["ranked_contributors"] else 0

    for hyp in hypotheses:
        if hyp.driver_type == "supply_disruption":
            hyp.supporting_dept_contribution_pct = top_contribution

    return hypotheses


def rank_hypotheses(hypotheses: list) -> list:
    """Sorts by net_support_score, strongest first. Secondary key (driver_type,
    alphabetical) breaks ties deterministically instead of relying on
    whatever order hypotheses happened to be built in."""
    return sorted(hypotheses, key=lambda h: (-h.net_support_score(), h.driver_type))


def hypotheses_to_dicts(hypotheses: list) -> list:
    """Serializes Hypothesis objects for storage in InvestigationState (dataclasses don't survive dict copies cleanly)."""
    return [
        {
            "driver_type": h.driver_type,
            "supporting_ticket_ids": h.supporting_ticket_ids,
            "contradicting_ticket_ids": h.contradicting_ticket_ids,
            "supporting_dept_contribution_pct": h.supporting_dept_contribution_pct,
            "evidence_count": h.evidence_count,
            "net_support_score": round(h.net_support_score(), 3),
        }
        for h in hypotheses
    ]


if __name__ == "__main__":
    # Self-test with fake evidence resembling Store 27's actual tickets —
    # T0007 (inventory, "no stockout on record") should now show up as
    # CONTRADICTING supply_disruption, not supporting it.
    fake_evidence = [
        {"ticket_id": "T0006", "category": "marketing",
         "text": "Regional marketing paused radio and local flyer spend for Store 27."},
        {"ticket_id": "T0010", "category": "customer_feedback",
         "text": "Handful of customer surveys this week mention 'didn't know about the sale'."},
        {"ticket_id": "T0007", "category": "inventory",
         "text": "MarkDown items received on schedule at Store 27 this period - no stockout on record. Inventory levels normal."},
        {"ticket_id": "T0008", "category": "staffing",
         "text": "Store 27 reported two open cashier positions unfilled for third consecutive week."},
        {"ticket_id": "T0009", "category": "competitor",
         "text": "Field rep noted a competing discount retailer opened a temporary pop-up location."},
    ]
    hyps = generate_hypotheses_from_evidence(fake_evidence)
    ranked = rank_hypotheses(hyps)
    print("Self-test results (T0007 should be under 'contradicting_ticket_ids', not 'supporting'):")
    for h in hypotheses_to_dicts(ranked):
        print(h)