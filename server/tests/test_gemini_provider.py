"""Gemini provider tests using httpx.MockTransport (no network, no key)."""

import httpx
import pytest

from app.errors import ProviderRateLimited, ProviderUnavailable
from app.providers.gemini import BASE_URL, EMBED_BATCH_SIZE, GeminiChat, GeminiEmbeddings, GeminiHttp


def make_http(handler, max_retries=2):
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    client = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return GeminiHttp("secret-key", 5, max_retries, 1.0, client=client, sleep=fake_sleep), sleeps


async def test_embed_documents_batches_requests_and_keeps_order():
    batches: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        batches.append(len(body["requests"]))
        assert request.headers["x-goog-api-key"] == "secret-key"
        assert "secret-key" not in str(request.url)  # key never in the URL
        assert body["requests"][0]["taskType"] == "RETRIEVAL_DOCUMENT"
        return httpx.Response(200, json={"embeddings": [{"values": [float(len(r["content"]["parts"][0]["text"]))]} for r in body["requests"]]})

    http, _ = make_http(handler)
    texts = ["a" * (i + 1) for i in range(EMBED_BATCH_SIZE + 5)]
    vectors = await GeminiEmbeddings(http, "m", 8).embed_documents(texts)
    assert batches == [EMBED_BATCH_SIZE, 5]
    assert [v[0] for v in vectors] == [float(i + 1) for i in range(len(texts))]


async def test_rate_limit_is_retried_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"error": "quota"})
        return httpx.Response(200, json={"embedding": {"values": [0.1, 0.2]}})

    http, sleeps = make_http(handler)
    assert await GeminiEmbeddings(http, "m", 2).embed_query("hi") == [0.1, 0.2]
    assert calls["n"] == 3 and sleeps == [1.0, 2.0]  # exponential backoff


async def test_persistent_rate_limit_raises_429_error():
    http, _ = make_http(lambda r: httpx.Response(429, json={}), max_retries=1)
    with pytest.raises(ProviderRateLimited):
        await GeminiEmbeddings(http, "m", 2).embed_query("hi")


class FakeInteraction:
    def __init__(self, output_text="Hello there"):
        self.output_text = output_text


class FakeInteractions:
    def __init__(self, result=None, error=None):
        self.result = result or FakeInteraction()
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.result


class FakeSdkClient:
    def __init__(self, interactions):
        self.interactions = interactions
        self.closed = False

    def close(self):
        self.closed = True


async def test_interactions_api_chat_uses_low_thinking_and_system_instruction():
    interactions = FakeInteractions()
    client = FakeSdkClient(interactions)
    chat = GeminiChat("secret-key", "models/gemini-3.8-flash", 90, client=client)

    assert await chat.generate("Use only document context", "What is the policy?") == "Hello there"
    assert interactions.kwargs == {
        "model": "gemini-3.8-flash",
        "system_instruction": "Use only document context",
        "input": "What is the policy?",
        "generation_config": {"max_output_tokens": 1024, "thinking_level": "low"},
    }


async def test_interactions_api_empty_answer_is_rejected():
    chat = GeminiChat("secret-key", "gemini-3.8-flash", 90, client=FakeSdkClient(FakeInteractions(FakeInteraction("  "))))
    with pytest.raises(ProviderUnavailable, match="empty answer"):
        await chat.generate("system", "question")


async def test_interactions_api_failure_maps_to_safe_provider_error():
    interactions = FakeInteractions(error=TimeoutError("private request detail"))
    chat = GeminiChat("secret-key", "gemini-3.8-flash", 90, client=FakeSdkClient(interactions))
    with pytest.raises(ProviderUnavailable) as error:
        await chat.generate("system", "question")
    assert "private request detail" not in error.value.message


async def test_interactions_sdk_client_is_closed():
    client = FakeSdkClient(FakeInteractions())
    chat = GeminiChat("secret-key", "gemini-3.8-flash", 90, client=client)
    await chat.aclose()
    assert client.closed


def test_chat_model_default_uses_current_configured_model():
    from app.config import Settings

    assert Settings().gemini_chat_model == "gemini-3.8-flash"




def test_provider_timeout_defaults_allow_slow_generation():
    from app.config import Settings

    assert Settings().provider_timeout_seconds == 90.0
    assert Settings().provider_max_retries == 1
