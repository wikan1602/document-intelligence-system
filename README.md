# Document Intelligence System

Sistem RAG (Retrieval-Augmented Generation) untuk menjawab pertanyaan dari dokumen multi-format dengan **source tracing** ke nama file, halaman, slide, atau sheet.

Dibangun sebagai Take Home Test AI Engineer — PT Altimeda Cipta Visitama.

---

## Tech Stack

| Komponen | Pilihan |
|---|---|
| Language | Python 3.11 |
| API | FastAPI |
| Vector DB | PostgreSQL + pgvector |
| Embedding | OpenAI `text-embedding-3-small` |
| LLM | Groq `llama-3.3-70b-specdec` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Monitoring | Langfuse |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Setup & Cara Run

### Prerequisites
- Docker & Docker Compose
- API Keys: OpenAI, Groq
- (Opsional) Langfuse account

### 1. Clone & Konfigurasi

```bash
git clone https://github.com/<username>/document-intelligence-system.git
cd document-intelligence-system

cp .env.example .env
# Edit .env dan isi API keys
```

### 2. Jalankan dengan Docker Compose

```bash
docker compose up --build
```

API berjalan di `http://localhost:8000`
UI Chatbot di `http://localhost:8000/chat`
Swagger docs di `http://localhost:8000/docs`

### 3. Run Lokal (tanpa Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn main:app --reload
```

### 4. Run Tests

```bash
pytest tests/ -v
```

---

## Cara Penggunaan

### Via UI Chatbot

1. Buka `http://localhost:8000/chat`
2. Drag & drop dokumen ke panel kiri (PDF, DOCX, PPTX, XLSX, CSV)
3. Tunggu proses indexing selesai
4. Ketik pertanyaan di kolom chat

### Via API

**Upload dokumen:**
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@dokumen.pdf"
```

**Query:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Apa prosedur audit internal?", "top_k": 5}'
```

**Response:**
```json
{
  "answer": "Berdasarkan dokumen ISO_9001.pdf halaman 12, prosedur audit internal mencakup...",
  "sources": [
    {
      "filename": "ISO_9001.pdf",
      "page_number": 12,
      "excerpt": "Internal audits shall be conducted at planned intervals..."
    }
  ],
  "latency_ms": 1240
}
```

---

## API Endpoints

| Method | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/upload` | Upload & proses dokumen |
| `POST` | `/query` | Tanya jawab dengan source tracing |
| `GET` | `/documents` | List semua dokumen terindeks |
| `GET` | `/documents/{id}` | Detail dokumen |
| `DELETE` | `/documents/{id}` | Hapus dokumen dari knowledge base |
| `GET` | `/health` | Health check |
| `GET` | `/chat` | UI Chatbot |

---

## Struktur Project

```
document-intelligence-system/
├── app/
│   ├── api/routes/         # upload.py, query.py, documents.py
│   ├── core/               # config.py, database.py
│   ├── ingestion/          # detector, extractors, chunker, embedder
│   ├── retrieval/          # searcher.py, reranker.py
│   ├── generation/         # generator.py (Groq + Langfuse)
│   └── models/             # SQLAlchemy ORM
├── tests/
├── docker/
│   └── init.sql
├── sample_docs/
│   ├── pdf/
│   ├── docx/
│   ├── pptx/
│   ├── xlsx/
│   └── csv/
├── .github/workflows/ci.yml
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```