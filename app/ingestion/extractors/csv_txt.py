import io

from app.ingestion.extractors.base import BaseExtractor, ExtractedChunk

LINES_PER_CHUNK = 100  # grouping per N baris


class CSVTXTExtractor(BaseExtractor):
    """
    Ekstrak konten CSV/TXT dengan sliding window per LINES_PER_CHUNK baris.
    Menyimpan line_range untuk source tracing.
    """

    def extract(self, file_bytes: bytes, filename: str) -> list[ExtractedChunk]:
        # Decode dengan fallback encoding
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")

        lines = text.splitlines()
        chunks: list[ExtractedChunk] = []

        for i in range(0, len(lines), LINES_PER_CHUNK):
            batch = lines[i : i + LINES_PER_CHUNK]
            content = "\n".join(batch).strip()
            if not content:
                continue

            start_line = i + 1
            end_line = i + len(batch)

            chunks.append(
                ExtractedChunk(
                    text=content,
                    row_range=f"{start_line}-{end_line}",
                    metadata={"filename": filename, "total_lines": len(lines)},
                )
            )

        return chunks
