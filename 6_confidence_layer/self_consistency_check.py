"""
self_consistency_check.py
Re-runs evidence retrieval with several differently-phrased queries for
the same store/week, and checks whether the SAME top hypothesis emerges
each time. If the answer changes depending on how you ask, that's a
sign the original result was fragile, not robust — this is the
"double-check yourself" pattern before committing to an answer.
"""

from pathlib import Path
import sys
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "4_rag_layer"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "5_agent"))

from hybrid_retriever import HybridRetriever
from multi_hypothesis_tracker import (
    generate_hypotheses_from_evidence, rank_hypotheses, hypotheses_to_dicts
)

# Varied phrasings of "why did revenue move" — deliberately different
# wording/emphasis so this actually tests robustness, not just re-runs
# the identical query.
QUERY_VARIANTS = [
    "revenue drop anomaly cause explanation",
    "what happened this week sales decline",
    "store performance issue root cause",
]

_retriever_cache = None


def _get_retriever() -> HybridRetriever:
    global _retriever_cache
    if _retriever_cache is None:
        _retriever_cache = HybridRetriever()
    return _retriever_cache


def check_self_consistency(store: int, decomposition_result: dict = None) -> dict:
    """
    Runs hypothesis generation across multiple query phrasings for the
    same store, and checks how often the same top hypothesis wins.
    Returns a consistency_score (0-1) = fraction of trials agreeing
    with the majority answer.
    """
    retriever = _get_retriever()
    top_hypotheses_per_trial = []

    for query in QUERY_VARIANTS:
        evidence = retriever.search(query, top_k=8, filters={"store": store})
        hyps = generate_hypotheses_from_evidence(evidence)
        if decomposition_result:
            from multi_hypothesis_tracker import attach_numeric_contribution
            hyps = attach_numeric_contribution(hyps, decomposition_result)
        ranked = rank_hypotheses(hyps)
        ranked_dicts = hypotheses_to_dicts(ranked)

        positive = [h for h in ranked_dicts if h["net_support_score"] > 0]
        top = positive[0]["driver_type"] if positive else "none"
        top_hypotheses_per_trial.append(top)

        counts = Counter(top_hypotheses_per_trial)
        majority_answer, majority_count = counts.most_common(1)[0]
        consistency_score = majority_count / len(QUERY_VARIANTS)

    return {
        "consistency_score": round(consistency_score, 3),
        "majority_answer": majority_answer,
        "trial_results": top_hypotheses_per_trial,
        # Compare counts directly instead of comparing floats to a
        # threshold — avoids floating-point boundary issues like
        # 2/3 = 0.6667 failing a >= 0.67 check by a hair.
        "is_consistent": majority_count > len(QUERY_VARIANTS) / 2,
    }


if __name__ == "__main__":
    print("Store 18 self-consistency:")
    print(check_self_consistency(18))

    print("\nStore 27 self-consistency:")
    print(check_self_consistency(27))