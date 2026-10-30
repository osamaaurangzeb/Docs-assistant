"""Provider interfaces.

The RAG service depends on these two small protocols only. Swapping Gemini for
OpenAI (or a fake in tests) means writing one class that satisfies them.
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks (one vector per input, same order)."""

    async def embed_query(self, text: str) -> list[float]:
        """Embed a user question."""


class LLMProvider(Protocol):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the model's text answer."""
