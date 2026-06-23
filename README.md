# Document Intelligence System

Sistem RAG (Retrieval-Augmented Generation) untuk menjawab pertanyaan dari dokumen internal multi-format dengan **source tracing** ke nama file, halaman, slide, atau sheet.

Dibangun sebagai Take Home Test AI Engineer — PT Altimeda Cipta Visitama.

---

## Tech Stack

| Komponen | Pilihan |
|---|---|
| Language | Python 3.11 |
| API | FastAPI |
| Vector DB | PostgreSQL + pgvector |
| Embedding | OpenAI `text-embedding-3-small` |
| LLM | Deepseek V4 Flash |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Monitoring | Langfuse |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Setup & Cara Run

### Prerequisites

- Docker & Docker Compose
- API Keys: OpenAI, Deepseek
- (Opsional) Langfuse account untuk monitoring

### 1. Clone & Konfigurasi

```bash
git clone https://github.com/wikan1602/document-intelligence-system.git
cd document-intelligence-system

cp .env.example .env
# Edit .env dan isi API keys
```

### 2. Jalankan dengan Docker Compose

```bash
docker compose up --build
```

| URL | Deskripsi |
|---|---|
| `http://localhost:8000` | API root |
| `http://localhost:8000/chat` | UI Chatbot |
| `http://localhost:8000/docs` | Swagger API Docs |
| `http://localhost:8000/health` | Health check |

### 3. Run Lokal (tanpa Docker)

Pastikan PostgreSQL dengan pgvector extension sudah berjalan.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn main:app --reload
```

### 4. Run Tests

```bash
pytest tests/ -v
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

## Contoh Q&A

### Upload Dokumen

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@ISO-9001-2015.pdf"
```

```json
{
  "document_id": "e3cc9f4f-5228-41f2-a177-292a7c29d034",
  "filename": "ISO-9001-2015.pdf",
  "format": "pdf",
  "chunk_count": 47
}
```

---

### Q&A 1 — Pertanyaan dari PDF

**Pertanyaan:**
> Apa prosedur audit internal menurut ISO 9001?

**Jawaban:**
> Berdasarkan ISO-9001-2015.pdf halaman 27, organisasi wajib melakukan audit internal pada interval yang direncanakan untuk memastikan sistem manajemen mutu memenuhi persyaratan standar dan diimplementasikan secara efektif. Prosedur mencakup: (a) perencanaan program audit mempertimbangkan pentingnya proses dan hasil audit sebelumnya, (b) penetapan kriteria dan ruang lingkup audit, (c) pemilihan auditor yang objektif dan tidak memihak, serta (d) pelaporan hasil audit kepada manajemen terkait.

**Sources:** `ISO-9001-2015.pdf` (Hal. 27)

---

### Q&A 2 — Pertanyaan dari XLSX

**Pertanyaan:**
> Berapa alokasi dana untuk proyek PRJ-AI-01?

**Jawaban:**
> Berdasarkan xlsx_alokasi_anggaran.xlsx Sheet Anggaran_IT baris 2, alokasi dana untuk proyek PRJ-AI-01 (Pengembangan Clinical Chatbot) adalah **Rp 750.000.000**, dengan penanggung jawab Wikan P.

**Sources:** `xlsx_alokasi_anggaran.xlsx` (Sheet: Anggaran_IT)

---

### Q&A 3 — Pertanyaan dari DOCX

**Pertanyaan:**
> Apa saja milestone utama di kuartal pertama proyek modernisasi infrastruktur?

**Jawaban:**
> Berdasarkan Proyek Modernisasi Infrastruktur TI.docx, Kuartal I berfokus pada inisiasi dan persiapan infrastruktur. Milestone utama meliputi: persetujuan desain arsitektur final, penandatanganan kontrak vendor, penyelesaian pengadaan perangkat utama, aktivasi lingkungan sandbox, dan penyelesaian baseline performa sistem lama.

**Sources:** `Proyek Modernisasi Infrastruktur TI.docx` (Bagian: Kuartal I – Inisiasi dan Persiapan Infrastruktur)

---

### Q&A 4 — Filter Dokumen Spesifik

Query dapat difilter ke dokumen tertentu menggunakan `document_id`:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Apa isi klausul 4.1?",
    "top_k": 5,
    "document_id": "e3cc9f4f-5228-41f2-a177-292a7c29d034"
  }'
```

Di UI `/chat`, gunakan dropdown **Cakupan Query** untuk memilih dokumen tertentu.

---

## Struktur Project

```
document-intelligence-system/
├── app/
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── upload.py
│   │       ├── query.py
│   │       └── documents.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── ingestion/
│   │   ├── detector.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── extractors/
│   │       ├── base.py
│   │       ├── pdf.py
│   │       ├── docx.py
│   │       ├── pptx.py
│   │       ├── xlsx.py
│   │       └── csv_txt.py
│   ├── retrieval/
│   │   ├── searcher.py
│   │   └── reranker.py
│   ├── generation/
│   │   └── generator.py
│   └── models/
│       ├── document.py
│       └── chunk.py
├── tests/
├── docker/
│   └── init.sql
├── sample_docs/
│   ├── pdf/
│   ├── docx/
│   ├── pptx/
│   ├── xlsx/
│   └── csv/
├── .github/workflows/
│   └── ci.yml
├── main.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── README.md
└── TECHNICAL.md
```

---

## Environment Variables

Salin `.env.example` ke `.env` dan isi nilai berikut:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/document_intelligence

OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...

# Langfuse (opsional)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```