import time
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.api.dependencies import get_db
from app.ingestion.embedder import embed_query

# 📄 PENYELARASAN 1: Import fungsi top-level asli dari core engine Anda
from app.retrieval.searcher import search_chunks
from app.generation.generator import generate_answer

router = APIRouter(prefix="/query", tags=["RAG Generation"])


class QueryRequest(BaseModel):
    question: str = Field(..., example="Apa prosedur audit untuk lini produksi X?")
    top_k: int = Field(default=5, ge=1, le=20)


class SourceMetadata(BaseModel):
    filename: str
    page_number: int | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    row_range: str | None = None
    heading: str | None = None
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceMetadata]
    latency_ms: float


@router.post("", response_model=QueryResponse)
def query_rag(request: QueryRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    start_time = time.time()

    try:
        # 1. Buat vektor query dari teks input
        query_vector = embed_query(request.question)

        # 📄 PENYELARASAN 2: Panggil fungsi search_chunks secara langsung
        retrieved_results = search_chunks(
            db=db, query_embedding=query_vector, top_k=request.top_k * 2
        )

        # Rerank ke top_k yang diminta
        from app.retrieval.reranker import rerank

        retrieved_results = rerank(
            query=request.question, chunks=retrieved_results, top_k=request.top_k
        )

        if not retrieved_results:
            return {
                "answer": "I could not find relevant information in the provided documents.",
                "sources": [],
                "latency_ms": round((time.time() - start_time) * 1000, 2),
            }

        # 📄 PENYELARASAN 3: Jalankan generator Gemini bawaan Anda
        generated_answer = generate_answer(
            question=request.question, results=retrieved_results
        )

        # 📄 PENYELARASAN 4: Mapping property flat langsung dari SearchResult dataclass
        sources = []
        for chunk in retrieved_results:
            sources.append(
                {
                    "filename": chunk.filename,  # <-- Langsung mengambil chunk.filename (bukan chunk.document.filename)
                    "page_number": chunk.page_number,
                    "slide_number": chunk.slide_number,
                    "sheet_name": chunk.sheet_name,
                    "row_range": chunk.row_range,
                    "heading": chunk.heading,
                    "excerpt": chunk.content[:200] + "..."
                    if len(chunk.content) > 200
                    else chunk.content,
                }
            )

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "answer": generated_answer,
            "sources": sources,
            "latency_ms": latency_ms,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memproses query RAG: {str(e)}",
        )
