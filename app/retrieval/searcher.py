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

    # Source tracing metadata
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
    document_id: str | None = None,
) -> list[SearchResult]:

    # Konversi list float ke format string pgvector [x, y, z, ...]
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # Filter kondisional untuk metadata routing dokumen spesifik
    doc_filter = "AND c.document_id = :document_id ::uuid" if document_id else ""

    # 1. Ditambahkan f-string di depan triple quotes agar doc_filter bisa masuk
    # 2. Ditambahkan perhitungan score: (1 - Cosine Distance) = Cosine Similarity
    # 3. Ditambahkan semua kolom metadata agar mapping SearchResult tidak AttributeError
    # 4. Mengubah placeholder menjadi format SQLAlchemy (:embedding, :top_k)
    sql = f"""
        SELECT 
            c.id AS chunk_id, 
            c.document_id, 
            d.filename, 
            c.content, 
            (1 - (c.embedding <=> :embedding ::vector)) AS score,
            c.page_number,
            c.slide_number,
            c.slide_title,
            c.sheet_name,
            c.row_range,
            c.heading
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        {doc_filter}
        ORDER BY c.embedding <=> :embedding ::vector
        LIMIT :top_k
    """

    params = {"embedding": embedding_str, "top_k": top_k}
    if document_id:
        params["document_id"] = str(document_id)

    # Membungkus query string dengan fungsi text() agar mematuhi SQLAlchemy 2.0
    rows = db.execute(text(sql), params).fetchall()

    return [
        SearchResult(
            chunk_id=str(row.chunk_id),  # Diubah dari row.id ke row.chunk_id
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
