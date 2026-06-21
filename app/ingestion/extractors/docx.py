import io

from docx import Document
from docx.oxml.ns import qn

from app.ingestion.extractors.base import BaseExtractor, ExtractedChunk


def _is_heading(paragraph) -> bool:
    return paragraph.style.name.startswith("Heading")


class DOCXExtractor(BaseExtractor):
    """
    Ekstrak teks dari DOCX dengan grouping per section/heading.
    Kalau tidak ada heading, fallback ke per-paragraph grouping.
    Menyimpan heading text untuk source tracing.
    """

    def extract(self, file_bytes: bytes, filename: str) -> list[ExtractedChunk]:
        doc = Document(io.BytesIO(file_bytes))
        chunks: list[ExtractedChunk] = []

        current_heading: str | None = None
        current_texts: list[str] = []
        paragraph_index: int = 0

        def flush(heading: str | None, texts: list[str], para_idx: int) -> None:
            combined = "\n".join(t for t in texts if t.strip())
            if combined.strip():
                chunks.append(
                    ExtractedChunk(
                        text=combined,
                        heading=heading,
                        metadata={"paragraph_index": para_idx, "filename": filename},
                    )
                )

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            if _is_heading(para):
                # Flush section sebelumnya
                flush(current_heading, current_texts, paragraph_index)
                current_heading = text
                current_texts = []
                paragraph_index += 1
            else:
                current_texts.append(text)
                paragraph_index += 1

        # Flush sisa
        flush(current_heading, current_texts, paragraph_index)

        return chunks
