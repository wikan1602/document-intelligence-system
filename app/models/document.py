from __future__ import annotations  # 💡 1. Tambahkan ini di baris paling atas untuk mempermudah string annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING  # 💡 2. Import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# 💡 3. Import Chunk HANYA untuk kebutuhan analisis IDE / Type Checker
if TYPE_CHECKING:
    from app.models.chunk import Chunk


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)   # pdf|docx|pptx|xlsx|csv
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # 💡 4. Sekarang Anda bisa menulis list[Chunk] tanpa tanda petik jika di atas memakai __future__ annotations
    chunks: Mapped[list[Chunk]] = relationship(  
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} format={self.format}>"