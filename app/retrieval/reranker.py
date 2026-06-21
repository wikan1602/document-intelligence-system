# app/retrieval/reranker.py
from sentence_transformers import CrossEncoder

_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query: str, chunks: list, top_k: int = 5) -> list:
    """
    Rerank chunks berdasarkan relevansi terhadap query.
    Input: chunks dari similarity_search (sudah top-20 misalnya)
    Output: top_k chunks yang paling relevan
    """
    if not chunks:
        return []

    pairs = [(query, chunk.content) for chunk in chunks]
    scores = _model.predict(pairs)

    scored = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]