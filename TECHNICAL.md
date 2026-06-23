# TECHNICAL.md — Document Intelligence System

## 1. Arsitektur Sistem

```
┌─────────────────────────────────────────────────────┐
│                   CLIENT / USER                      │
│              (UI /chat atau API call)                │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP (multipart / JSON)
┌─────────────────▼───────────────────────────────────┐
│                  FASTAPI LAYER                       │
│   /upload  │  /query  │  /documents  │  /chat       │
└──────┬──────────────────────────┬────────────────────┘
       │                          │
┌──────▼──────┐          ┌────────▼────────────┐
│  INGESTION  │          │  RETRIEVAL PIPELINE │
│  PIPELINE   │          │                     │
│             │          │  1. embed_query()   │
│ 1. detect   │          │  2. search_chunks() │
│ 2. extract  │          │  3. rerank()        │
│ 3. chunk    │          └────────┬────────────┘
│ 4. embed    │                   │
│ 5. store    │          ┌────────▼────────────┐
└──────┬──────┘          │    GENERATION       │
       │                 │  generate_answer()  │
       │                 │  Deepseek V4 Flash  │
       │                 └────────┬────────────┘
       │                          │
┌──────▼──────────────────────────▼────────────┐
│            PostgreSQL + pgvector              │
│       documents | chunks | embeddings        │
└──────┬──────────────────────────┬────────────┘
       │                          │
┌──────▼──────┐          ┌────────▼────────┐
│   OpenAI    │          │    Langfuse     │
│  Embedding  │          │   Monitoring    │
└─────────────┘          └─────────────────┘
```

---

## 2. Ingestion Pipeline

### 2.1 Format Detection (`detector.py`)

Deteksi format menggunakan dua layer:

1. **Ekstensi file** — cara tercepat dan paling reliable untuk file yang di-upload user
2. **Magic bytes fallback** — `%PDF` untuk PDF, `PK\x03\x04` untuk Office formats (ZIP-based). Untuk membedakan DOCX/PPTX/XLSX, sistem membaca 2000 byte pertama dan mencari marker internal (`word/`, `ppt/`, `xl/`)

### 2.2 Extractors

| Format | Library | Strategi |
|---|---|---|
| PDF | PyMuPDF (fitz) | `page.get_text()` per halaman + filter halaman noise |
| DOCX | python-docx | Iterasi paragraf, deteksi heading via `para.style.name` |
| PPTX | python-pptx | Iterasi slides + shapes, title via `placeholder_format.idx == 0` |
| XLSX | openpyxl | `read_only=True, data_only=True`, grouping per 50 baris |
| CSV/TXT | Built-in | Decode UTF-8 dengan error handling, sliding window per 100 baris |

### 2.3 PDF Noise Filter

Halaman-halaman berikut di-skip sebelum masuk pipeline untuk menjaga kualitas retrieval:

1. **Halaman terlalu pendek** — `word count < 50`, eliminasi cover, halaman kosong, dan halaman satu baris
2. **Halaman daftar isi** — deteksi ratio baris yang mengandung pola `..` > 50%, menghindari false positive retrieval dari daftar isi yang banyak mengandung kata kunci tapi tanpa konten substantif

Tanpa filter ini, daftar isi PDF cenderung mendapat cosine similarity tinggi karena mengandung banyak kata kunci dari seluruh dokumen, merusak kualitas retrieval.

### 2.4 Chunking Strategy

| Format | Strategi | Alasan |
|---|---|---|
| PDF | Sliding window, 512 token, overlap 50 | Dokumen naratif — perlu konteks antar paragraf |
| DOCX | Per section/heading + sliding window jika terlalu panjang | Heading = unit logis dokumen |
| PPTX | Per slide = 1 chunk | 1 slide = 1 topik, menjaga koherensi |
| XLSX | Per row-group (50 baris) | Tabel terlalu panjang jika di-embed sekaligus |
| CSV | Per 100 baris | Flat file, unit natural adalah kumpulan baris |

**Token counting** menggunakan `tiktoken` dengan encoder `cl100k_base` — sama dengan model embedding OpenAI, sehingga chunk size presisi di level token, bukan word atau karakter.

---

## 3. Embedding

**Model**: `text-embedding-3-small` (OpenAI)
- Dimensi: 1536
- Cost: ~$0.02 / 1M token
- Encoder: `cl100k_base`
- Batching: 100 teks per API call untuk efisiensi

**Alternatif yang dipertimbangkan**:
- `text-embedding-3-large`: 2x lebih mahal, improvement marginal untuk use case ini
- Local model (sentence-transformers/multilingual): Gratis tapi perlu GPU untuk performa optimal, tidak cocok untuk Railway deployment

---

## 4. Retrieval

### 4.1 Vector Search (pgvector)

Menggunakan **cosine distance** (`<=>` operator):

```sql
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
  AND (c.document_id = :document_id ::uuid OR :document_id IS NULL)
ORDER BY c.embedding <=> :embedding ::vector
LIMIT :top_k
```

Cosine dipilih karena OpenAI embeddings sudah normalized — cosine distance equivalent dengan dot product, lebih stabil dari L2 di high-dimensional space.

**Filter dokumen**: Query mendukung `document_id` opsional untuk membatasi pencarian ke satu dokumen tertentu, menghindari cross-document contamination saat user ingin menanya dokumen spesifik.

### 4.2 Reranker (Two-Stage Retrieval)

**Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (sentence-transformers)

```
Query
  │
  ▼
Vector Search → ambil top-K×2 kandidat (misal 10 chunk)
  │
  ▼
Cross-Encoder Reranker → re-score setiap pasangan (query, chunk)
  │
  ▼
Sort ulang → ambil top-K terbaik → LLM
```

**Kenapa cross-encoder lebih akurat dari bi-encoder?**

Bi-encoder (vector search) mengembedding query dan chunk secara terpisah — interaksi antar token tidak tertangkap. Cross-encoder membaca pasangan (query, chunk) sekaligus, sehingga bisa menangkap relevansi yang lebih nuanced, terutama untuk pertanyaan yang membutuhkan pemahaman konteks.

**Trade-off**: Latency bertambah ~5-10 detik di CPU (Railway free tier). Dikurangi dengan membatasi kandidat ke `top_k × 2` bukan `top_k × 4`.

---

## 5. Generation

**Model**: Deepseek V4 Flash (via Groq API)
- Latency: ~300-800ms
- Context window: besar, tidak overflow untuk use case ini
- Temperature: **0.2** — rendah untuk mengutamakan faktualitas

**Prompt strategy**:

```
[Context 1 — File: X.pdf | Page 12]
{chunk_content}

[Context 2 — File: Y.docx | Section: Klausul 7]
{chunk_content}

...

Question: {user_question}
Answer:
```

Setiap context block diberi label sumber yang informatif sehingga LLM bisa menyebutkan sumber dalam jawaban secara natural.

---

## 6. Monitoring (Langfuse)

Setiap pipeline di-trace via decorator `@observe`:

| Span | Yang Diukur |
|---|---|
| `rag_query` | End-to-end latency, input question, output answer |
| `rerank_chunks` | Input chunks, output chunks setelah rerank, rerank scores |

Langfuse bersifat **opsional** — jika env var tidak di-set, sistem tetap berjalan normal tanpa monitoring.

---

## 7. Database Schema

```sql
CREATE TABLE documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename     TEXT NOT NULL,
    format       TEXT NOT NULL,
    file_size    BIGINT,
    uploaded_at  TIMESTAMPTZ DEFAULT now(),
    metadata     JSONB
);

CREATE TABLE chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  UUID REFERENCES documents(id) ON DELETE CASCADE,
    content      TEXT NOT NULL,
    embedding    vector(1536),
    chunk_index  INTEGER NOT NULL,
    -- Source tracing fields
    page_number  INTEGER,
    slide_number INTEGER,
    slide_title  TEXT,
    sheet_name   TEXT,
    row_range    TEXT,
    heading      TEXT,
    metadata     JSONB,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Index untuk approximate nearest neighbor search
CREATE INDEX ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**IVFFlat** dipilih karena cocok untuk dataset kecil-menengah (< 1 juta rows), build time cepat, dan `lists = 100` adalah rekomendasi pgvector untuk ukuran ini.

**CASCADE DELETE**: Hapus dokumen otomatis menghapus semua chunk terkait.

---

## 8. Trade-off & Keputusan Desain

| Keputusan | Pilihan | Alasan | Trade-off |
|---|---|---|---|
| LLM | Deepseek V4 Flash | Cost efisien, performa baik | Bukan model terbesar |
| Embedding | text-embedding-3-small | Cost efisien, 1536 dim cukup | Bukan model terbesar |
| Vector DB | pgvector | Sesuai requirement, satu infra | Kurang scalable vs Qdrant/Weaviate |
| Reranker | cross-encoder MiniLM | Gratis, akurasi baik | Tambah latency ~5-10 detik di CPU |
| Chunking PDF | Sliding window + tiktoken | Token-precise, context terjaga | Sedikit lebih lambat dari word-split |
| Chunking PPTX | Per slide | 1 slide = 1 topik logis | Slide sangat panjang bisa kurang terkover |
| PDF Noise Filter | Heuristik word count + TOC detection | Meningkatkan retrieval precision tanpa overhead | Tidak 100% akurat untuk semua jenis PDF |
| Document Filter | `document_id` opsional di `/query` | Cegah cross-document contamination | User perlu tahu document ID yang benar |
| Monitoring | Langfuse | Open source, free tier tersedia | Perlu setup akun terpisah |

---

## 9. Deployment (Railway)

### Arsitektur di Railway

```
Railway Project
├── Service: API (Docker)
│   └── Dockerfile → uvicorn main:app
└── Service: PostgreSQL
    └── pgvector/pgvector:pg16
        └── init.sql → CREATE EXTENSION vector
```

### Steps

```bash
# 1. Push ke GitHub
git push origin main

# 2. Railway → New Project → Deploy from GitHub Repo

# 3. Add PostgreSQL service
#    Railway → Add Service → Database → PostgreSQL
#    Pilih image: pgvector/pgvector:pg16
#    DATABASE_URL otomatis di-inject

# 4. Set environment variables di Railway dashboard:
#    OPENAI_API_KEY, GROQ_API_KEY
#    LANGFUSE_* (opsional)

# 5. Railway detect Dockerfile otomatis → build & deploy
```

**railway.toml**:

```toml
[build]
builder = "DOCKERFILE"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
```

---

## 10. Limitasi & Improvement

### Limitasi Saat Ini

- PDF scan (image-based) tidak didukung — perlu OCR
- Reranker lambat di CPU (~5-10 detik), ideal butuh GPU
- Tidak ada authentication/rate limiting di API
- Tidak ada streaming response untuk LLM

### Improvement yang Bisa Dilakukan

- **OCR**: Tambahkan Tesseract atau Azure Form Recognizer untuk scanned PDF
- **Hybrid search**: Gabungkan BM25 + vector search (Reciprocal Rank Fusion) untuk meningkatkan recall
- **Streaming**: Server-sent events untuk jawaban LLM real-time
- **Auth**: JWT atau API key per user/tenant
- **Async ingestion**: Background job (ARQ/Celery) untuk file besar agar upload tidak timeout
- **GPU reranker**: Deploy reranker di instance dengan GPU untuk latency < 1 detik