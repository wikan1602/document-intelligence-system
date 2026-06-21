# tests/test_pipeline.py
from pathlib import Path
import pytest
from app.core.database import SessionLocal, init_db
from app.models.document import Document
from app.models.chunk import Chunk
from app.ingestion.detector import detect_format
from app.ingestion.extractors import get_extractor
from app.ingestion.chunker import chunk_extracted
from app.ingestion.embedder import embed_texts, embed_query
from app.retrieval.searcher import search_chunks
from app.generation.generator import generate_answer

def test_full_end_to_end_rag_pipeline():
    """
    Integration test untuk menguji siklus RAG utuh:
    Ingestion berkas, penyimpanan vektor database, similarity search, dan response generation via Groq.
    """
    init_db()
    db = SessionLocal()
    
    file_path = Path("sample_docs/pdf/Add & manage connections – Notion Help Center.pdf")
    if not file_path.exists():
        db.close()
        pytest.skip("Berkas sampel tidak ditemukan, melewati integrasi E2E pipeline.")
        
    try:
        # 1. Pipeline Ingestion
        file_bytes = file_path.read_bytes()
        fmt = detect_format(file_path.name)
        extracted = get_extractor(fmt).extract(file_bytes, file_path.name)
        chunks = chunk_extracted(extracted, fmt)
        embeddings = embed_texts([c.text for c in chunks])

        # 2. Simpan entitas ke DB
        doc = Document(filename=file_path.name, format=str(fmt), file_size=len(file_bytes))
        db.add(doc)
        db.flush()

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            db.add(Chunk(
                document_id=doc.id,
                content=chunk.text,
                embedding=emb,
                chunk_index=i,
                page_number=chunk.page_number,
            ))
        db.commit()

        # 3. Pengujian Kueri Vektor Semantik (pgvector)
        question = "What is this document about?"
        query_emb = embed_query(question)
        results = search_chunks(db, query_emb, top_k=3)

        assert len(results) > 0, "Sistem harus berhasil mengembalikan chunk yang relevan"
        assert results[0].score >= 0.0, "Skor kecocokan similarity harus valid"

        # 4. Pengujian Generasi Jawaban LLM Groq
        answer = generate_answer(question, results)
        assert isinstance(answer, str), "Output dari model generator harus berupa string teks"
        assert len(answer.strip()) > 0, "Jawaban dari LLM tidak boleh kosong"
        assert "Error generating answer" not in answer, f"Terjadi kegagalan inferensi LLM: {answer}"
        
    finally:
        db.close()