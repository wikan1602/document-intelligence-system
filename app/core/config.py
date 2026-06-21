# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Variabel Database & OpenAI ---
    database_url: str
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"

    # --- pgvector Dimension ---
    embedding_dimensions: int = 1536

    # --- Groq LLM ---
    groq_api_key: str
    llm_model: str = "llama-3.3-70b-versatile"

    # --- Parameter Chunking ---
    chunk_size: int = 512
    chunk_overlap: int = 50

    # 📄 PENYELARASAN: Tambahkan parameter jumlah retrieval default untuk searcher.py
    top_k_results: int = 5

    # --- Variabel Langfuse Monitoring ---
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # --- Konfigurasi Pydantic ---
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
