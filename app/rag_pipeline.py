import pickle
from functools import lru_cache

import faiss


@lru_cache(maxsize=1)
def _load_rag_assets():
    # Lazily import sentence-transformers so non-RAG views do not pay the startup cost.
    from sentence_transformers import SentenceTransformer

    index = faiss.read_index("data/index/index.faiss")
    with open("data/index/metadata.pkl", "rb") as f:
        metadata = pickle.load(f)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return index, metadata, model


def retrieve(query, top_k=5):
    index, metadata, model = _load_rag_assets()
    query_vec = model.encode([query])

    D, I = index.search(query_vec, top_k)

    results = []

    for idx, i in enumerate(I[0]):
        results.append({
            "text": metadata[i]["text"],
            "page": metadata[i]["page"],
            "paragraph": metadata[i].get("paragraph"),
            "reference": metadata[i].get("reference", "Unknown"),
            "locator": metadata[i].get("locator", ""),
            "chunk": metadata[i].get("chunk"),
            "score": float(D[0][idx]) if len(D[0]) > idx else 0.0
        })

    return results
