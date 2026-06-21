# test_pipeline.py
import uuid
from pathlib import Path
from app.core.database import SessionLocal, init_db
from app.models.document import Document
from app.models.chunk import Chunk
from app.ingestion.detector import detect_format
from app.ingestion.extractors import get_extractor
from app.ingestion.chunker import chunk_extracted
from app.ingestion.embedder import embed_texts, embed_query
from app.retrieval.searcher import search_chunks
from app.generation.generator import generate_answer
from app.models import Document, Chunk  # pastikan models ter-load

init_db()
db = SessionLocal()

# 1. Ingest satu file
file_path = Path("sample_docs/pdf/Add & manage connections – Notion Help Center.pdf")  # ganti path
file_bytes = file_path.read_bytes()
fmt = detect_format(file_path.name)

extracted = get_extractor(fmt).extract(file_bytes, file_path.name)
chunks = chunk_extracted(extracted, fmt)
embeddings = embed_texts([c.text for c in chunks])

# 2. Simpan ke DB
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
print(f"✅ Ingested: {len(chunks)} chunks")

# 3. Query
question = "What is this document about?"
query_emb = embed_query(question)
results = search_chunks(db, query_emb, top_k=3)

print(f"✅ Retrieved: {len(results)} chunks")
for r in results:
    print(f"   score={r.score:.3f} | page={r.page_number} | {r.content[:60]}...")

# 4. Generate
answer = generate_answer(question, results)
print(f"\n✅ Answer:\n{answer}")

db.close()