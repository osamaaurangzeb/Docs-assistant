"""Composition root: the one place that wires settings -> concrete providers -> services."""

from app.config import Settings
from app.providers.gemini import GeminiChat, GeminiEmbeddings, GeminiHttp
from app.services.rag import RagService
from app.services.session_store import SessionStore


def build_rag_service(settings: Settings) -> tuple[RagService, tuple[GeminiHttp, GeminiChat]]:
    api_key = settings.gemini_api_key.get_secret_value()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy server/.env.example to server/.env and add your key."
        )
    http = GeminiHttp(
        api_key=api_key,
        timeout=settings.provider_timeout_seconds,
        max_retries=settings.provider_max_retries,
        retry_base_delay=settings.provider_retry_base_delay_seconds,
    )
    chat = GeminiChat(
        api_key=api_key,
        model=settings.gemini_chat_model,
        timeout=settings.provider_timeout_seconds,
    )
    rag = RagService(
        embedder=GeminiEmbeddings(http, settings.gemini_embedding_model, settings.embedding_dimensions),
        llm=chat,
        store=SessionStore(settings.session_ttl_seconds, settings.max_sessions),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        top_k=settings.top_k,
        min_similarity=settings.min_similarity,
    )
    return rag, (http, chat)
