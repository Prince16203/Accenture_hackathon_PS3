"""
match_strength.py
Evaluates how strong the retrieval match actually was — not just
whether evidence exists, but how relevant it was (fused BM25+dense
score) and how much of it there is. Weak, thin, or barely-relevant
evidence should cap confidence even if a hypothesis technically "wins."

Also applies the confidence_cap from sparse_history_fallback.py —
a cohort-proxy comparison is inherently weaker evidence than a KPI's
own sufficient history, and should never score as high as a standard-path result.
"""


def score_match_strength(evidence: list, materiality_path: str = "standard") -> dict:
    """
    evidence: list of retrieved ticket dicts, each with a 'fused_score' key
    materiality_path: one of 'standard', 'sparse_history_fallback' —
      determines whether a confidence ceiling applies regardless of match quality.
    """
    if not evidence:
        return {
            "match_strength": "none",
            "score": 0.0,
            "reasoning": "No evidence retrieved.",
            "confidence_ceiling": 1.0,
        }

    scores = [e.get("fused_score", 0) for e in evidence]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    n_evidence = len(evidence)

    # Thresholds are calibrated empirically against this corpus's observed
    # fused_score range (roughly 0.01-0.035 for relevant hits, per Phase 4 runs)
    if max_score >= 0.030 and n_evidence >= 3:
        match_strength = "strong"
        score = 1.0
    elif max_score >= 0.020 and n_evidence >= 2:
        match_strength = "moderate"
        score = 0.6
    else:
        match_strength = "weak"
        score = 0.3

    confidence_ceiling = 1.0
    ceiling_reason = None
    if materiality_path == "sparse_history_fallback":
        confidence_ceiling = 0.6
        ceiling_reason = "Evidence supports a sparse-history KPI evaluated via cohort proxy — confidence capped regardless of match quality."

    return {
        "match_strength": match_strength,
        "score": score,
        "avg_fused_score": round(avg_score, 5),
        "max_fused_score": round(max_score, 5),
        "n_evidence": n_evidence,
        "confidence_ceiling": confidence_ceiling,
        "ceiling_reason": ceiling_reason,
    }


if __name__ == "__main__":
    fake_evidence = [
        {"fused_score": 0.032, "ticket_id": "T0001"},
        {"fused_score": 0.031, "ticket_id": "T0003"},
        {"fused_score": 0.032, "ticket_id": "T0004"},
    ]
    print(score_match_strength(fake_evidence, materiality_path="standard"))
    print(score_match_strength(fake_evidence, materiality_path="sparse_history_fallback"))
    print(score_match_strength([], materiality_path="standard"))