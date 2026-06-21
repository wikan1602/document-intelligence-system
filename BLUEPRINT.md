# 📘 Blueprint — Document Intelligence System
**PT Altimeda Cipta Visitama | Take Home Test — AI Engineer**

---

## 1. Tujuan Sistem

Membangun sistem RAG (Retrieval-Augmented Generation) yang mampu:
- Menerima dan memproses dokumen multi-format secara otomatis
- Mengindeks konten ke dalam vector database
- Menjawab pertanyaan dalam bahasa natural dengan **source tracing** (nama file, halaman, slide, atau sheet)

---

## 2. Tech Stack Final

| Komponen       | Pilihan                           | Alasan                                                   |
|----------------|-----------------------------------|----------------------------------------------------------|
| Language       | Python 3.10+                      | Requirement wajib                                        |
| API Framework  | FastAPI                           | Requirement wajib                                        |
| Vector DB      | PostgreSQL + pgvector             | Requirement wajib                                        |
| Embedding      | `text-embedding-3-small` (OpenAI) | Murah ($0.02/1M token), kualitas bagus untuk RAG         |
| LLM            | llama-3.3-70b-versatile                 | Murah, context window besar, cepat     |
| Monitoring     | Langfuse                          | Open source, ada cloud free tier                         |
| Container      | Docker + Docker Compose           | Isolasi service, mudah deploy                            |
| Deployment     | Railway                           | Support Docker Compose + managed PostgreSQL              |
| CI/CD          | GitHub Actions                    | Gratis untuk public repo                                 |

---

## 3. Arsitektur Sistem

```
┌─────────────────────────────────────────────────────┐
│                   CLIENT / USER                      │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP Request
┌─────────────────▼───────────────────────────────────┐
│                  FASTAPI LAYER                       │
│  /upload  │  /query  │  /documents  │  /health      │
└─────────────────┬───────────────────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
┌───────▼──────┐    ┌────────▼────────┐
│  INGESTION   │    │   RETRIEVAL &   │
│  PIPELINE    │    │   GENERATION    │
└───────┬──────┘    └────────┬────────┘
        │                    │
        │          ┌─────────▼─────────┐
        │          │   VECTOR SEARCH   │
        │          │   (pgvector)      │
        │          └─────────┬─────────┘
        │                    │
┌───────▼────────────────────▼─────────┐
│         PostgreSQL + pgvector         │
│   chunks | embeddings | metadata      │
└──────────────────────────────────────┘
        │                    │
┌───────▼──────┐    ┌────────▼────────┐
│  OpenAI      │    │  Groq           │
│  Embedding   │    │        (LLM)    │
└──────────────┘    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Langfuse     │
                    │   (Monitoring)  │
                    └─────────────────┘
```

---

## 4. Struktur Project

```
document-intelligence/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── upload.py           # POST /upload
│   │   │   ├── query.py            # POST /query
│   │   │   └── documents.py        # GET /documents, DELETE /documents/{id}
│   │   └── dependencies.py         # DB session, shared dependencies
│   ├── core/
│   │   ├── config.py               # env vars & settings (pydantic-settings)
│   │   └── database.py             # SQLAlchemy engine + pgvector setup
│   ├── ingestion/
│   │   ├── detector.py             # auto-detect format dari MIME/extension
│   │   ├── extractors/
│   │   │   ├── base.py             # abstract base class extractor
│   │   │   ├── pdf.py              # PyMuPDF (fitz)
│   │   │   ├── docx.py             # python-docx
│   │   │   ├── pptx.py             # python-pptx
│   │   │   ├── xlsx.py             # openpyxl
│   │   │   └── csv_txt.py          # pandas / plain read
│   │   ├── chunker.py              # chunking strategies per format
│   │   └── embedder.py             # batch embedding via OpenAI API
│   ├── retrieval/
│   │   ├── searcher.py             # pgvector cosine similarity search
│   │   └── reranker.py             # optional cross-encoder reranking
│   ├── generation/
│   │   └── generator.py            # prompt builder + Gemini LLM call
│   └── models/
│       ├── document.py             # SQLAlchemy ORM: documents table
│       └── chunk.py                # SQLAlchemy ORM: chunks table
├── tests/
│   ├── test_extractors.py
│   ├── test_retrieval.py
│   └── test_api.py
├── docker/
│   └── init.sql                    # CREATE EXTENSION pgvector
├── sample_docs/
│   ├── pdf/                        # 2 dokumen PDF (ISO, Texas Instruments)
│   ├── docx/                       # 2 dokumen DOCX
│   ├── pptx/                       # 2 dokumen PPTX
│   ├── xlsx/                       # 2 dokumen XLSX (bonus)
│   └── csv/                        # 2 dokumen CSV (bonus)
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions: lint + test
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── README.md
└── TECHNICAL.md
```

---

## 5. Alur Detail (Flow)

### 5.1 Ingestion Flow

```
Upload file (multipart/form-data)
    │
    ▼
detector.py
    → deteksi format via MIME type + ekstensi
    → pilih extractor yang sesuai
    │
    ▼
extractor (pdf / docx / pptx / xlsx / csv_txt)
    → return List[ExtractedPage]
       {text, page_number, slide_number, sheet_name, heading, raw_metadata}
    │
    ▼
chunker.py
    → terapkan chunking strategy sesuai format
    → return List[Chunk] dengan metadata lengkap
    │
    ▼
embedder.py
    → batch call ke OpenAI text-embedding-3-small
    → return List[vector(1536)]
    │
    ▼
PostgreSQL
    → INSERT ke tabel documents (metadata level file)
    → INSERT ke tabel chunks (teks + embedding + source metadata)
    │
    ▼
Response: { document_id, chunk_count, format, filename }
```

### 5.2 Query Flow

```
POST /query { "question": "..." }
    │
    ▼
Embed query
    → OpenAI text-embedding-3-small
    │
    ▼
pgvector similarity search
    → cosine distance, ambil top-K chunks (default K=5)
    │
    ▼
(Optional) Reranking
    → sort ulang berdasarkan relevansi lebih presisi
    │
    ▼
Prompt builder
    → susun context dari chunks + sertakan source info
    → format: [Source: filename, page X] \n {chunk_text}
    │
    ▼
llama-3.3-70b-versatile
    → generate jawaban berdasarkan context
    │
    ▼
Langfuse
    → log: query, chunks retrieved, answer, latency, token usage
    │
    ▼
Response:
{
  "answer": "...",
  "sources": [
    { "filename": "ISO_9001.pdf", "page": 12 },
    { "filename": "TI_Datasheet.pdf", "page": 4 }
  ]
}
```

---

## 6. Chunking Strategy per Format

| Format   | Strategy                               | Metadata yang Disimpan                    |
|----------|----------------------------------------|-------------------------------------------|
| PDF      | Sliding window 512 token, overlap 50   | `filename`, `page_number`                 |
| DOCX     | Split per heading/section              | `filename`, `heading`, `paragraph_index`  |
| PPTX     | Per slide (1 chunk = 1 slide)          | `filename`, `slide_number`, `slide_title` |
| XLSX     | Per sheet, dikelompokkan per row-group | `filename`, `sheet_name`, `row_range`     |
| CSV/TXT  | Sliding window per N baris/karakter    | `filename`, `line_range`                  |

---

## 7. Database Schema

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabel dokumen (metadata level file)
CREATE TABLE documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename     TEXT NOT NULL,
    format       TEXT NOT NULL,         -- 'pdf' | 'docx' | 'pptx' | 'xlsx' | 'csv'
    file_size    BIGINT,
    uploaded_at  TIMESTAMPTZ DEFAULT now(),
    metadata     JSONB
);

-- Tabel chunks (unit retrieval)
CREATE TABLE chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  UUID REFERENCES documents(id) ON DELETE CASCADE,
    content      TEXT NOT NULL,
    embedding    vector(1536),          -- OpenAI text-embedding-3-small
    chunk_index  INTEGER NOT NULL,

    -- Source tracing fields
    page_number  INTEGER,               -- untuk PDF
    slide_number INTEGER,               -- untuk PPTX
    slide_title  TEXT,                  -- untuk PPTX
    sheet_name   TEXT,                  -- untuk XLSX
    row_range    TEXT,                  -- untuk XLSX/CSV (contoh: "10-25")
    heading      TEXT,                  -- untuk DOCX

    metadata     JSONB,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Index untuk similarity search (IVFFlat)
CREATE INDEX ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

## 8. API Endpoints

| Method | Endpoint               | Deskripsi                              |
|--------|------------------------|----------------------------------------|
| POST   | `/upload`              | Upload & proses dokumen baru           |
| POST   | `/query`               | Tanya jawab dengan source tracing      |
| GET    | `/documents`           | List semua dokumen yang sudah diindeks |
| GET    | `/documents/{id}`      | Detail dokumen + chunk count           |
| DELETE | `/documents/{id}`      | Hapus dokumen + semua chunk-nya        |
| GET    | `/health`              | Health check (API + DB status)         |

### Contoh Request & Response

**POST /query**
```json
// Request
{
  "question": "Apa persyaratan dokumentasi untuk ISO 9001?",
  "top_k": 5
}

// Response
{
  "answer": "Berdasarkan dokumen ISO 9001:2015, persyaratan dokumentasi mencakup...",
  "sources": [
    {
      "filename": "ISO_9001_2015.pdf",
      "page_number": 12,
      "excerpt": "Organizations shall maintain documented information..."
    },
    {
      "filename": "ISO_9001_2015.pdf",
      "page_number": 15,
      "excerpt": "The extent of documented information can differ..."
    }
  ],
  "latency_ms": 1240
}
```

---

## 9. Docker Compose

```yaml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

---

## 10. Environment Variables

```env
# .env.example

# Database
POSTGRES_USER=docint
POSTGRES_PASSWORD=secret
POSTGRES_DB=document_intelligence
DATABASE_URL=postgresql://docint:secret@db:5432/document_intelligence

# OpenAI (Embedding)
OPENAI_API_KEY=sk-...

# Groq (LLM)
GROQ_API_KEY=gsk_...

# Langfuse (Monitoring)
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com

# App Config
TOP_K_RESULTS=5
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

---

## 11. GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pip install pytest ruff
      - run: ruff check app/
      - run: pytest tests/ -v
```

---

## 12. Sample Dokumen (Rencana)

| Format | Dokumen                                 | Sumber           |
|--------|-----------------------------------------|------------------|
| PDF    | ISO 9001:2015 Overview                  | iso.org / publik |
| PDF    | Texas Instruments — Application Report  | ti.com           |
| DOCX   | ISO 27001 Summary (converted)           | publik           |
| DOCX   | TI Reference Design Doc (converted)     | ti.com           |
| PPTX   | ISO Standards Introduction Slides       | dibuat manual    |
| PPTX   | TI Product Overview Presentation        | ti.com / publik  |
| XLSX   | ISO Checklist Audit Template (bonus)    | publik           |
| CSV    | TI Product Comparison Table (bonus)     | ti.com / ekstrak |

---

## 13. Rencana Pengerjaan (Phases)

### Phase 1 — Core (Target: Working End-to-End)
- [ ] Setup project structure + virtual environment
- [ ] Docker Compose: FastAPI + PostgreSQL + pgvector
- [ ] Database schema + SQLAlchemy models
- [ ] Extractor: PDF, DOCX, PPTX
- [ ] Chunker (per-format strategy)
- [ ] Embedder (OpenAI batch)
- [ ] FastAPI: `POST /upload` + `POST /query`
- [ ] RAG pipeline end-to-end berjalan

### Phase 2 — Polish & Bonus
- [ ] Extractor: XLSX + CSV/TXT
- [ ] Langfuse monitoring integration
- [ ] GitHub Actions CI (lint + test)
- [ ] Error handling, logging, validasi input
- [ ] `GET /documents` + `DELETE /documents/{id}`

### Phase 3 — Docs & Deploy
- [ ] Deploy ke Railway (API + DB)
- [ ] README.md (setup, cara run, contoh Q&A)
- [ ] TECHNICAL.md (arsitektur, trade-off, chunking rationale)
- [ ] Sample Q&A documentation dengan output nyata
- [ ] Video demo lokal (backup jika deploy gagal)

---

## 14. Trade-off & Keputusan Desain

| Keputusan        | Opsi Dipilih              | Alasan                                    | Trade-off                                          |
|------------------|---------------------------|-------------------------------------------|----------------------------------------------------|
| LLM              | Gemini 2.0 Flash          | Murah + cepat + context besar             | Bukan OpenAI ecosystem                             |
| Embedding        | text-embedding-3-small    | Cost efisien, quality cukup               | Bukan model terbesar                               |
| Vector DB        | pgvector                  | Sesuai requirement, satu DB untuk semua   | Kurang scalable vs dedicated (Qdrant/Weaviate)     |
| Chunking PDF     | Sliding window            | Cocok untuk dokumen naratif               | Bisa memotong context antar paragraf               |
| Chunking PPTX    | Per slide                 | 1 slide = 1 topik logis                   | Slide panjang bisa kurang terkover                 |
| Reranker         | Optional                  | Tambah akurasi retrieval                  | Tambah latency                                     |
| Deployment       | Railway                   | Paling mudah Docker + managed DB          | Cost lebih tinggi vs self-host jangka panjang      |
