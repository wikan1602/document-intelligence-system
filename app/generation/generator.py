# app/generation/generator.py
from groq import Groq
from langfuse import Langfuse, observe

from app.core.config import settings
from app.retrieval.searcher import SearchResult

# Inisialisasi Client Groq
_client = Groq(api_key=settings.groq_api_key)

# Init Langfuse (tetap aktif jika env vars dikonfigurasi)
_langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
)


def _format_source_label(result: SearchResult) -> str:
    """Buat label sumber yang informatif untuk context prompt."""
    parts = [f"File: {result.filename}"]
    if result.page_number:
        parts.append(f"Page {result.page_number}")
    if result.slide_number:
        title = f" ({result.slide_title})" if result.slide_title else ""
        parts.append(f"Slide {result.slide_number}{title}")
    if result.sheet_name:
        parts.append(f"Sheet: {result.sheet_name}")
        if result.row_range:
            parts.append(f"Rows {result.row_range}")
    if result.heading:
        parts.append(f"Section: {result.heading}")
    return " | ".join(parts)


def _build_prompt(question: str, results: list[SearchResult]) -> str:
    context_blocks = []
    for i, r in enumerate(results, start=1):
        label = _format_source_label(r)
        context_blocks.append(f"[Context {i} — {label}]\n{r.content}")

    context_str = "\n\n".join(context_blocks)

    return f"""You are a document intelligence assistant. Answer the user's question based ONLY on the provided context below.

Rules:
- Answer clearly and concisely based on the context.
- If the answer is not found in the context, say "I could not find relevant information in the provided documents."
- Do NOT make up information outside the context.
- Always refer to the source when relevant (e.g., "According to [filename], page X...").

Context:
{context_str}

Question: {question}

Answer:"""


@observe(name="rag_query")
def generate_answer(
    question: str,
    results: list[SearchResult],
) -> str:
    """
    Generate jawaban dari Groq berdasarkan retrieved chunks.
    Mendukung auto-logging latency dan token ke Langfuse via decorator.
    """
    prompt = _build_prompt(question, results)

    try:
        # Menggunakan Chat Completion standar OpenAI-compatible milik Groq
        response = _client.chat.completions.create(
            model=settings.llm_model,  # Menggunakan model Groq (misal: llama-3.3-70b-specdec)
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,            # Rendah dan deterministik untuk akurasi data RAG
            max_tokens=1024,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        answer = f"Error generating answer via Groq: {str(e)}"

    return answer