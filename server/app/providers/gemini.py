"""Google Gemini provider (free AI Studio key) over plain REST via httpx.

Why REST instead of the SDK: one dependency we already need, full control over
retries/timeouts, and trivial to mock in tests with `httpx.MockTransport`.

The API key is sent in the `x-goog-api-key` header (never in the URL) so it
cannot leak into access logs or error messages.
"""

import asyncio
import logging

from collections.abc import Awaitable, Callable

import httpx

from app.errors import ProviderRateLimited, ProviderUnavailable

logger = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
EMBED_BATCH_SIZE = 50  # API allows up to 100 per batch; stay well under
_RETRYABLE = {429, 500, 502, 503, 504}


class GeminiHttp:
    """Shared transport: auth header, timeout, retry with backoff, error mapping."""

    def __init__(
        self,
        api_key: str,
        timeout: float,
        max_retries: int,
        retry_base_delay: float,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        self._max_retries = max_retries
        self._base_delay = retry_base_delay
        self._client = client or httpx.AsyncClient(base_url=BASE_URL, timeout=timeout)
        self._sleep = sleep

    async def aclose(self) -> None:
        await self._client.aclose()

    async def post(self, path: str, payload: dict) -> dict:
        for attempt in range(self._max_retries + 1):
            last_attempt = attempt == self._max_retries
            try:
                response = await self._client.post(path, json=payload, headers=self._headers)
            except httpx.HTTPError as exc:
                logger.warning(
                    "Gemini transport error on %s (%s): %s",
                    path,
                    type(exc).__name__,
                    str(exc) or "no additional details",
                )
                if last_attempt:
                    raise ProviderUnavailable(
                        "The AI provider did not respond in time. Please try again."
                    ) from exc
                await self._sleep(self._base_delay * 2**attempt)
                continue

            if response.status_code == 200:
                return response.json()

            logger.warning("Gemini %s -> %s: %s", path, response.status_code, response.text[:300])
            if response.status_code in _RETRYABLE and not last_attempt:
                await self._sleep(self._retry_delay(response, attempt))
                continue
            self._raise_for_status(response.status_code)
        raise ProviderUnavailable("AI provider request failed.")  # pragma: no cover

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), 30.0)
        return self._base_delay * 2**attempt

    @staticmethod
    def _raise_for_status(status: int) -> None:
        if status == 429:
            raise ProviderRateLimited(
                "The AI provider's rate limit was reached (free tier). Wait a minute and retry."
            )
        if status in (401, 403):
            raise ProviderUnavailable("Gemini rejected the server's API key. Check GEMINI_API_KEY in server/.env.")
        if status == 404:
            raise ProviderUnavailable(
                "The configured Gemini model was not found. Check GEMINI_CHAT_MODEL and "
                "GEMINI_EMBEDDING_MODEL in server/.env."
            )
        raise ProviderUnavailable("Gemini returned an error. Check the server log for details.")


class GeminiEmbeddings:
    def __init__(self, http: GeminiHttp, model: str, dimensions: int):
        self._http = http
        self._model = model
        self._dimensions = dimensions

    def _request(self, text: str, task_type: str) -> dict:
        return {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
            "outputDimensionality": self._dimensions,
        }

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[start : start + EMBED_BATCH_SIZE]
            data = await self._http.post(
                f"/models/{self._model}:batchEmbedContents",
                {"requests": [self._request(t, "RETRIEVAL_DOCUMENT") for t in batch]},
            )
            embeddings = data.get("embeddings", [])
            if len(embeddings) != len(batch):
                raise ProviderUnavailable("The AI provider returned an unexpected embeddings response.")
            vectors.extend(e["values"] for e in embeddings)
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        data = await self._http.post(
            f"/models/{self._model}:embedContent", self._request(text, "RETRIEVAL_QUERY")
        )
        try:
            return data["embedding"]["values"]
        except (KeyError, TypeError) as exc:
            raise ProviderUnavailable("The AI provider returned an unexpected embedding response.") from exc


class GeminiChat:
    """Chat generation through Google's official Interactions API SDK.

    Embeddings continue to use the lightweight REST transport above. The SDK
    is used only for chat because the same Interactions API call is verified
    to work with the configured model/key in the project's smoke test.
    """

    def __init__(self, api_key: str, model: str, timeout: float, client=None):
        self._model = model.removeprefix("models/")
        self._timeout = timeout
        if client is None:
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:  # pragma: no cover - installation issue
                raise RuntimeError(
                    "google-genai is required for Gemini chat. Run `poetry install`."
                ) from exc
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=int(timeout * 1000)),
            )
        self._client = client

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            interaction = await asyncio.to_thread(
                self._client.interactions.create,
                model=self._model,
                system_instruction=system_prompt,
                input=user_prompt,
                generation_config={
                    "max_output_tokens": 1024,
                    "thinking_level": "low",
                },
            )
        except Exception as exc:
            # Do not expose SDK exception text: it can contain request details.
            logger.warning("Gemini Interactions API request failed (%s)", type(exc).__name__)
            raise ProviderUnavailable(
                "The AI provider could not complete the answer. Please try again."
            ) from exc

        answer = getattr(interaction, "output_text", None)
        if not isinstance(answer, str) or not answer.strip():
            raise ProviderUnavailable("The AI provider returned an empty answer.")
        return answer.strip()

    async def aclose(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            await asyncio.to_thread(close)
