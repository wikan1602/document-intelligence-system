from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from app.api.dependencies import get_db
from app.models.document import Document
from app.models.chunk import Chunk

router = APIRouter(prefix="/documents", tags=["Document Management"])

class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    format: str
    file_size: int | None
    uploaded_at: datetime
    chunk_count: int

    class Config:
        from_attributes = True

@router.get("", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    try:
        documents = db.query(Document).all()
        result = []
        for doc in documents:
            # Hitung jumlah chunk untuk dokumen ini
            count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
            result.append({
                "id": doc.id,
                "filename": doc.filename,
                "format": str(doc.format),
                "file_size": doc.file_size,
                "uploaded_at": doc.uploaded_at,
                "chunk_count": count
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal query ke database: {str(e)}")

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_document(id: UUID, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    try:
        db.delete(document)
        db.commit()
        return {"message": "Sukses menghapus dokumen beserta seluruh chunk-nya."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))