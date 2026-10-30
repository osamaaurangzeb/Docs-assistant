"""RAG orchestration: ingest (chunk -> embed -> store) and ask (embed -> retrieve -> answer)."""

import logging
from dataclasses import dataclass

from app.errors import ValidationFailed
from app.providers.base import EmbeddingProvider, LLMProvider
from app.services.chunker import split_text
from app.services.prompts import NOT_FOUND_MESSAGE, SYSTEM_PROMPT, build_user_prompt
from app.services.session_store import SessionStore
from app.services.vector_store import VectorIndex

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    session_id: str
    chunk_count: int


@dataclass(frozen=True)
class Source:
    chunk_index: int
    score: float
    text: str


@dataclass(frozen=True)
class Answer:
    answer: str
    sources: list[Source]


class RagService:
    def __init__(
        self,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        store: SessionStore,
        *,
        chunk_size: int,
        chunk_overlap: int,
        top_k: int,
        min_similarity: float,
    ):
        self._embedder = embedder
        self._llm = llm
        self._store = store
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._top_k = top_k
        self._min_similarity = min_similarity

    async def ingest(self, text: str) -> IngestResult:
        chunks = split_text(text, self._chunk_size, self._chunk_overlap)
        if not chunks:
            raise ValidationFailed("The document has no readable text.")
        embeddings = await self._embedder.embed_documents(chunks)
        session_id = self._store.create(VectorIndex(chunks, embeddings))
        logger.info("Ingested document: %d chunks", len(chunks))
        return IngestResult(session_id, len(chunks))

    async def ask(self, session_id: str, question: str) -> Answer:
        # Look the session up first: an unknown id must fail before we spend
        # any provider quota.
        session = self._store.get(session_id)

        query_embedding = await self._embedder.embed_query(question)
        matches = session.index.search(query_embedding, self._top_k, self._min_similarity)

        if not matches:
            # Nothing in the document is similar enough: answer without the LLM.
            logger.info("No chunk above similarity threshold; skipping LLM")
            return Answer(NOT_FOUND_MESSAGE, [])

        # Only the retrieved chunks (never the full document) reach the model.
        answer = await self._llm.generate(
            SYSTEM_PROMPT, build_user_prompt(question, [m.text for m in matches])
        )
        return Answer(answer, [Source(m.index, m.score, m.text) for m in matches])

    def delete_session(self, session_id: str) -> bool:
        return self._store.delete(session_id)
