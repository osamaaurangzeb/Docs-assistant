"""In-memory vector index with cosine-similarity search.

One `VectorIndex` is built per document/session. Vectors are L2-normalised once
at construction so a query is a single matrix-vector product.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Match:
    index: int  # position of the chunk within the document
    score: float  # cosine similarity in [-1, 1]
    text: str


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0  # a zero vector stays zero -> similarity 0
    return matrix / norms


class VectorIndex:
    def __init__(self, chunks: list[str], embeddings: list[list[float]]):
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            raise ValueError("cannot index an empty document")
        self._chunks = chunks
        self._matrix = _normalize(np.asarray(embeddings, dtype=np.float32))

    def __len__(self) -> int:
        return len(self._chunks)

    def search(
        self, query_embedding: list[float], top_k: int, min_score: float = 0.0
    ) -> list[Match]:
        query = _normalize(np.asarray(query_embedding, dtype=np.float32))
        if query.shape[-1] != self._matrix.shape[1]:
            raise ValueError("query and index embedding dimensions differ")
        scores = self._matrix @ query
        order = np.argsort(-scores)[:top_k]
        return [
            Match(index=int(i), score=float(scores[i]), text=self._chunks[i])
            for i in order
            if scores[i] >= min_score
        ]
