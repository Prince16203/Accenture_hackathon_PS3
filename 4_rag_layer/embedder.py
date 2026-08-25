import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
"""
embedder.py
Embeds field_reports.csv into a persistent ChromaDB collection.
Uses a small, fast sentence-transformer model (all-MiniLM-L6-v2) —
chosen over larger models like bge-base for speed given this is a
79-record corpus, not a production-scale one. Swappable later if
retrieval quality needs improving.

Run once to build the index; hybrid_retriever.py reads from it.
"""

import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIELD_REPORTS_PATH = PROJECT_ROOT / "1_data_foundation" / "sources" / "field_reports_adhoc" / "field_reports.csv"
CHROMA_PERSIST_PATH = PROJECT_ROOT / "4_rag_layer" / "evidence_store" / "chroma_db"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "field_reports"

_model_cache = None


def get_model() -> SentenceTransformer:
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


def load_field_reports() -> pd.DataFrame:
    df = pd.read_csv(FIELD_REPORTS_PATH, encoding="utf-8")
    df["dept"] = df["dept"].fillna("")
    return df


def build_index(force_rebuild: bool = False) -> chromadb.Collection:
    """
    Builds (or rebuilds) the ChromaDB collection from field_reports.csv.
    Each ticket's `text` field is embedded; all other columns are stored
    as metadata for filtering (region, access_level, category, dates).
    """
    CHROMA_PERSIST_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_PATH))

    if force_rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(COLLECTION_NAME)

    if collection.count() > 0 and not force_rebuild:
        print(f"Collection already has {collection.count()} records — skipping rebuild. "
              f"Call build_index(force_rebuild=True) to reindex.")
        return collection

    df = load_field_reports()
    model = get_model()

    texts = df["text"].tolist()
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    metadatas = df.drop(columns=["text"]).astype(str).to_dict(orient="records")
    ids = df["ticket_id"].tolist()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"Indexed {len(ids)} field reports into ChromaDB at {CHROMA_PERSIST_PATH}")
    return collection


def get_collection() -> chromadb.Collection:
    """Read-only accessor — used by hybrid_retriever.py without triggering a rebuild."""
    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_PATH))
    return client.get_or_create_collection(COLLECTION_NAME)


if __name__ == "__main__":
    collection = build_index(force_rebuild=True)
    print(f"\nTotal records indexed: {collection.count()}")

    # quick sanity check — embed a query and see nearest neighbors
    model = get_model()
    query = "stockout delayed shipment empty shelves"
    query_emb = model.encode([query]).tolist()
    results = collection.query(query_embeddings=query_emb, n_results=3)
    print(f"\nNearest neighbors for query: '{query}'")
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        print(f"  [{meta['ticket_id']}] store={meta['store']} dist={dist:.4f}")
        print(f"    {doc[:100]}...")