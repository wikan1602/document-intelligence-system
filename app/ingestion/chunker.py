import tiktoken

from app.core.config import settings
from app.ingestion.detector import DocumentFormat
from app.ingestion.extractors.base import ExtractedChunk

# Gunakan encoder cl100k_base (sama dengan text-embedding-3-small)
_encoder = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def _split_by_tokens(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """
    Split teks menjadi potongan berdasarkan jumlah token.
    Menggunakan sliding window dengan overlap.
    """
    tokens = _encoder.encode(text)
    chunks: list[str] = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = _encoder.decode(chunk_tokens).strip()
        if chunk_text:
            chunks.append(chunk_text)
        if end == len(tokens):
            break
        start += chunk_size - chunk_overlap

    return chunks


def chunk_extracted(
    extracted: list[ExtractedChunk],
    fmt: DocumentFormat,
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
) -> list[ExtractedChunk]:
    """
    Terapkan chunking strategy sesuai format dokumen.

    - PDF   : sliding window per halaman (split jika halaman > chunk_size token)
    - DOCX  : per section/heading (split jika section terlalu panjang)
    - PPTX  : per slide — tidak di-split (1 slide = 1 chunk)
    - XLSX  : per row-group — tidak di-split lebih lanjut
    - CSV   : per line-group — tidak di-split lebih lanjut
    """
    result: list[ExtractedChunk] = []

    for source_chunk in extracted:
        if source_chunk.is_empty():
            continue

        token_count = _count_tokens(source_chunk.text)

        # Format yang perlu sliding window kalau konten terlalu panjang
        needs_split = fmt in (DocumentFormat.PDF, DocumentFormat.DOCX)

        if needs_split and token_count > chunk_size:
            sub_texts = _split_by_tokens(source_chunk.text, chunk_size, chunk_overlap)
            for sub_text in sub_texts:
                result.append(
                    ExtractedChunk(
                        text=sub_text,
                        page_number=source_chunk.page_number,
                        slide_number=source_chunk.slide_number,
                        slide_title=source_chunk.slide_title,
                        sheet_name=source_chunk.sheet_name,
                        row_range=source_chunk.row_range,
                        heading=source_chunk.heading,
                        metadata=source_chunk.metadata,
                    )
                )
        else:
            result.append(source_chunk)

    return result
