"""Request/response models. Field names are camelCase on the wire (sessionId, ...)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentCreated(BaseModel):
    sessionId: str
    chunkCount: int


class AskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", min_length=1, max_length=128)
    question: str

    @field_validator("question")
    @classmethod
    def _strip_and_require(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be empty")
        return value


class SourceOut(BaseModel):
    chunkIndex: int
    score: float
    preview: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
