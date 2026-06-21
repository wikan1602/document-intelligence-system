import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from app.api.dependencies import get_db
from app.ingestion.detector import detect_format

# 📄 PENYELARASAN 1: Import get_extractor yang sukses di unit test
from app.ingestion.extractors import get_extractor
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
        # 1. Simpan berkas sementara untuk menghitung ukuran file fisik
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_file_path)

        # 2. Ambil bytes data untuk diproses oleh extractor
        with open(temp_file_path, "rb") as f:
            file_bytes = f.read()

        # 3. Deteksi format (Mengembalikan DocumentFormat Enum)
        try:
            file_format = detect_format(file.filename, file.content_type)
        except ValueError as val_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(val_err),
            )

        # 4. Ambil extractor yang sesuai berdasarkan format dokumen
        extractor = get_extractor(file_format)
        extracted_pages = extractor.extract(file_bytes, file.filename)

        if not extracted_pages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Gagal mengekstrak teks atau dokumen kosong.",
            )

        # 5. Rekam entitas Document ke database metadata
        db_document = Document(
            filename=file.filename,
            format=str(file_format),  # Konversi enum ke string untuk kolom DB
            file_size=file_size,
            metadata={"content_type": file.content_type},
        )
        db.add(db_document)
        db.flush()

        # 6. Jalankan pemotongan teks secara semantik (Chunking)
        chunks_data = chunk_extracted(extracted_pages, file_format)

        # 7. Buat representasi vektor 1536 dimensi via OpenAI Embedding
        texts_to_embed = [c.text for c in chunks_data]
        embeddings = embed_texts(texts_to_embed)

        # 8. Lakukan bulk insert potongan chunk dokumen beserta vektornya ke pgvector
        for idx, (chunk_obj, embedding) in enumerate(zip(chunks_data, embeddings)):
            db_chunk = Chunk(
                document_id=db_document.id,
                content=chunk_obj.text,
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

    except HTTPException as http_ex:
        # Teruskan kembali HTTP Exception bawaan tanpa tertimpa block Exception global
        raise http_ex
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses dokumen: {str(e)}",
        )
    finally:
        # Bersihkan file sampah di folder /tmp agar storage server tidak penuh
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
