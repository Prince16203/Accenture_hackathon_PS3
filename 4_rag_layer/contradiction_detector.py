"""
contradiction_detector.py
Flags when retrieved evidence for the same store/week disagrees with
itself — e.g. one ticket claims a stockout, another claims full
inventory. This feeds directly into 6_confidence_layer/abstention_policy.py.

Uses a lightweight heuristic approach: opposing keyword pairs +
explicit 'contradicted' category tags, rather than a full NLI model —
appropriate for a 79-record corpus where semantic subtlety matters
less than catching the obvious cases cleanly.
"""

OPPOSING_PAIRS = [
    (["stockout", "shortage", "empty shelves", "out of stock", "unavailable"],
     ["full stock", "no stockout", "inventory levels normal", "stock levels maintained", "no shortage"]),
    (["confirmed", "verified"], ["unconfirmed", "unclear", "no formal", "not consistently"]),
    (["delayed", "delay"], ["on schedule", "on time", "received in full"]),
]


def _contains_any(text: str, phrases: list) -> bool:
    text_lower = text.lower()
    return any(p in text_lower for p in phrases)


def detect_contradictions(evidence_list: list) -> dict:
    """
    Given a list of retrieved evidence dicts (from hybrid_retriever.search()),
    checks for opposing claims within the set. Returns a verdict with
    flagged pairs if contradictions are found.
    """
    flagged_pairs = []

    # Check explicit category tags first — cheapest, most reliable signal
    explicit_contradicted = [e for e in evidence_list if e.get("category") == "contradicted"]

    # Check opposing keyword pairs across all evidence in the set
    for i, e1 in enumerate(evidence_list):
        for e2 in evidence_list[i + 1:]:
            for positive_terms, negative_terms in OPPOSING_PAIRS:
                e1_has_positive = _contains_any(e1["text"], positive_terms)
                e2_has_negative = _contains_any(e2["text"], negative_terms)
                e1_has_negative = _contains_any(e1["text"], negative_terms)
                e2_has_positive = _contains_any(e2["text"], positive_terms)

                if (e1_has_positive and e2_has_negative) or (e1_has_negative and e2_has_positive):
                    flagged_pairs.append({
                        "ticket_a": e1["ticket_id"],
                        "ticket_b": e2["ticket_id"],
                        "reason": f"Opposing claims detected re: {positive_terms[0]} vs {negative_terms[0]}",
                    })

    has_contradiction = len(flagged_pairs) > 0 or len(explicit_contradicted) > 0

    # Also flag if evidence is thin — a different reason to be cautious,
    # not technically a contradiction, but relevant to the same downstream decision
    is_thin_evidence = len(evidence_list) < 2

    return {
        "has_contradiction": has_contradiction,
        "is_thin_evidence": is_thin_evidence,
        "flagged_pairs": flagged_pairs,
        "explicit_contradicted_tickets": [e["ticket_id"] for e in explicit_contradicted],
        "recommendation": (
            "ABSTAIN_OR_FLAG_LOW_CONFIDENCE" if (has_contradiction or is_thin_evidence)
            else "PROCEED"
        ),
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hybrid_retriever import HybridRetriever

    retriever = HybridRetriever()

    print("=" * 60)
    print("Contradiction check: Store 17 (expect contradiction detected)")
    print("=" * 60)
    evidence = retriever.search("pricing seemed off inventory audit stock levels", top_k=5, filters={"store": 17})
    result = detect_contradictions(evidence)
    print(f"Has contradiction: {result['has_contradiction']}")
    print(f"Recommendation: {result['recommendation']}")
    for pair in result["flagged_pairs"]:
        print(f"  {pair['ticket_a']} vs {pair['ticket_b']}: {pair['reason']}")

    print("\n" + "=" * 60)
    print("Contradiction check: Store 18 (expect clean, no contradiction)")
    print("=" * 60)
    evidence2 = retriever.search("stockout delayed shipment weather", top_k=5, filters={"store": 18})
    result2 = detect_contradictions(evidence2)
    print(f"Has contradiction: {result2['has_contradiction']}")
    print(f"Recommendation: {result2['recommendation']}")