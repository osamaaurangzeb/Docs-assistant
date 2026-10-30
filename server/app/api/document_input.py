"""Extract and validate document text from a pasted-text field or an uploaded file."""

from pathlib import PurePath

from fastapi import UploadFile

from app.errors import PayloadTooLarge, ValidationFailed

ALLOWED_EXTENSIONS = {".txt", ".md"}


async def extract_text(text: str | None, file: UploadFile | None, max_bytes: int) -> str:
    has_text = text is not None and text.strip() != ""
    has_file = file is not None and bool(file.filename)

    if has_text and has_file:
        raise ValidationFailed("Provide either pasted text or a file, not both.")
    if not has_text and not has_file:
        raise ValidationFailed("Document is empty. Paste some text or upload a .txt/.md file.")

    if has_file:
        content = await _read_file(file, max_bytes)
    else:
        content = text
        if len(content.encode("utf-8")) > max_bytes:
            raise _too_large(max_bytes)

    content = content.strip()
    if not content:
        raise ValidationFailed("Document is empty.")
    return content


async def _read_file(file: UploadFile, max_bytes: int) -> str:
    suffix = PurePath(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValidationFailed("Unsupported file type. Only .txt and .md files are accepted.")

    raw = await file.read(max_bytes + 1)  # never buffer more than the limit + 1 byte
    if len(raw) > max_bytes:
        raise _too_large(max_bytes)
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationFailed("File is not valid UTF-8 text.") from exc


def _too_large(max_bytes: int) -> PayloadTooLarge:
    return PayloadTooLarge(f"Document is too large. The limit is {max_bytes // 1000} KB of text.")
