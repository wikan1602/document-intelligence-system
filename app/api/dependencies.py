from typing import Generator
from app.core.database import SessionLocal

def get_db() -> Generator:
    """
    Dependency helper untuk menyediakan database session per request
    dan memastikan session ditutup setelah request selesai.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()