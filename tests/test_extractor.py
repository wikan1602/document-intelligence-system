# test_ingestion.py
from pathlib import Path
from app.ingestion.detector import detect_format
from app.ingestion.extractors import get_extractor
from app.ingestion.chunker import chunk_extracted
from app.ingestion.embedder import embed_texts

file_path = Path("sample_docs/pdf/Add & manage connections – Notion Help Center.pdf")
file_bytes = file_path.read_bytes()

fmt = detect_format(file_path.name)
extracted = get_extractor(fmt).extract(file_bytes, file_path.name)
chunks = chunk_extracted(extracted, fmt)
embeddings = embed_texts([c.text for c in chunks])

print(f"Chunks: {len(chunks)}")
print(f"Embeddings: {len(embeddings)}, dimensi: {len(embeddings[0])}")