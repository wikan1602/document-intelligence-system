from enum import StrEnum
from pathlib import Path


class DocumentFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    TXT = "txt"


# Fallback map ekstensi → format (kalau MIME tidak cukup)
_EXT_MAP: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".pptx": DocumentFormat.PPTX,
    ".xlsx": DocumentFormat.XLSX,
    ".csv": DocumentFormat.CSV,
    ".txt": DocumentFormat.TXT,
}

# MIME type → format
_MIME_MAP: dict[str, DocumentFormat] = {
    "application/pdf": DocumentFormat.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentFormat.DOCX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentFormat.PPTX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentFormat.XLSX,
    "text/csv": DocumentFormat.CSV,
    "text/plain": DocumentFormat.TXT,
}


def detect_format(filename: str, content_type: str | None = None) -> DocumentFormat:
    """
    Deteksi format dokumen berdasarkan MIME type dan ekstensi file.

    Priority:
    1. content_type dari HTTP header (paling eksplisit)
    2. ekstensi filename (fallback)

    Raises:
        ValueError: jika format tidak didukung
    """
    # Coba dari content_type dulu
    if content_type:
        fmt = _MIME_MAP.get(content_type.lower().split(";")[0].strip())
        if fmt:
            return fmt

    # Fallback ke ekstensi
    ext = Path(filename).suffix.lower()
    fmt = _EXT_MAP.get(ext)
    if fmt:
        return fmt

    raise ValueError(
        f"Format tidak didukung: filename='{filename}', content_type='{content_type}'. "
        f"Format yang didukung: {', '.join(_EXT_MAP.keys())}"
    )


SUPPORTED_EXTENSIONS = list(_EXT_MAP.keys())
SUPPORTED_MIME_TYPES = list(_MIME_MAP.keys())
