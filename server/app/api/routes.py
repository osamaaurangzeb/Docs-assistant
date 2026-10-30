"""HTTP layer: thin handlers that validate input and delegate to `RagService`."""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.api.document_input import extract_text
from app.api.schemas import AskRequest, AskResponse, DocumentCreated, SourceOut
from app.config import Settings
from app.errors import SessionNotFound, ValidationFailed
from app.services.rag import RagService

router = APIRouter(prefix="/api")

PREVIEW_CHARS = 200


def get_rag(request: Request) -> RagService:
    return request.app.state.rag


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/documents", response_model=DocumentCreated, status_code=201)
async def create_document(
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    rag: RagService = Depends(get_rag),
    settings: Settings = Depends(get_app_settings),
) -> DocumentCreated:
    content = await extract_text(text, file, settings.max_document_bytes)
    result = await rag.ingest(content)
    return DocumentCreated(sessionId=result.session_id, chunkCount=result.chunk_count)


@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    rag: RagService = Depends(get_rag),
    settings: Settings = Depends(get_app_settings),
) -> AskResponse:
    if len(body.question) > settings.max_question_chars:
        raise ValidationFailed(f"Question is too long (max {settings.max_question_chars} characters).")
    result = await rag.ask(body.session_id, body.question)
    return AskResponse(
        answer=result.answer,
        sources=[
            SourceOut(chunkIndex=s.chunk_index, score=round(s.score, 4), preview=s.text[:PREVIEW_CHARS])
            for s in result.sources
        ],
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, rag: RagService = Depends(get_rag)) -> None:
    if not rag.delete_session(session_id):
        raise SessionNotFound("Session not found or already expired.")
