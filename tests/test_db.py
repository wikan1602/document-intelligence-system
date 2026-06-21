# tests/test_db.py
from app.core.database import init_db, SessionLocal
from app.models.document import Document
from app.models.chunk import Chunk

def test_database_initialization_and_tables():
    """
    Memastikan skema database PostgreSQL + pgvector berhasil diinisialisasi
    and tabel-tabel sistem bisa di-query tanpa error.
    """
    # 1. Jalankan inisialisasi tabel
    init_db()
    
    # 2. Buka session untuk verifikasi query ORM
    db = SessionLocal()
    try:
        # Lakukan query dasar untuk mengecek struktur tabel
        doc_count = db.query(Document).count()
        chunk_count = db.query(Chunk).count()
        
        # Assert bahwa hasilnya mengembalikan angka (berarti tabel ada)
        assert isinstance(doc_count, int)
        assert isinstance(chunk_count, int)
    finally:
        db.close()