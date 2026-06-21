import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.api.dependencies import get_db
from app.ingestion.detector import detect_format

# 📄 PENYELARASAN 1: Import fungsi chunk_extracted yang asli
from app.ingestion.chunker import chunk_extracted
from app.ingestion.embedder import embed_texts
from app.models.document import Document
from app.models.chunk import Chunk

router = APIRouter(prefix="/upload", tags=["Ingestion"])

TEMP_DIR = "/tmp/uploaded_docs"
os.makedirs(TEMP_DIR, exist_ok=True)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    temp_file_path = os.path.join(TEMP_DIR, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_file_path)

        detector_result = detect_format(temp_file_path)
        if not detector_result or not detector_result.get("supported"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format file '{file.filename}' tidak didukung.",
            )

        file_format = detector_result["format"]
        extractor = detector_result["extractor"]

        extracted_pages = extractor.extract(temp_file_path)
        if not extracted_pages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Gagal mengekstrak teks atau dokumen kosong.",
            )

        db_document = Document(
            filename=file.filename,
            format=str(
                file_format
            ),  # Pastikan diconvert string jika kolom DB bertipe string
            file_size=file_size,
            metadata={"content_type": file.content_type},
        )
        db.add(db_document)
        db.flush()

        # 📄 PENYELARASAN 2: Panggil fungsi chunk_extracted asli milik Anda
        chunks_data = chunk_extracted(extracted_pages, file_format)

        # 📄 PENYELARASAN 3: Ambil konten string menggunakan .text sesuai schema ExtractedChunk Anda
        texts_to_embed = [c.text for c in chunks_data]

        embeddings = embed_texts(texts_to_embed)

        for idx, (chunk_obj, embedding) in enumerate(zip(chunks_data, embeddings)):
            db_chunk = Chunk(
                document_id=db_document.id,
                content=chunk_obj.text,  # <-- Menggunakan chunk_obj.text dari ExtractedChunk
                embedding=embedding,
                chunk_index=idx,
                page_number=chunk_obj.page_number,
                slide_number=chunk_obj.slide_number,
                slide_title=chunk_obj.slide_title,
                sheet_name=chunk_obj.sheet_name,
                row_range=chunk_obj.row_range,
                heading=chunk_obj.heading,
                metadata=chunk_obj.metadata if chunk_obj.metadata else {},
            )
            db.add(db_chunk)

        db.commit()

        return {
            "document_id": str(db_document.id),
            "filename": db_document.filename,
            "format": str(db_document.format),
            "chunk_count": len(chunks_data),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses dokumen: {str(e)}",
        )
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
