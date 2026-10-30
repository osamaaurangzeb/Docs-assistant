"""In-memory session store.

A session owns exactly one document's `VectorIndex`. Isolation is structural:
the only way to reach an index is `get(session_id)`, so a request can never see
another session's chunks. Sessions expire after `ttl_seconds` of inactivity and
the store is capped at `max_sessions` (oldest-idle evicted) so memory is bounded.
"""

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.errors import SessionNotFound
from app.services.vector_store import VectorIndex


@dataclass
class Session:
    id: str
    index: VectorIndex
    last_access: float = field(default_factory=time.monotonic)


class SessionStore:
    def __init__(
        self,
        ttl_seconds: int,
        max_sessions: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._ttl = ttl_seconds
        self._max = max_sessions
        self._clock = clock
        self._sessions: dict[str, Session] = {}

    def create(self, index: VectorIndex) -> str:
        self._purge_expired()
        while len(self._sessions) >= self._max:
            oldest = min(self._sessions.values(), key=lambda s: s.last_access)
            del self._sessions[oldest.id]
        # Unguessable id: knowing/guessing another session's id is the only
        # way to reach its data, so it must not be sequential.
        session_id = secrets.token_urlsafe(16)
        self._sessions[session_id] = Session(session_id, index, self._clock())
        return session_id

    def get(self, session_id: str) -> Session:
        self._purge_expired()
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFound("Session not found or expired. Please submit the document again.")
        session.last_access = self._clock()
        return session

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def __len__(self) -> int:
        return len(self._sessions)

    def _purge_expired(self) -> None:
        now = self._clock()
        expired = [sid for sid, s in self._sessions.items() if now - s.last_access > self._ttl]
        for sid in expired:
            del self._sessions[sid]
