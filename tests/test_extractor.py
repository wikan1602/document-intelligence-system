# tests/test_extractor.py
from pathlib import Path
import pytest
from app.ingestion.detector import detect_format
from app.ingestion.extractors import get_extractor
from app.ingestion.chunker import chunk_extracted
from app.ingestion.embedder import embed_texts

def test_extractor_and_embedding_pipeline():
    """
    Memverifikasi pipeline parser berkas: ekstraksi konten, 
    pemotongan semantik, dan keakuratan dimensi vektor embedding.
    """
    file_path = Path("sample_docs/pdf/Add & manage connections – Notion Help Center.pdf")
    
    # Proteksi CI: Skip test jika file fisik belum di-upload ke repo GitHub
    if not file_path.exists():
        pytest.skip(f"Berkas sampel tidak ditemukan di {file_path}, melewati pengujian.")
        
    file_bytes = file_path.read_bytes()
    
    # 1. Jalankan komponen ingestion
    fmt = detect_format(file_path.name)
    extractor = get_extractor(fmt)
    extracted = extractor.extract(file_bytes, file_path.name)
    chunks = chunk_extracted(extracted, fmt)
    
    # 2. Jalankan Asersi Pengujian
    assert len(chunks) > 0, "Hasil chunking dokumen tidak boleh kosong"
    
    embeddings = embed_texts([c.text for c in chunks])
    assert len(embeddings) == len(chunks), "Jumlah embedding harus sama dengan jumlah chunk"
    assert len(embeddings[0]) == 1536, "Dimensi embedding OpenAI text-embedding-3-small harus 1536"