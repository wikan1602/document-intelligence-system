import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Source tracing — diisi sesuai format dokumen
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)    # PDF
    slide_number: Mapped[int | None] = mapped_column(Integer, nullable=True)   # PPTX
    slide_title: Mapped[str | None] = mapped_column(String, nullable=True)     # PPTX
    sheet_name: Mapped[str | None] = mapped_column(String, nullable=True)      # XLSX
    row_range: Mapped[str | None] = mapped_column(String, nullable=True)       # XLSX/CSV
    heading: Mapped[str | None] = mapped_column(String, nullable=True)         # DOCX

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Chunk id={self.id} doc={self.document_id} index={self.chunk_index}>"
