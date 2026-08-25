import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
"""
hybrid_retriever.py
Combines BM25 (keyword) and dense (semantic) retrieval over the
field_reports evidence store, fused via Reciprocal Rank Fusion (RRF).
This is what lets the agent find relevant tickets whether the query
uses exact terminology from the tickets or just describes the situation
in different words.
"""

import pandas as pd
from rank_bm25 import BM25Okapi
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embedder import get_model, get_collection, load_field_reports

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _tokenize(text: str) -> list:
    return text.lower().replace(",", "").replace(".", "").split()


class HybridRetriever:
    def __init__(self):
        self.df = load_field_reports()
        self.collection = get_collection()
        self.model = get_model()

        corpus = [_tokenize(t) for t in self.df["text"].tolist()]
        self.bm25 = BM25Okapi(corpus)
        self.ticket_ids = self.df["ticket_id"].tolist()

    def _bm25_search(self, query: str, top_k: int = 10) -> list:
        """Returns [(ticket_id, rank), ...] sorted by BM25 relevance."""
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self.ticket_ids, scores), key=lambda x: x[1], reverse=True)
        return [(tid, i + 1) for i, (tid, score) in enumerate(ranked[:top_k])]

    def _dense_search(self, query: str, top_k: int = 10) -> list:
        """Returns [(ticket_id, rank), ...] sorted by embedding similarity."""
        query_emb = self.model.encode([query]).tolist()
        results = self.collection.query(query_embeddings=query_emb, n_results=top_k)
        ids = results["ids"][0]
        return [(tid, i + 1) for i, tid in enumerate(ids)]

    def search(self, query: str, top_k: int = 5, rrf_k: int = 60,
               filters: dict = None) -> list:
        bm25_ranks = dict(self._bm25_search(query, top_k=20))
        dense_ranks = dict(self._dense_search(query, top_k=20))

        # Sort explicitly for deterministic iteration — sets have
        # randomized order between Python process runs, which was
        # silently breaking ties differently on every run.
        all_ids = sorted(set(bm25_ranks) | set(dense_ranks))
        fused_scores = {}
        for tid in all_ids:
            score = 0.0
            if tid in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[tid])
            if tid in dense_ranks:
                score += 1.0 / (rrf_k + dense_ranks[tid])
            fused_scores[tid] = score

        # Secondary sort key (ticket_id) breaks ties deterministically
        # instead of relying on dict/set insertion order.
        ranked_ids = sorted(fused_scores.items(), key=lambda x: (-x[1], x[0]))

        results = []
        for tid, score in ranked_ids:
            row = self.df[self.df["ticket_id"] == tid].iloc[0]

            if filters:
                skip = False
                for key, val in filters.items():
                    if str(row.get(key, "")) != str(val):
                        skip = True
                        break
                if skip:
                    continue

            results.append({
                "ticket_id": tid,
                "fused_score": round(score, 5),
                "text": row["text"],
                "store": row["store"],
                "region": row["region"],
                "dept": row["dept"],
                "event_date": row["event_date"],
                "logged_date": row["logged_date"],
                "category": row["category"],
                "access_level": row["access_level"],
                "source_type": row["source_type"],
            })

            if len(results) >= top_k:
                break

        return results


if __name__ == "__main__":
    retriever = HybridRetriever()

    print("=" * 60)
    print("Query: 'stockout delayed shipment weather' (expect Store 18 tickets)")
    print("=" * 60)
    for r in retriever.search("stockout delayed shipment weather disruption", top_k=5):
        print(f"  [{r['ticket_id']}] store={r['store']} score={r['fused_score']:.5f} ({r['category']})")
        print(f"    {r['text'][:90]}...")

    print("\n" + "=" * 60)
    print("Query: 'marketing paused staffing competitor' (expect Store 27 tickets)")
    print("=" * 60)
    for r in retriever.search("marketing paused staffing shortage competitor pricing", top_k=5):
        print(f"  [{r['ticket_id']}] store={r['store']} score={r['fused_score']:.5f} ({r['category']})")
        print(f"    {r['text'][:90]}...")

    print("\n" + "=" * 60)
    print("Query: 'Store 17 pricing issue' with store filter")
    print("=" * 60)
    for r in retriever.search("pricing seemed off contradicted inventory", top_k=5, filters={"store": 17}):
        print(f"  [{r['ticket_id']}] store={r['store']} score={r['fused_score']:.5f} ({r['category']})")
        print(f"    {r['text'][:90]}...")