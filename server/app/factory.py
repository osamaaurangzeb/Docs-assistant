"""FastAPI application factory.

`create_app` accepts an optional pre-built `RagService` so tests can inject fake
providers and never need an API key.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import Settings, get_settings
from app.container import build_rag_service
from app.errors import AppError
from app.services.rag import RagService

logger = logging.getLogger(__name__)

# multipart framing + form field overhead allowed on top of the document limit
_BODY_OVERHEAD_BYTES = 64 * 1024


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(settings: Settings | None = None, rag: RagService | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resources = None
        if rag is None:
            app.state.rag, resources = build_rag_service(settings)  # fails fast without a key
        yield
        if resources is not None:
            http, chat = resources
            await chat.aclose()
            await http.aclose()

    app = FastAPI(title="Document Assistant API", lifespan=lifespan)
    app.state.settings = settings
    if rag is not None:
        app.state.rag = rag

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def reject_oversized_body(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_document_bytes + _BODY_OVERHEAD_BYTES:
            return _error(413, "payload_too_large", "Request body is too large.")
        return await call_next(request)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        detail = first.get("msg", "Invalid request.")
        return _error(400, "invalid_request", f"{field}: {detail}" if field else detail)

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return _error(500, "internal_error", "Something went wrong on the server.")

    app.include_router(router)
    return app
