import io

import fitz  # PyMuPDF

from app.ingestion.extractors.base import BaseExtractor, ExtractedChunk


class PDFExtractor(BaseExtractor):
    """
    Ekstrak teks dari PDF per halaman menggunakan PyMuPDF (fitz).
    Menyimpan page_number untuk source tracing.
    """

    def extract(self, file_bytes: bytes, filename: str) -> list[ExtractedChunk]:
        chunks: list[ExtractedChunk] = []

        doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
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
