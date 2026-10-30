# Docwise — document question answering

Docwise is a small React/FastAPI application for asking questions about one
text document at a time. It accepts pasted text and `.txt` or `.md` files.
The backend chunks the document, embeds those chunks, and keeps the vectors in
an in-memory index associated with a generated session ID. For each question,
it embeds the question, retrieves the closest chunks, and sends those excerpts
to Gemini as the answer context.

The full document is not sent to Gemini on each question.

## Requirements

- Python 3.11 or later
- Poetry
- Node.js and npm
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Run locally

Open two terminals from the project root.

### 1. Configure and start the API

```bash
cd server
poetry install
cp .env.example .env
```

Set `GEMINI_API_KEY` in `server/.env`. Do not put this key in the client
directory or commit the `.env` file.

Start the API:

```bash
poetry run python -m app.main
```

The API listens on `http://127.0.0.1:8000`. Its health endpoint is
`http://127.0.0.1:8000/api/health`; FastAPI's interactive API reference is at
`http://127.0.0.1:8000/docs`.

### 2. Start the web client

In the second terminal:

```bash
cd client
npm install
npm run dev
```

Open `http://localhost:5173`.

The Vite development server proxies `/api` requests to the local FastAPI
server. If you change the API host or port, update `client/vite.config.js` and
the server's `CORS_ORIGINS` setting accordingly.

## Configuration

The API reads settings from `server/.env`. The checked-in
`server/.env.example` is the reference list of supported settings.

| Variable | Default | Purpose |
|---|---:|---|
| `GEMINI_API_KEY` | — | Required server-side Gemini credential |
| `GEMINI_CHAT_MODEL` | `gemini-3.8-flash` | Model used to answer questions |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Model used for document and query vectors |
| `EMBEDDING_DIMENSIONS` | `768` | Embedding vector dimensions |
| `CHUNK_SIZE` | `800` | Target chunk length, in characters |
| `CHUNK_OVERLAP` | `100` | Character overlap between adjacent chunks |
| `TOP_K` | `4` | Maximum retrieved chunks passed to the model |
| `MIN_SIMILARITY` | `0.30` | Minimum cosine similarity for a chunk to be included |
| `MAX_DOCUMENT_BYTES` | `200000` | Maximum document size |
| `MAX_QUESTION_CHARS` | `1000` | Maximum question length |
| `SESSION_TTL_SECONDS` | `3600` | Session expiry after inactivity |
| `MAX_SESSIONS` | `200` | Maximum number of in-memory sessions |
| `APP_HOST` / `APP_PORT` | `127.0.0.1` / `8000` | API bind address |
| `APP_RELOAD` | `true` | Enable the development file watcher |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed browser origins |
| `PROVIDER_TIMEOUT_SECONDS` | `90` | HTTP timeout for Gemini requests |
| `PROVIDER_MAX_RETRIES` | `1` | Retries transient embedding REST failures |
| `PROVIDER_RETRY_BASE_DELAY_SECONDS` | `2` | Initial embedding retry delay; subsequent delays increase exponentially |

### Gemini model and timeout notes

The default chat model is `gemini-3.8-flash`. If an existing `.env` file
contains an older `GEMINI_CHAT_MODEL` value, that value overrides the default;
edit the `.env` file rather than only changing `config.py`.

A Gemini `ReadTimeout` means the client did not receive a response before its
configured deadline. It is not the same as a model-not-found response. The
default timeout is 90 seconds because generation can take longer than
embedding. The application makes one bounded retry for transient transport
failures. If requests still time out, check the network connection and provider
availability, then try a shorter question or a smaller document. Increasing
the timeout further can make a slow request wait longer; it does not make the
provider respond faster.

## API

All application endpoints are under `/api`.

| Method | Path | Behaviour |
|---|---|---|
| `POST` | `/documents` | Accepts a text form field or a `.txt` / `.md` upload; chunks and embeds it; returns `sessionId` and `chunkCount` |
| `POST` | `/ask` | Accepts `sessionId` and `question`; retrieves relevant chunks and returns `answer` plus source previews |
| `DELETE` | `/sessions/{session_id}` | Deletes that in-memory session |
| `GET` | `/health` | Returns API process health |

Example question request:

```json
{
  "sessionId": "the-id-returned-by-document-upload",
  "question": "What does the document say about the launch date?"
}
```

Successful responses and errors are JSON. The API returns stable error codes
for the client to interpret. The React client maps those codes to short,
user-facing messages; it does not display raw response bodies, stack traces,
or provider response text. Detailed provider diagnostics stay in the server
logs. Errors use this shape:

```json
{
  "error": {
    "code": "provider_unavailable",
    "message": "The AI provider did not respond in time. Please try again."
  }
}
```

The API uses `400` for invalid input, `404` for an unknown or expired session,
`413` for an oversized request, `429` when Gemini's rate limit remains after
retrying, `502` for an upstream provider failure, and `500` for an unexpected
application error.

## How retrieval works

1. The API accepts pasted text or reads an uploaded UTF-8 text/Markdown file.
2. The chunker prefers paragraph boundaries and splits long paragraphs. The
   default chunk size is 800 characters with 100 characters of overlap.
3. Gemini creates document embeddings in batches. The vectors and chunk text
   are stored together in a `VectorIndex` owned by the new session.
4. On a question, the API checks the session, embeds the question using the
   retrieval-query task type, and ranks that session's chunks by cosine
   similarity.
5. Up to `TOP_K` chunks at or above `MIN_SIMILARITY` are passed to Gemini.
   The system prompt says to answer only from those excerpts and treats the
   document text as untrusted input.
6. If no chunk clears the threshold, the API returns a fixed
   “not available in the provided content” response without calling the chat
   model.

The response includes short previews of the excerpts selected for the answer.
Those previews are useful for inspection; they are not a formal citation or
proof that every sentence in the answer is supported.

## Tests

Run the backend test suite from `server/`:

```bash
poetry run pytest
```

The tests use fake embedding and language-model providers, plus an
`httpx.MockTransport` for the Gemini adapter. They do not make external API
requests and do not require a Gemini key.

## Project layout

```text
client/                  React application and Vite configuration
server/app/api/           HTTP routes, input handling, and schemas
server/app/providers/     Gemini HTTP adapter and provider interfaces
server/app/services/      Chunking, retrieval, prompts, and session storage
server/tests/             API, service, and provider tests
docs/                     Implementation decisions and trade-offs
```

## Operational limits

- Session data lives in process memory. Restarting the API clears every
  session; multiple API workers do not share the same index.
- A session ID is an unguessable bearer identifier, not a user account or an
  authentication system. Anyone who obtains an ID can use that session.
- The application accepts text and Markdown only. PDF parsing, login,
  persistent storage, streaming, and deployment automation are not included.
- The configured document-size limit is approximately 200 KB. Embedding many
  chunks can still take time and may encounter provider quotas.
- Similarity search is a lightweight baseline. The threshold is configurable
  and may need tuning for documents with different writing styles or subject
  matter.

For a multi-user deployment, add authentication and authorization, move
sessions and vectors to shared storage, enforce per-user quotas, and run
document ingestion in a background job. Those changes are intentionally
outside the scope of this take-home implementation.
