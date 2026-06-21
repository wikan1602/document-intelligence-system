from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractedChunk:
    """
    Unit hasil ekstraksi dari dokumen — satu halaman, slide, atau section.
    Semua field source tracing bersifat opsional, diisi sesuai format.
    """

    text: str

    # Source tracing
    page_number: int | None = None  # PDF
    slide_number: int | None = None  # PPTX
    slide_title: str | None = None  # PPTX
    sheet_name: str | None = None  # XLSX
    row_range: str | None = None  # XLSX / CSV
    heading: str | None = None  # DOCX

    metadata: dict = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not self.text.strip()


class BaseExtractor(ABC):
    """
    Abstract base class untuk semua extractor.
    Setiap format (PDF, DOCX, dll) mengimplementasikan extract().
    """

    @abstractmethod
    def extract(self, file_bytes: bytes, filename: str) -> list[ExtractedChunk]:
        """
        Ekstrak konten dari file bytes.

        Args:
            file_bytes: raw bytes dari file yang diupload
            filename: nama file asli (untuk metadata)

        Returns:
            List of ExtractedChunk, satu per halaman/slide/section
        """
        ...
