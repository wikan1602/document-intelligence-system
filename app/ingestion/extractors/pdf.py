import io

import fitz  # PyMuPDF

from app.ingestion.extractors.base import BaseExtractor, ExtractedChunk


class PDFExtractor(BaseExtractor):
    """
    Ekstrak teks dari PDF per halaman menggunakan PyMuPDF (fitz).
    Menyaring halaman noise (terlalu pendek atau Daftar Isi) agar tidak mengotori database.
    Menyimpan page_number untuk source tracing.
    """

    def _is_too_short(self, text: str) -> bool:
        """Mengeliminasi halaman cover, halaman kosong, atau transisi bab."""
        return len(text.split()) < 50

    def _is_table_of_contents(self, text: str) -> bool:
        """Mendeteksi halaman Daftar Isi berdasarkan dominasi leader dots (.....)."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return False

        # Hitung baris yang mengandung deretan titik khas indeks Daftar Isi
        toc_lines_count = sum(
            1 for line in lines if "..." in line or line.count("..") >= 2
        )

        # Jika lebih dari 40% baris berupa format titik indeks, tandai sebagai ToC
        return (toc_lines_count / len(lines)) > 0.4

    def extract(self, file_bytes: bytes, filename: str) -> list[ExtractedChunk]:
        chunks: list[ExtractedChunk] = []

        doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue

            # 📄 FILTER HEURISTIK: Skip halaman noise sebelum diproses lebih jauh
            if self._is_too_short(text) or self._is_table_of_contents(text):
                continue

            chunks.append(
                ExtractedChunk(
                    text=text,
                    page_number=page_num,
                    metadata={"total_pages": doc.page_count, "filename": filename},
                )
            )

        doc.close()
        return chunks
