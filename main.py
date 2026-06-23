# main.py
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.database import init_db
from app.api.routes.upload import router as upload_router
from app.api.routes.query import router as query_router
from app.api.routes.documents import router as documents_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    init_db()
    logger.info("Database initialized ✓")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Document Intelligence System",
    description="RAG-based Q&A dari dokumen multi-format dengan source tracing.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed}ms)")
    return response


app.include_router(upload_router, tags=["Ingestion"])
app.include_router(query_router, tags=["Query"])
app.include_router(documents_router, tags=["Documents"])


@app.get("/health", tags=["Health"])
def health_check():
    from app.core.database import engine
    import sqlalchemy
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version": "1.0.0",
    }

# Tambahkan/pastikan route ini ada di dalam main.py Anda
@app.get("/chat", response_class=HTMLResponse, tags=["UI Chatbot"])
async def get_chatbot_ui():
    """
    Dashboard Terintegrasi: Drag & Drop Ingestion, Knowledge Management (List & Delete),
    dan Chatbot Q&A RAG dengan Source Tracing.
    """
    html_content = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Intelligence System</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg: #0f1117;
            --surface: #1a1d27;
            --surface-2: #22263a;
            --border: #2a2f45;
            --accent: #6c8eff;
            --accent-dim: rgba(108,142,255,0.12);
            --accent-glow: rgba(108,142,255,0.25);
            --green: #3ecf8e;
            --green-dim: rgba(62,207,142,0.1);
            --red: #f87171;
            --red-dim: rgba(248,113,113,0.1);
            --text: #e2e8f0;
            --text-muted: #64748b;
            --text-dim: #94a3b8;
            --font: 'Inter', sans-serif;
            --mono: 'JetBrains Mono', monospace;
            --radius: 10px;
            --sidebar: 288px;
        }

        body {
            font-family: var(--font);
            background: var(--bg);
            color: var(--text);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* NAV */
        nav {
            height: 52px;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            flex-shrink: 0;
            z-index: 10;
        }

        .nav-brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .nav-icon {
            width: 30px;
            height: 30px;
            background: var(--accent);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            color: #fff;
            box-shadow: 0 0 12px var(--accent-glow);
        }

        .nav-title {
            font-size: 14px;
            font-weight: 700;
            letter-spacing: -0.3px;
            color: var(--text);
        }

        .nav-sub {
            font-size: 11px;
            color: var(--text-muted);
            font-family: var(--mono);
        }

        .nav-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 11px;
            font-weight: 600;
            color: var(--green);
            background: var(--green-dim);
            border: 1px solid rgba(62,207,142,0.2);
            padding: 3px 9px;
            border-radius: 20px;
        }

        .status-dot {
            width: 6px;
            height: 6px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .nav-link {
            font-size: 12px;
            font-weight: 500;
            color: var(--text-muted);
            text-decoration: none;
            padding: 5px 10px;
            border-radius: 6px;
            border: 1px solid var(--border);
            transition: all 0.15s;
        }

        .nav-link:hover {
            color: var(--accent);
            border-color: var(--accent);
            background: var(--accent-dim);
        }

        /* LAYOUT */
        .layout {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        /* SIDEBAR */
        aside {
            width: var(--sidebar);
            background: var(--surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }

        .sidebar-section {
            padding: 14px;
            border-bottom: 1px solid var(--border);
        }

        .section-label {
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 10px;
        }

        /* DROP ZONE */
        .drop-zone {
            border: 1.5px dashed var(--border);
            border-radius: var(--radius);
            padding: 18px 12px;
            text-align: center;
            cursor: pointer;
            position: relative;
            transition: all 0.2s;
        }

        .drop-zone:hover, .drop-zone.drag-over {
            border-color: var(--accent);
            background: var(--accent-dim);
        }

        .drop-zone input {
            position: absolute;
            inset: 0;
            opacity: 0;
            cursor: pointer;
            width: 100%;
            height: 100%;
        }

        .drop-icon {
            font-size: 22px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }

        .drop-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-dim);
        }

        .drop-sub {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 3px;
            font-family: var(--mono);
        }

        .upload-status {
            margin-top: 8px;
            font-size: 11px;
            font-weight: 500;
            padding: 6px 10px;
            border-radius: 6px;
            display: none;
        }

        .upload-status.loading { background: var(--accent-dim); color: var(--accent); display: block; }
        .upload-status.success { background: var(--green-dim); color: var(--green); display: block; }
        .upload-status.error { background: var(--red-dim); color: var(--red); display: block; }

        /* DOC LIST */
        .doc-list-wrap {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            padding: 14px;
        }

        .doc-list-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }

        .doc-badge {
            font-size: 10px;
            font-weight: 700;
            font-family: var(--mono);
            background: var(--surface-2);
            color: var(--text-muted);
            padding: 2px 7px;
            border-radius: 10px;
            border: 1px solid var(--border);
        }

        .doc-list {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .doc-list::-webkit-scrollbar { width: 4px; }
        .doc-list::-webkit-scrollbar-track { background: transparent; }
        .doc-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

        .doc-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 10px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: 8px;
            transition: all 0.15s;
            cursor: pointer;
        }

        .doc-item:hover { border-color: var(--accent); background: var(--accent-dim); }
        .doc-item.selected { border-color: var(--accent); background: var(--accent-dim); box-shadow: 0 0 0 1px var(--accent); }

        .doc-item-left {
            display: flex;
            align-items: center;
            gap: 8px;
            overflow: hidden;
            flex: 1;
        }

        .doc-icon { font-size: 15px; flex-shrink: 0; }
        .doc-icon.pdf { color: #f87171; }
        .doc-icon.docx { color: #60a5fa; }
        .doc-icon.pptx { color: #fb923c; }
        .doc-icon.xlsx, .doc-icon.csv { color: var(--green); }

        .doc-info { overflow: hidden; }
        .doc-name {
            font-size: 11px;
            font-weight: 600;
            color: var(--text);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .doc-meta {
            font-size: 10px;
            color: var(--text-muted);
            font-family: var(--mono);
        }

        .doc-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

        .doc-btn {
            width: 24px;
            height: 24px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            border-radius: 5px;
            cursor: pointer;
            font-size: 11px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }

        .doc-btn:hover { background: var(--red-dim); color: var(--red); }

        .empty-state {
            text-align: center;
            padding: 24px 12px;
            color: var(--text-muted);
            font-size: 12px;
            border: 1.5px dashed var(--border);
            border-radius: var(--radius);
        }

        .empty-state i { font-size: 20px; margin-bottom: 6px; display: block; }

        /* FILTER BAR */
        .filter-bar {
            padding: 8px 14px;
            border-top: 1px solid var(--border);
            background: var(--surface);
        }

        .filter-select {
            width: 100%;
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text);
            font-family: var(--font);
            font-size: 11px;
            padding: 6px 10px;
            border-radius: 7px;
            outline: none;
            cursor: pointer;
            transition: border-color 0.15s;
        }

        .filter-select:focus { border-color: var(--accent); }
        .filter-select option { background: var(--surface-2); }

        .filter-label {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 5px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        /* CHAT AREA */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: var(--bg);
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .chat-messages::-webkit-scrollbar { width: 4px; }
        .chat-messages::-webkit-scrollbar-track { background: transparent; }
        .chat-messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

        /* MESSAGES */
        .msg-row { display: flex; gap: 10px; max-width: 760px; }
        .msg-row.user { margin-left: auto; flex-direction: row-reverse; }

        .msg-avatar {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            flex-shrink: 0;
        }

        .msg-avatar.bot { background: var(--accent); color: #fff; box-shadow: 0 0 10px var(--accent-glow); }
        .msg-avatar.user { background: var(--surface-2); color: var(--text-dim); border: 1px solid var(--border); }
        .msg-avatar.loading { background: var(--surface-2); color: var(--text-muted); border: 1px solid var(--border); }

        .msg-bubble {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 14px;
            font-size: 13px;
            line-height: 1.65;
            color: var(--text);
            max-width: 100%;
        }

        .msg-row.user .msg-bubble {
            background: var(--accent);
            border-color: var(--accent);
            color: #fff;
            border-radius: 12px 4px 12px 12px;
        }

        .msg-bubble.loading {
            color: var(--text-muted);
            font-style: italic;
            font-size: 12px;
        }

        .msg-bubble p { white-space: pre-wrap; }

        /* SOURCES */
        .sources {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid var(--border);
        }

        .sources-label {
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 6px;
        }

        .source-tags { display: flex; flex-wrap: wrap; gap: 5px; }

        .source-tag {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 10px;
            font-weight: 600;
            font-family: var(--mono);
            background: var(--surface-2);
            color: var(--accent);
            border: 1px solid var(--border);
            padding: 3px 8px;
            border-radius: 5px;
        }

        .latency {
            font-size: 10px;
            font-family: var(--mono);
            color: var(--text-muted);
            text-align: right;
            margin-top: 6px;
        }

        /* SYSTEM MESSAGE */
        .sys-msg {
            text-align: center;
            padding: 4px 0;
        }

        .sys-msg span {
            font-size: 11px;
            font-weight: 500;
            color: var(--text-muted);
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 3px 10px;
            border-radius: 20px;
            font-family: var(--mono);
        }

        /* INPUT BAR */
        .input-bar {
            padding: 14px 24px;
            background: var(--surface);
            border-top: 1px solid var(--border);
            flex-shrink: 0;
        }

        .input-form {
            display: flex;
            gap: 8px;
            align-items: center;
            max-width: 900px;
            margin: 0 auto;
        }

        .input-field {
            flex: 1;
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text);
            font-family: var(--font);
            font-size: 13px;
            padding: 10px 14px;
            border-radius: 9px;
            outline: none;
            transition: border-color 0.15s;
        }

        .input-field::placeholder { color: var(--text-muted); }
        .input-field:focus { border-color: var(--accent); background: var(--bg); }

        .send-btn {
            background: var(--accent);
            color: #fff;
            border: none;
            padding: 10px 18px;
            border-radius: 9px;
            font-family: var(--font);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 7px;
            transition: all 0.15s;
            box-shadow: 0 0 12px var(--accent-glow);
            flex-shrink: 0;
        }

        .send-btn:hover { filter: brightness(1.1); }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .input-hint {
            text-align: center;
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 6px;
            font-family: var(--mono);
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
        }

        /* WELCOME */
        .welcome {
            display: flex;
            gap: 10px;
            max-width: 760px;
        }
    </style>
</head>
<body>

<nav>
    <div class="nav-brand">
        <div class="nav-icon"><i class="fa-solid fa-brain"></i></div>
        <div>
            <div class="nav-title">Document Intelligence</div>
            <div class="nav-sub">RAG · pgvector · Groq</div>
        </div>
    </div>
    <div class="nav-right">
        <div class="status-badge"><div class="status-dot"></div> DB Online</div>
        <a href="/docs" target="_blank" class="nav-link"><i class="fa-solid fa-code" style="margin-right:5px"></i>API Docs</a>
    </div>
</nav>

<div class="layout">
    <aside>
        <div class="sidebar-section">
            <div class="section-label">Upload Dokumen</div>
            <div class="drop-zone" id="dropZone">
                <input type="file" id="fileInput" />
                <div class="drop-icon"><i class="fa-solid fa-cloud-arrow-up"></i></div>
                <div class="drop-title">Drag & drop atau klik</div>
                <div class="drop-sub">PDF · DOCX · PPTX · XLSX · CSV</div>
            </div>
            <div class="upload-status" id="uploadStatus"></div>
        </div>

        <div class="doc-list-wrap">
            <div class="doc-list-header">
                <div class="section-label" style="margin-bottom:0">Knowledge Base</div>
                <span class="doc-badge" id="docCount">0</span>
            </div>
            <div class="doc-list" id="docList">
                <div class="empty-state">
                    <i class="fa-solid fa-circle-notch fa-spin"></i>
                    Memuat dokumen...
                </div>
            </div>
        </div>

        <div class="filter-bar">
            <div class="filter-label">Cakupan Query</div>
            <select class="filter-select" id="docFilter">
                <option value="">Semua dokumen</option>
            </select>
        </div>
    </aside>

    <div class="chat-area">
        <div class="chat-messages" id="chatBox">
            <div class="welcome">
                <div class="msg-avatar bot"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-bubble">
                    <p>Halo! Saya siap menjawab pertanyaan dari dokumen yang sudah diindeks. Upload file di panel kiri, lalu pilih cakupan query — semua dokumen atau satu dokumen tertentu.</p>
                </div>
            </div>
        </div>

        <div class="input-bar">
            <form class="input-form" id="queryForm">
                <input type="text" class="input-field" id="queryInput"
                    placeholder="Tanya sesuatu dari dokumen..." autocomplete="off" required />
                <button type="submit" class="send-btn" id="sendBtn">
                    Kirim <i class="fa-solid fa-paper-plane" style="font-size:11px"></i>
                </button>
            </form>
            <div class="input-hint" id="inputHint">Cakupan: semua dokumen</div>
        </div>
    </div>
</div>

<script>
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const docList = document.getElementById('docList');
    const docCount = document.getElementById('docCount');
    const chatBox = document.getElementById('chatBox');
    const queryForm = document.getElementById('queryForm');
    const docFilter = document.getElementById('docFilter');
    const inputHint = document.getElementById('inputHint');

    let docsCache = [];

    // --- FETCH DOCUMENTS ---
    async function fetchDocuments() {
        try {
            const res = await fetch('/documents');
            if (!res.ok) throw new Error();
            const data = await res.json();
            docsCache = data.documents || data;
            renderDocs(docsCache);
            updateFilter(docsCache);
        } catch {
            docList.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i>Gagal memuat dokumen.</div>`;
        }
    }

    function renderDocs(docs) {
        docCount.textContent = docs.length;
        if (!docs.length) {
            docList.innerHTML = `<div class="empty-state"><i class="fa-solid fa-folder-open"></i>Belum ada dokumen terindeks.</div>`;
            return;
        }
        docList.innerHTML = docs.map(doc => {
            const fmt = doc.format.toLowerCase();
            let iconClass = 'fa-file-lines';
            let colorClass = '';
            if (fmt.includes('pdf')) { iconClass = 'fa-file-pdf'; colorClass = 'pdf'; }
            else if (fmt.includes('docx')) { iconClass = 'fa-file-word'; colorClass = 'docx'; }
            else if (fmt.includes('pptx')) { iconClass = 'fa-file-powerpoint'; colorClass = 'pptx'; }
            else if (fmt.includes('xls') || fmt.includes('csv')) { iconClass = 'fa-file-excel'; colorClass = 'xlsx'; }

            return `<div class="doc-item" data-id="${doc.id}" onclick="selectDoc('${doc.id}', '${doc.filename.replace(/'/g,"\\'")}')">
                <div class="doc-item-left">
                    <div class="doc-icon ${colorClass}"><i class="fa-solid ${iconClass}"></i></div>
                    <div class="doc-info">
                        <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
                        <div class="doc-meta">${doc.chunk_count} chunks · ${fmt.toUpperCase()}</div>
                    </div>
                </div>
                <div class="doc-actions">
                    <button class="doc-btn" onclick="event.stopPropagation(); deleteDocument('${doc.id}', '${doc.filename.replace(/'/g,"\\'")}')">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </div>`;
        }).join('');
    }

    function updateFilter(docs) {
        const current = docFilter.value;
        docFilter.innerHTML = '<option value="">Semua dokumen</option>';
        docs.forEach(doc => {
            const opt = document.createElement('option');
            opt.value = doc.id;
            opt.textContent = doc.filename;
            docFilter.appendChild(opt);
        });
        if (current) docFilter.value = current;
        updateHint();
    }

    docFilter.addEventListener('change', () => {
        updateHint();
        // Sync highlight di doc list
        document.querySelectorAll('.doc-item').forEach(el => {
            el.classList.toggle('selected', el.dataset.id === docFilter.value);
        });
    });

    function selectDoc(id, filename) {
        docFilter.value = id;
        updateHint();
        document.querySelectorAll('.doc-item').forEach(el => {
            el.classList.toggle('selected', el.dataset.id === id);
        });
    }

    function updateHint() {
        const sel = docFilter.options[docFilter.selectedIndex];
        inputHint.textContent = docFilter.value
            ? `Cakupan: ${sel.textContent}`
            : 'Cakupan: semua dokumen';
    }

    // --- DELETE ---
    async function deleteDocument(id, filename) {
        if (!confirm(`Hapus "${filename}" dari knowledge base?`)) return;
        const res = await fetch(`/documents/${id}`, { method: 'DELETE' });
        if (res.ok) {
            if (docFilter.value === id) { docFilter.value = ''; updateHint(); }
            fetchDocuments();
            appendSysMsg(`"${filename}" dihapus dari knowledge base.`);
        } else {
            alert('Gagal menghapus dokumen.');
        }
    }

    // --- UPLOAD ---
    ['dragenter', 'dragover'].forEach(e => dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.add('drag-over'); }));
    ['dragleave', 'drop'].forEach(e => dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.remove('drag-over'); }));
    dropZone.addEventListener('drop', e => { if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files[0]); });
    fileInput.addEventListener('change', () => { if (fileInput.files.length) handleUpload(fileInput.files[0]); });

    async function handleUpload(file) {
        uploadStatus.className = 'upload-status loading';
        uploadStatus.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Mengindeks ${file.name}...`;
        fileInput.value = '';

        const form = new FormData();
        form.append('file', file);

        try {
            const res = await fetch('/upload', { method: 'POST', body: form });
            const data = await res.json();
            if (res.ok) {
                uploadStatus.className = 'upload-status success';
                uploadStatus.innerHTML = `<i class="fa-solid fa-check"></i> ${file.name} — ${data.chunk_count} chunks`;
                fetchDocuments();
                appendSysMsg(`"${file.name}" berhasil diindeks.`);
            } else {
                throw new Error(data.detail || 'Upload gagal.');
            }
        } catch (err) {
            uploadStatus.className = 'upload-status error';
            uploadStatus.innerHTML = `<i class="fa-solid fa-xmark"></i> ${err.message}`;
        }
    }

    // --- QUERY ---
    queryForm.addEventListener('submit', async e => {
        e.preventDefault();
        const input = document.getElementById('queryInput');
        const sendBtn = document.getElementById('sendBtn');
        const question = input.value.trim();
        if (!question) return;

        appendMsg(question, 'user');
        input.value = '';
        sendBtn.disabled = true;

        const loadingId = appendMsg('Mencari di dokumen...', 'loading');

        const body = { question, top_k: 5 };
        if (docFilter.value) body.document_id = docFilter.value;

        try {
            const res = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await res.json();
            document.getElementById(loadingId)?.remove();

            if (res.ok) {
                appendMsg(data.answer, 'bot', data.sources, data.latency_ms);
            } else {
                throw new Error(data.detail || 'Query gagal.');
            }
        } catch (err) {
            document.getElementById(loadingId)?.remove();
            appendMsg(`Error: ${err.message}`, 'bot');
        } finally {
            sendBtn.disabled = false;
        }
    });

    // --- RENDER HELPERS ---
    function appendMsg(text, type, sources = [], latency = null) {
        const id = 'msg-' + Math.random().toString(36).slice(2, 9);
        const row = document.createElement('div');
        row.id = id;
        row.className = `msg-row ${type === 'user' ? 'user' : ''}`;

        const avatarIcon = type === 'user' ? 'fa-user' : type === 'loading' ? 'fa-spinner fa-spin' : 'fa-robot';
        const avatarClass = type === 'user' ? 'user' : type === 'loading' ? 'loading' : 'bot';

        let sourcesHtml = '';
        if (sources?.length) {
            const unique = [];
            const seen = new Set();
            sources.forEach(s => {
                const k = `${s.filename}-${s.page_number}-${s.slide_number}-${s.sheet_name}`;
                if (!seen.has(k)) { seen.add(k); unique.push(s); }
            });
            sourcesHtml = `<div class="sources">
                <div class="sources-label"><i class="fa-solid fa-link" style="margin-right:4px"></i>Sumber</div>
                <div class="source-tags">${unique.map(s => {
                    let loc = '';
                    if (s.page_number) loc = ` :${s.page_number}`;
                    else if (s.slide_number) loc = ` slide:${s.slide_number}`;
                    else if (s.sheet_name) loc = ` [${s.sheet_name}]`;
                    return `<span class="source-tag"><i class="fa-solid fa-paperclip" style="font-size:9px"></i>${s.filename}${loc}</span>`;
                }).join('')}</div>
            </div>`;
        }

        const latencyHtml = latency ? `<div class="latency"><i class="fa-solid fa-bolt" style="margin-right:3px"></i>${latency}ms</div>` : '';

        row.innerHTML = `
            <div class="msg-avatar ${avatarClass}"><i class="fa-solid ${avatarIcon}"></i></div>
            <div class="msg-bubble ${type === 'loading' ? 'loading' : ''}">
                <p>${text}</p>
                ${sourcesHtml}
                ${latencyHtml}
            </div>`;

        chatBox.appendChild(row);
        chatBox.scrollTop = chatBox.scrollHeight;
        return id;
    }

    function appendSysMsg(text) {
        const el = document.createElement('div');
        el.className = 'sys-msg';
        el.innerHTML = `<span><i class="fa-solid fa-circle-info" style="margin-right:5px"></i>${text}</span>`;
        chatBox.appendChild(el);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    fetchDocuments();
</script>
</body>
</html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )