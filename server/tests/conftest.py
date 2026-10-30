import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.factory import create_app
from app.services.rag import RagService
from app.services.session_store import SessionStore
from tests.fakes import FakeEmbedder, FakeLLM


@pytest.fixture
def settings() -> Settings:
    return Settings(
        gemini_api_key="test-key",
        chunk_size=200,
        chunk_overlap=30,
        top_k=2,
        min_similarity=0.2,
        max_document_bytes=5_000,
    )


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(settings, embedder, llm) -> TestClient:
    rag = RagService(
        embedder,
        llm,
        SessionStore(ttl_seconds=3600, max_sessions=10),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        top_k=settings.top_k,
        min_similarity=settings.min_similarity,
    )
    with TestClient(create_app(settings=settings, rag=rag)) as c:
        yield c
