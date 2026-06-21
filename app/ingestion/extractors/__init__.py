from app.ingestion.detector import DocumentFormat
from app.ingestion.extractors.base import BaseExtractor, ExtractedChunk
from app.ingestion.extractors.csv_txt import CSVTXTExtractor
from app.ingestion.extractors.docx import DOCXExtractor
from app.ingestion.extractors.pdf import PDFExtractor
from app.ingestion.extractors.pptx import PPTXExtractor
from app.ingestion.extractors.xlsx import XLSXExtractor

__all__ = ["BaseExtractor", "ExtractedChunk", "get_extractor"]

_EXTRACTOR_MAP: dict[DocumentFormat, type[BaseExtractor]] = {
    DocumentFormat.PDF: PDFExtractor,
    DocumentFormat.DOCX: DOCXExtractor,
    DocumentFormat.PPTX: PPTXExtractor,
    DocumentFormat.XLSX: XLSXExtractor,
    DocumentFormat.CSV: CSVTXTExtractor,
    DocumentFormat.TXT: CSVTXTExtractor,
}


def get_extractor(fmt: DocumentFormat) -> BaseExtractor:
    """Return extractor instance yang sesuai dengan format dokumen."""
    extractor_cls = _EXTRACTOR_MAP.get(fmt)
    if not extractor_cls:
        raise ValueError(f"Tidak ada extractor untuk format: {fmt}")
    return extractor_cls()
