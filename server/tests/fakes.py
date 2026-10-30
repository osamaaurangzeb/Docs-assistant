"""Deterministic fake providers so tests need no network and no API key."""

import re
import zlib

from app.errors import ProviderUnavailable

DIMS = 64


def _vector(text: str) -> list[float]:
    """Bag-of-words hashed into a fixed-size vector: shared words => similar vectors."""
    vec = [0.0] * DIMS
    for word in re.findall(r"\w+", text.lower()):
        vec[zlib.crc32(word.encode()) % DIMS] += 1.0
    return vec


class FakeEmbedder:
    def __init__(self):
        self.document_calls = 0
        self.query_calls = 0
        self.fail = False

    async def embed_documents(self, texts):
        if self.fail:
            raise ProviderUnavailable("embedding provider down")
        self.document_calls += 1
        return [_vector(t) for t in texts]

    async def embed_query(self, text):
        if self.fail:
            raise ProviderUnavailable("embedding provider down")
        self.query_calls += 1
        return _vector(text)


class FakeLLM:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.fail = False

    async def generate(self, system_prompt, user_prompt):
        if self.fail:
            raise ProviderUnavailable("llm provider down")
        self.calls.append((system_prompt, user_prompt))
        return "FAKE ANSWER"
