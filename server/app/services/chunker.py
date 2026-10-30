"""Paragraph-aware text chunking with overlap.

Strategy (see docs/DECISIONS.md):
  1. Split on blank lines so we never cut through a paragraph if we can help it.
  2. Paragraphs longer than `chunk_size` are split on sentence boundaries, and
     sentences longer than `chunk_size` are split on word boundaries.
  3. Units are packed greedily into chunks up to `chunk_size` characters.
  4. Each new chunk starts with the tail (~`overlap` chars) of the previous one
     so an answer straddling a boundary is still retrievable.

`chunk_size` is a target: a chunk can exceed it by at most `overlap` characters
because of the carried-over tail.
"""

import re

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(normalized) if p.strip()]

    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            units.append(paragraph)
        else:
            units.extend(_split_long_paragraph(paragraph, chunk_size))

    return _pack(units, chunk_size, overlap)


def _split_long_paragraph(paragraph: str, limit: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_SPLIT.split(paragraph):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_by_words(sentence, limit))
        elif current and len(current) + 1 + len(sentence) > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def _split_by_words(text: str, limit: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for word in text.split():
        # A single token longer than the limit (e.g. a huge URL) is hard-cut.
        while len(word) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:limit])
            word = word[limit:]
        if current and len(current) + 1 + len(word) > limit:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return pieces


def _overlap_tail(text: str, overlap: int) -> str:
    """Last ~`overlap` characters of `text`, starting on a word boundary."""
    if overlap <= 0 or len(text) <= overlap:
        return text if overlap > 0 else ""
    tail = text[-overlap:]
    first_space = tail.find(" ")
    if first_space != -1:
        tail = tail[first_space + 1 :]
    return tail.strip()


def _pack(units: list[str], chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for unit in units:
        if current and len(current) + 2 + len(unit) > chunk_size:
            chunks.append(current)
            tail = _overlap_tail(current, overlap)
            current = f"{tail}\n\n{unit}" if tail else unit
        else:
            current = f"{current}\n\n{unit}" if current else unit
    if current:
        chunks.append(current)
    return chunks
