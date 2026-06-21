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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document Intelligence System Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            .chat-height { height: calc(100vh - 140px); }
            .doc-list-height { height: calc(100vh - 420px); }
            .drag-over { border-color: #4f46e5 !important; background-color: #e0e7ff !important; }
        </style>
    </head>
    <body class="bg-slate-100 font-sans text-slate-800 antialiased">
        <div class="h-screen flex flex-col">
            <nav class="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0 shadow-xs">
                <div class="flex items-center gap-3">
                    <div class="bg-indigo-600 text-white p-2 rounded-lg"><i class="fa-solid fa-brain text-lg"></i></div>
                    <div>
                        <h1 class="text-xl font-bold text-slate-900 tracking-tight">Document Intelligence</h1>
                        <p class="text-xs text-slate-500 font-medium">RAG Core Engine Active • Powered by Groq</p>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                        <span class="w-1.5 h-1.5 mr-1.5 bg-emerald-500 rounded-full animate-pulse"></span> DB Connected
                    </span>
                    <a href="/docs" target="_blank" class="text-sm font-semibold text-slate-600 hover:text-indigo-600 transition-colors"><i class="fa-solid fa-code mr-1"></i> Swagger API Docs →</a>
                </div>
            </nav>

            <div class="flex-1 flex overflow-hidden">
                <div class="w-80 bg-white border-r border-slate-200 flex flex-col shrink-0">
                    <div class="p-4 border-b border-slate-200">
                        <h2 class="font-bold text-xs text-slate-400 uppercase tracking-wider mb-3">Add Knowledge Source</h2>
                        <div id="dropZone" class="border-2 border-dashed border-slate-300 rounded-xl p-5 text-center cursor-pointer hover:border-indigo-500 hover:bg-slate-50 transition-all relative">
                            <input type="file" id="fileInput" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                            <i class="fa-solid fa-cloud-arrow-up text-3xl text-slate-400 mb-2"></i>
                            <p class="text-xs text-slate-600 font-semibold">Drag & Drop Berkas di Sini</p>
                            <p class="text-[10px] text-slate-400 mt-1">PDF, DOCX, PPTX, XLSX, CSV</p>
                        </div>
                        <div id="uploadStatus" class="mt-2 text-xs font-medium hidden"></div>
                    </div>

                    <div class="flex-1 flex flex-col overflow-hidden p-4">
                        <div class="flex items-center justify-between mb-3 shrink-0">
                            <h2 class="font-bold text-xs text-slate-400 uppercase tracking-wider">Active Knowledge Base</h2>
                            <span id="docCount" class="text-xs bg-slate-100 px-2 py-0.5 rounded-full font-bold text-slate-600">0 files</span>
                        </div>
                        <div id="docList" class="flex-1 overflow-y-auto space-y-2 doc-list-height pr-1">
                            <div class="text-center py-6 text-slate-400 text-xs"><i class="fa-solid fa-circle-notch animate-spin mr-1"></i> Memuat dokumen...</div>
                        </div>
                    </div>
                </div>

                <div class="flex-1 flex flex-col bg-slate-50 chat-height">
                    <div id="chatBox" class="flex-1 p-6 overflow-y-auto space-y-4">
                        <div class="flex gap-4 max-w-3xl">
                            <div class="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-md font-bold text-sm shrink-0"><i class="fa-solid fa-robot"></i></div>
                            <div class="bg-white p-4 rounded-2xl shadow-xs border border-slate-200/80">
                                <p class="text-sm leading-relaxed text-slate-700">Halo Wikan! Saya adalah Asisten AI Kecerdasan Dokumen Anda. Silakan jatuhkan (*drag & drop*) berkas SOP, regulasi, atau spreadsheet di panel kiri untuk diindeks ke database vektor, lalu ajukan pertanyaan Anda di sini!</p>
                            </div>
                        </div>
                    </div>

                    <div class="p-4 bg-white border-t border-slate-200 shadow-md shrink-0">
                        <div class="max-w-4xl mx-auto">
                            <form id="queryForm" class="flex gap-3">
                                <input type="text" id="queryInput" placeholder="Tanyakan isi dokumen Anda... (Contoh: Apa keputusan rapat tanggal X?)" class="flex-1 border border-slate-200 bg-slate-50 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 focus:bg-white transition-all shadow-inner" required autocomplete="off" />
                                <button type="submit" id="sendBtn" class="bg-indigo-600 text-white px-6 py-3 rounded-xl text-sm font-bold hover:bg-indigo-700 active:scale-98 transition-all flex items-center gap-2 shadow-md">
                                    <span>Kirim</span><i class="fa-solid fa-paper-plane text-xs"></i>
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('fileInput');
            const uploadStatus = document.getElementById('uploadStatus');
            const docList = document.getElementById('docList');
            const docCount = document.getElementById('docCount');
            const queryForm = document.getElementById('queryForm');
            const chatBox = document.getElementById('chatBox');

            // --- FUNGSI MENGAMBIL DAFTAR DOKUMEN (GET /documents) ---
            async function fetchDocuments() {
                try {
                    const response = await fetch('/documents');
                    if (!response.ok) throw new Error();
                    const docs = await response.json();
                    
                    docCount.innerText = `${docs.length} file${docs.length !== 1 ? 's' : ''}`;
                    
                    if (docs.length === 0) {
                        docList.innerHTML = `
                            <div class="text-center py-8 border-2 border-dashed border-slate-200 rounded-xl p-4 text-slate-400">
                                <i class="fa-solid fa-folder-open text-2xl mb-2 block"></i>
                                <p class="text-xs font-medium">Belum ada file terindeks.</p>
                            </div>
                        `;
                        return;
                    }

                    docList.innerHTML = docs.map(doc => {
                        let icon = 'fa-file-lines';
                        if (doc.format.toLowerCase().includes('pdf')) icon = 'fa-file-pdf text-rose-500';
                        else if (doc.format.toLowerCase().includes('docx')) icon = 'fa-file-word text-blue-500';
                        else if (doc.format.toLowerCase().includes('pptx')) icon = 'fa-file-powerpoint text-orange-500';
                        else if (doc.format.toLowerCase().includes('xls') || doc.format.toLowerCase().includes('csv')) icon = 'fa-file-excel text-emerald-500';

                        return `
                            <div class="flex items-center justify-between p-3 bg-slate-50 border border-slate-200/60 rounded-xl hover:shadow-xs transition-all group">
                                <div class="flex items-center gap-3 overflow-hidden">
                                    <div class="text-lg shrink-0"><i class="fa-solid ${icon}"></i></div>
                                    <div class="overflow-hidden">
                                        <p class="text-xs font-semibold text-slate-700 truncate" title="${doc.filename}">${doc.filename}</p>
                                        <p class="text-[10px] text-slate-400 font-medium">${doc.chunk_count} semantic chunks</p>
                                    </div>
                                </div>
                                <button onclick="deleteDocument('${doc.id}', '${doc.filename}')" class="text-slate-300 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer shrink-0" title="Hapus dari Knowledge Base">
                                    <i class="fa-solid fa-trash-can text-xs"></i>
                                </button>
                            </div>
                        `;
                    }).join('');
                } catch (err) {
                    docList.innerHTML = `<div class="text-xs text-red-500 text-center py-4">Gagal memuat basis pengetahuan.</div>`;
                }
            }

            // --- FUNGSI MENGHAPUS DOKUMEN (DELETE /documents/{id}) ---
            async function deleteDocument(id, filename) {
                if (!confirm(`Hapus "${filename}" dari database? Seluruh vektor chunk terkait akan ikut terhapus otomatis.`)) return;
                try {
                    const response = await fetch(`/documents/${id}`, { method: 'DELETE' });
                    if (response.ok) {
                        fetchDocuments();
                        appendSystemMessage(`Dokumen "${filename}" berhasil dihapus dari sistem.`);
                    } else {
                        alert('Gagal menghapus dokumen.');
                    }
                } catch (err) {
                    alert('Terjadi kesalahan koneksi.');
                }
            }

            // --- FITUR DRAG & DROP HANDLING (POST /upload) ---
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); }, false);
            });
            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.remove('drag-over'); }, false);
            });

            dropZone.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files.length) handleUpload(files[0]);
            });

            fileInput.addEventListener('change', (e) => {
                if (fileInput.files.length) handleUpload(fileInput.files[0]);
            });

            async function handleUpload(file) {
                const formData = new FormData();
                formData.append('file', file);

                uploadStatus.className = "mt-2 text-xs font-semibold text-indigo-600 block bg-indigo-50 border border-indigo-100 p-2 rounded-lg animate-pulse text-center";
                uploadStatus.innerHTML = `<i class="fa-solid fa-spinner animate-spin mr-1"></i> Mengonversi & Membuat Embedding...`;
                fileInput.value = '';

                try {
                    const response = await fetch('/upload', { method: 'POST', body: formData });
                    const data = await response.json();

                    if (response.ok) {
                        uploadStatus.className = "mt-2 text-xs font-semibold text-emerald-700 block bg-emerald-50 border border-emerald-100 p-2 rounded-lg text-center";
                        uploadStatus.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${file.name} terindeks (${data.chunk_count} chunk)!`;
                        fetchDocuments(); // Refresh daftar file
                        appendSystemMessage(`Dokumen "${file.name}" siap digunakan untuk Chatbot.`);
                    } else {
                        throw new Error(data.detail || 'Gagal memproses file.');
                    }
                } catch (err) {
                    uploadStatus.className = "mt-2 text-xs font-semibold text-rose-700 block bg-rose-50 border border-rose-100 p-2 rounded-lg text-center";
                    uploadStatus.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> ${err.message}`;
                }
            }

            // --- FITUR CHATBOT HANDLING (POST /query) ---
            queryForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const queryInput = document.getElementById('queryInput');
                const sendBtn = document.getElementById('sendBtn');
                const question = queryInput.value.trim();

                if (!question) return;

                appendMessage('User', question, 'user');
                queryInput.value = '';
                sendBtn.disabled = true;
                
                const loadingId = appendMessage('AI', 'Sedang melakukan kueri semantik dan merumuskan jawaban...', 'bot-loading');

                try {
                    const response = await fetch('/query', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question: question, top_k: 5 })
                    });
                    const data = await response.json();
                    
                    document.getElementById(loadingId).remove();

                    if (response.ok) {
                        appendMessage('AI', data.answer, 'bot', data.sources, data.latency_ms);
                    } else {
                        throw new Error(data.detail || 'Gagal mengambil jawaban.');
                    }
                } catch (err) {
                    if (document.getElementById(loadingId)) document.getElementById(loadingId).remove();
                    appendMessage('AI', `Terjadi gangguan: ${err.message}`, 'bot');
                } finally {
                    sendBtn.disabled = false;
                }
            });

            // --- HELPER UNTUK RENDERING ELEMEN OBROLAN ---
            function appendMessage(sender, text, type, sources = [], latency = null) {
                const messageId = 'msg-' + Math.random().toString(36).substr(2, 9);
                const wrapper = document.createElement('div');
                wrapper.id = messageId;
                wrapper.className = type === 'user' ? 'flex gap-4 max-w-2xl ml-auto justify-end' : 'flex gap-4 max-w-3xl';

                let sourcesHtml = '';
                if (sources && sources.length > 0) {
                    sourcesHtml = `<div class="mt-3 pt-2 border-t border-slate-100">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1"><i class="fa-solid fa-arrow-turn-up text-indigo-400 rotate-90 mr-1"></i> Referensi Sumber:</p>
                        <div class="flex flex-wrap gap-1.5">`;
                    
                    // Filter sumber unik agar tidak menumpuk badge yang sama
                    const uniqueSources = [];
                    const seen = new Set();
                    sources.forEach(src => {
                        let key = `${src.filename}-${src.page_number}-${src.sheet_name}-${src.slide_number}`;
                        if (!seen.has(key)) {
                            seen.add(key);
                            uniqueSources.push(src);
                        }
                    });

                    uniqueSources.forEach(src => {
                        let pos = '';
                        if (src.page_number) pos = ` (Hal. ${src.page_number})`;
                        else if (src.slide_number) pos = ` (Slide ${src.slide_number})`;
                        else if (src.sheet_name) pos = ` (Sheet: ${src.sheet_name})`;
                        
                        sourcesHtml += `<span class="inline-flex items-center text-[10px] bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded-lg border border-indigo-100 shadow-3xs">
                            <i class="fa-solid fa-paperclip text-[9px] mr-1 opacity-70"></i>${src.filename}${pos}
                        </span>`;
                    });
                    sourcesHtml += `</div></div>`;
                }

                let latencyHtml = latency ? `<p class="text-[9px] text-right text-slate-400 mt-1 font-medium"><i class="fa-solid fa-gauge-high mr-1"></i> Groq inference: ${latency}ms</p>` : '';

                if (type === 'user') {
                    wrapper.innerHTML = `
                        <div class="bg-indigo-600 text-white p-3.5 rounded-2xl rounded-tr-xs shadow-md text-sm leading-relaxed">
                            <p>${text}</p>
                        </div>
                    `;
                } else {
                    const avatarClass = type === 'bot-loading' ? 'bg-slate-400 animate-pulse' : 'bg-indigo-600 shadow-md';
                    const iconClass = type === 'bot-loading' ? 'fa-spinner animate-spin' : 'fa-robot';
                    wrapper.innerHTML = `
                        <div class="w-9 h-9 rounded-xl ${avatarClass} text-white flex items-center justify-center font-bold text-sm shrink-0"><i class="fa-solid ${iconClass}"></i></div>
                        <div class="bg-white p-4 rounded-2xl rounded-tl-xs shadow-xs border border-slate-200/80 text-sm flex-1">
                            <p class="whitespace-pre-line text-slate-700 leading-relaxed">${text}</p>
                            ${sourcesHtml}
                            ${latencyHtml}
                        </div>
                    `;
                }

                chatBox.appendChild(wrapper);
                chatBox.scrollTop = chatBox.scrollHeight;
                return messageId;
            }

            function appendSystemMessage(text) {
                const wrapper = document.createElement('div');
                wrapper.className = 'text-center py-1';
                wrapper.innerHTML = `<span class="inline-block bg-slate-200/70 text-slate-600 text-[11px] font-semibold px-3 py-1 rounded-full border border-slate-300/40 shadow-3xs"><i class="fa-solid fa-circle-info mr-1"></i> ${text}</span>`;
                chatBox.appendChild(wrapper);
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            // Jalankan ambil dokumen saat halaman dimuat pertama kali
            window.onload = fetchDocuments;
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