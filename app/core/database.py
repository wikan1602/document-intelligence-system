from collections.abc import Generator

from pgvector.sqlalchemy import Vector  # noqa: F401  (re-exported for models)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # reconnect otomatis kalau koneksi putus
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Aktifkan pgvector extension dan buat semua tabel."""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yield DB session lalu tutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
