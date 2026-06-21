from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chunk import Chunk
from app.models.document import Document


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    filename: str
    content: str
    score: float                    # cosine similarity (0-1, makin tinggi makin relevan)

    # Source tracing
    page_number: int | None
    slide_number: int | None
    slide_title: str | None
    sheet_name: str | None
    row_range: str | None
    heading: str | None


def search_chunks(
    db: Session,
    query_embedding: list[float],
    top_k: int = settings.top_k_results,
) -> list[SearchResult]:
    """
    Cari chunks paling relevan menggunakan cosine similarity via pgvector.

    Menggunakan operator <=> (cosine distance), lalu konversi ke similarity score.
    """
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    sql = text("""
        SELECT
            c.id,
            c.document_id,
            d.filename,
            c.content,
            1 - (c.embedding <=> :embedding ::vector) AS score,
            c.page_number,
            c.slide_number,
            c.slide_title,
            c.sheet_name,
            c.row_range,
            c.heading
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> :embedding ::vector
        LIMIT :top_k
    """)

    rows = db.execute(sql, {"embedding": embedding_str, "top_k": top_k}).fetchall()

    return [
        SearchResult(
            chunk_id=str(row.id),
            document_id=str(row.document_id),
            filename=row.filename,
            content=row.content,
            score=float(row.score),
            page_number=row.page_number,
            slide_number=row.slide_number,
            slide_title=row.slide_title,
            sheet_name=row.sheet_name,
            row_range=row.row_range,
            heading=row.heading,
        )
        for row in rows
    ]
