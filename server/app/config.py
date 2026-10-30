"""Application settings.

This is the ONLY module that reads environment variables / the .env file.
Everything else receives a `Settings` instance (or plain values) from the
composition root, which keeps secrets out of business logic and makes the
services trivial to test.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    # Provider credentials / models
    gemini_api_key: SecretStr = SecretStr("")
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_chat_model: str = "gemini-3.8-flash"
    embedding_dimensions: int = 768

    # RAG tuning
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 4
    min_similarity: float = 0.30

    # Limits
    max_document_bytes: int = 200_000
    max_question_chars: int = 1000
    session_ttl_seconds: int = 3600
    max_sessions: int = 200

    # Server
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_reload: bool = True

    # Networking
    cors_origins: str = "http://localhost:5173"
    provider_timeout_seconds: float = 90.0
    provider_max_retries: int = 1
    provider_retry_base_delay_seconds: float = 2.0

    @model_validator(mode="after")
    def _check_chunking(self) -> "Settings":
        if self.chunk_size < 100:
            raise ValueError("CHUNK_SIZE must be >= 100")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be >= 0 and < CHUNK_SIZE")
        if self.top_k < 1:
            raise ValueError("TOP_K must be >= 1")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
