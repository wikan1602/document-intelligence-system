import time

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

_client = OpenAI(api_key=settings.openai_api_key)

BATCH_SIZE = 100  # OpenAI max per request


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed satu batch teks, dengan retry otomatis kalau rate limit."""
    response = _client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    # Pastikan urutan output sama dengan input
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed list of texts secara batch.
    Otomatis dibagi per BATCH_SIZE untuk menghindari limit OpenAI.

    Returns:
        List of embeddings, urutan sama dengan input texts.
    """
    if not texts:
        return []

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        embeddings = _embed_batch(batch)
        all_embeddings.extend(embeddings)

        # Hindari rate limit kalau ada banyak batch
        if i + BATCH_SIZE < len(texts):
            time.sleep(0.5)

    return all_embeddings


def embed_query(query: str) -> list[float]:
    """Embed single query string untuk similarity search."""
    result = _embed_batch([query])
    return result[0]
