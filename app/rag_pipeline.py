import faiss
import pickle
from sentence_transformers import SentenceTransformer

index = faiss.read_index("data/index/index.faiss")

with open("data/index/metadata.pkl", "rb") as f:
    metadata = pickle.load(f)

model = SentenceTransformer("all-MiniLM-L6-v2")


def retrieve(query, top_k=5):
    query_vec = model.encode([query])

    D, I = index.search(query_vec, top_k)

    results = []

    for idx, i in enumerate(I[0]):
        results.append({
            "text": metadata[i]["text"],
            "page": metadata[i]["page"],
            "reference": metadata[i].get("reference", "Unknown"),
            "score": float(D[0][idx]) if len(D[0]) > idx else 0.0
        })

    return results