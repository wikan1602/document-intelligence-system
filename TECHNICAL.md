# TECHNICAL.md — Document Intelligence System

## 1. Arsitektur Sistem

```
┌─────────────────────────────────────────────────────┐
│                   CLIENT / USER                      │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP (multipart / JSON)
┌─────────────────▼───────────────────────────────────┐
│                  FASTAPI LAYER                       │
│  /upload  │  /query  │  /documents  │  /chat        │
└─────────────────┬───────────────────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
┌───────▼──────┐    ┌────────▼────────┐
│  INGESTION   │    │    RETRIEVAL &  │
│  PIPELINE    │    │    GENERATION   │
└───────┬──────┘    └────────┬────────┘
        │                    │
        │          ┌─────────▼─────────┐
        │          │  VECTOR SEARCH +  │
        │          │  RERANKER         │
        │          └─────────┬─────────┘
        │                    │
┌───────▼────────────────────▼─────────┐
│         PostgreSQL + pgvector         │
│   documents | chunks | embeddings    │
└──────────────────────────────────────┘
        │                    │
┌───────▼──────┐    ┌────────▼────────────┐
│  OpenAI      │    │  Deepseek           │
│  Embedding   │    │  deepseek-v4-flash  │
└──────────────┘    └────────┬────────────┘
                             │
                    ┌────────▼────────┐
                    │    Langfuse     │
                    │   (Monitoring)  │
                    └─────────────────┘
```

---

## 2. Ingestion Pipeline

### 2.1 Format Detection (`detector.py`)

Deteksi format menggunakan dua layer:
1. **Ekstensi file** — cara tercepat dan paling reliable
2. **Magic bytes fallback** — `%PDF` untuk PDF, `PK\x03\x04` untuk Office formats (ZIP-based)

### 2.2 Extractors

| Format | Library | Strategi |
|---|---|---|
| PDF | PyMuPDF (fitz) | `page.get_text()` per halaman |
| DOCX | python-docx | Iterasi paragraf, deteksi heading via `para.style.name` |
| PPTX | python-pptx | Iterasi slides + shapes, title via `placeholder_format.idx == 0` |
| XLSX | openpyxl | `read_only=True, data_only=True`, grouping per 50 baris |
| CSV/TXT | Built-in | Decode UTF-8, sliding window per 100 baris |

### 2.3 Chunking Strategy

| Format | Strategi | Metadata Disimpan |
|---|---|---|
| PDF | Sliding window, 512 token, overlap 50 | `filename`, `page_number` |
| DOCX | Per section/heading + sliding window jika terlalu panjang | `filename`, `heading` |
| PPTX | Per slide = 1 chunk | `filename`, `slide_number`, `slide_title` |
| XLSX | Per row-group (50 baris) | `filename`, `sheet_name`, `row_range` |
| CSV | Per 100 baris | `filename`, `row_range` |

**Token counting** menggunakan `tiktoken` dengan encoder `cl100k_base` — sama dengan model embedding OpenAI, sehingga chunk size presisi.

---

## 3. Embedding

**Model**: `text-embedding-3-small` (OpenAI)
- Dimensi: 1536
- Cost: ~$0.02 / 1M token
- Encoder: `cl100k_base`

**Alternatif yang dipertimbangkan**:
- `text-embedding-3-large`: 2x lebih mahal, improvement marginal untuk use case ini
- Local model (sentence-transformers): Gratis tapi perlu GPU untuk performa optimal

---

## 4. Retrieval

### 4.1 Vector Search (pgvector)

Menggunakan **cosine distance** (`<=>` operator):

```sql
SELECT *, 1 - (embedding <=> :query_vector) AS score
FROM chunks
ORDER BY embedding <=> :query_vector
LIMIT :top_k
```

Cosine dipilih karena OpenAI embeddings sudah normalized — cosine distance equivalent dengan dot product, lebih stabil dari L2 di high-dimensional space.

### 4.2 Reranker

**Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`

Flow dua tahap:
1. Vector search ambil **top-K×4** kandidat (misal 20 chunk)
2. Cross-encoder re-score setiap pasangan (query, chunk)
3. Sort ulang, ambil **top-K** terbaik

**Kenapa cross-encoder lebih akurat dari bi-encoder?**
Bi-encoder (vector search) mengembedding query dan chunk secara terpisah — interaksi antar token tidak tertangkap. Cross-encoder membaca keduanya sekaligus sehingga bisa menangkap relevansi yang lebih nuanced.

**Trade-off**: Latency bertambah ~200-500ms tergantung jumlah kandidat.

---

## 5. Generation

**Model**: Deepseek `deepseek-v4-flash`
- Cost: jauh lebih murah dari GPT-4o
- Latency: ~300-800ms (Groq menggunakan custom inference hardware)
- Context window: 128K token

**Prompt strategy**:
```
[Context 1 — File: X.pdf | Page 12]
{chunk_content}

[Context 2 — File: Y.docx | Section: Klausul 7]
{chunk_content}

Question: {user_question}
Answer:
```

Temperature: **0.2** — rendah untuk mengutamakan faktualitas.

---

## 6. Monitoring (Langfuse)

Setiap call ke `generate_answer()` di-trace via `@observe` decorator:
- Input: question + jumlah chunks
- Output: jawaban
- Latency & token usage otomatis ter-capture

Langfuse bersifat **opsional** — jika env var tidak di-set, sistem tetap berjalan normal.

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
    page_number  INTEGER,
    slide_number INTEGER,
    slide_title  TEXT,
    sheet_name   TEXT,
    row_range    TEXT,
    heading      TEXT,
    metadata     JSONB,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

## 8. Trade-off & Keputusan Desain

| Keputusan | Pilihan | Alasan | Trade-off |
|---|---|---|---|
| LLM | Groq llama-3.3-70b | Murah + sangat cepat | Bukan model proprietary terbaik |
| Embedding | text-embedding-3-small | Cost efisien, kualitas cukup | Bukan model terbesar |
| Vector DB | pgvector | Sesuai requirement, satu DB | Kurang scalable vs Qdrant/Weaviate |
| Reranker | cross-encoder MiniLM | Gratis, akurasi bagus | Tambah latency ~300ms |
| Chunking PDF | Sliding window + tiktoken | Token-precise | Sedikit lebih lambat dari word-split |
| Chunking PPTX | Per slide | 1 slide = 1 topik logis | Slide panjang bisa kurang terkover |
| Monitoring | Langfuse | Open source, free tier | Perlu setup akun terpisah |
| Deployment | Railway | Docker Compose + managed DB | Cost lebih tinggi vs self-host |

---

## 9. Rencana Deployment (Railway)

```bash
# 1. Push ke GitHub
git push origin main

# 2. Railway → New Project → Deploy from GitHub Repo

# 3. Add PostgreSQL service di Railway dashboard
#    (DATABASE_URL otomatis di-inject)

# 4. Set environment variables:
#    OPENAI_API_KEY, GROQ_API_KEY, LANGFUSE_* (opsional)

# 5. Railway detect Dockerfile otomatis → build & deploy
```

Railway dipilih karena mendukung Docker Compose dan managed PostgreSQL dengan pgvector extension tersedia di image `pgvector/pgvector:pg16`.

---

## 10. Limitasi & Improvement

### Limitasi Saat Ini
- PDF scan (image-based) tidak didukung — perlu OCR
- Tidak ada authentication di API
- Tidak ada streaming response untuk LLM

### Improvement yang Bisa Dilakukan
- **OCR**: Tambahkan Tesseract / Azure Form Recognizer untuk scanned PDF
- **Hybrid search**: Gabungkan BM25 + vector search (reciprocal rank fusion)
- **Streaming**: Server-sent events untuk jawaban LLM real-time
- **Auth**: API key per user
- **Async ingestion**: Background job untuk file besar
