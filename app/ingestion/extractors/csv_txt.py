from app.ingestion.extractors.base import BaseExtractor, ExtractedChunk

LINES_PER_CHUNK = 100  # grouping per N baris


class CSVTXTExtractor(BaseExtractor):
    """
    Ekstrak konten CSV/TXT dengan sliding window per LINES_PER_CHUNK baris.
    Khusus untuk format CSV, baris pertama akan di-treat sebagai Header
    dan disisipkan di setiap chunk untuk menjaga konteks struktural.
    """

    def extract(self, file_bytes: bytes, filename: str) -> list[ExtractedChunk]:
        # Decode dengan fallback encoding
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")

        lines = text.splitlines()
        if not lines:
            return []

        chunks: list[ExtractedChunk] = []

        # Deteksi format berdasarkan ekstensi
        is_csv = filename.lower().endswith(".csv")

        header_line = ""
        start_idx = 0

        # Ekstrak header khusus untuk CSV
        if is_csv and lines:
            header_line = lines[0].strip()
            start_idx = 1  # Baris data bergeser mulai dari index 1

        # Edge case: File CSV kosong atau cuma berisi header
        if start_idx >= len(lines) and header_line:
            return [
                ExtractedChunk(
                    text=header_line,
                    row_range="1-1",
                    metadata={"filename": filename, "total_lines": len(lines)},
                )
            ]

        for i in range(start_idx, len(lines), LINES_PER_CHUNK):
            batch_original = lines[i : i + LINES_PER_CHUNK]
            if not batch_original:
                continue

            # Copy agar list lines asli tidak termodifikasi
            batch_to_join = batch_original.copy()

            # Tempelkan header di awal batch jika formatnya CSV
            if is_csv and header_line:
                batch_to_join.insert(0, header_line)

            content = "\n".join(batch_to_join).strip()
            if not content:
                continue

            # Melacak range baris aktual di file asli
            start_line = i + 1
            end_line = i + len(batch_original)

            chunks.append(
                ExtractedChunk(
                    text=content,
                    row_range=f"{start_line}-{end_line}",
                    metadata={"filename": filename, "total_lines": len(lines)},
                )
            )

        return chunks
