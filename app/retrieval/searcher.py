from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    filename: str
    content: str
    score: float  # cosine similarity (0-1, makin tinggi makin relevan)

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
    document_id: str | None = None,  # tambah ini
) -> list[SearchResult]:

    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # tambah filter kondisional
    doc_filter = "AND c.document_id = :document_id ::uuid" if document_id else ""

    sql = text(f"""
        SELECT ...
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        {doc_filter}
        ORDER BY c.embedding <=> :embedding ::vector
        LIMIT :top_k
    """)

    params = {"embedding": embedding_str, "top_k": top_k}
    if document_id:
        params["document_id"] = document_id

    rows = db.execute(sql, params).fetchall()

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
