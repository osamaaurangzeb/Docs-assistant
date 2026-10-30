import pytest

from app.errors import SessionNotFound
from app.services.session_store import SessionStore
from app.services.vector_store import VectorIndex


def index(label: str) -> VectorIndex:
    return VectorIndex([label], [[1.0, 0.0]])


def test_sessions_are_isolated():
    store = SessionStore(ttl_seconds=60, max_sessions=10)
    a = store.create(index("doc A"))
    b = store.create(index("doc B"))
    assert a != b
    assert store.get(a).index.search([1, 0], 1)[0].text == "doc A"
    assert store.get(b).index.search([1, 0], 1)[0].text == "doc B"


def test_unknown_session_raises():
    with pytest.raises(SessionNotFound):
        SessionStore(60, 10).get("nope")


def test_sessions_expire_after_ttl():
    now = [0.0]
    store = SessionStore(ttl_seconds=10, max_sessions=10, clock=lambda: now[0])
    sid = store.create(index("doc"))
    now[0] = 5
    store.get(sid)  # touching it renews the TTL
    now[0] = 14
    store.get(sid)
    now[0] = 30
    with pytest.raises(SessionNotFound):
        store.get(sid)


def test_oldest_idle_session_is_evicted_at_capacity():
    now = [0.0]
    store = SessionStore(ttl_seconds=1000, max_sessions=2, clock=lambda: now[0])
    first = store.create(index("1"))
    now[0] = 1
    second = store.create(index("2"))
    now[0] = 2
    third = store.create(index("3"))
    assert len(store) == 2
    with pytest.raises(SessionNotFound):
        store.get(first)
    store.get(second)
    store.get(third)


def test_delete():
    store = SessionStore(60, 10)
    sid = store.create(index("doc"))
    assert store.delete(sid) is True
    assert store.delete(sid) is False
