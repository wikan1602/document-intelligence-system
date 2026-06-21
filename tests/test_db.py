# test_db.py
from app.core.database import init_db
from app.models import Chunk, Document  # ← ini yang penting, harus diimport dulu

init_db()
print("OK — tabel berhasil dibuat")