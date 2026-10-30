import pytest

from app.services.chunker import split_text


def test_short_text_is_a_single_chunk():
    assert split_text("Hello world.", 800, 100) == ["Hello world."]


def test_empty_or_whitespace_text_yields_no_chunks():
    assert split_text("   \n\n  ", 800, 100) == []


def test_paragraphs_are_kept_whole_when_they_fit():
    text = "Para one is here.\n\nPara two is here.\n\nPara three is here."
    chunks = split_text(text, chunk_size=20, overlap=0)
    assert chunks == ["Para one is here.", "Para two is here.", "Para three is here."]


def test_small_paragraphs_are_packed_together_up_to_chunk_size():
    text = "Para one is here.\n\nPara two is here.\n\nPara three is here."
    assert split_text(text, chunk_size=40, overlap=0) == [
        "Para one is here.\n\nPara two is here.",
        "Para three is here.",
    ]


def test_chunks_respect_size_plus_overlap_bound():
    text = " ".join(f"Sentence number {i} talks about something." for i in range(200))
    chunks = split_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 300 + 50 for c in chunks)


def test_consecutive_chunks_overlap():
    paragraphs = [f"Paragraph {i} " + "word " * 30 for i in range(6)]
    chunks = split_text("\n\n".join(paragraphs), chunk_size=250, overlap=60)
    assert len(chunks) > 1
    for prev, nxt in zip(chunks, chunks[1:]):
        shared_words = set(prev.split()[-8:]) & set(nxt.split()[:12])
        assert shared_words, "next chunk should start with the tail of the previous one"


def test_no_content_is_lost():
    text = "\n\n".join(f"Unique marker {i} " + "filler " * 20 for i in range(15))
    joined = "\n".join(split_text(text, chunk_size=200, overlap=30))
    assert all(f"Unique marker {i} " in joined for i in range(15))


def test_a_single_huge_token_is_hard_cut():
    chunks = split_text("x" * 1000, chunk_size=300, overlap=0)
    assert all(len(c) <= 300 for c in chunks)
    assert "".join(chunks) == "x" * 1000


def test_crlf_is_normalised():
    assert split_text("a\r\n\r\nb", 100, 0) == ["a\n\nb"]


@pytest.mark.parametrize("size,overlap", [(0, 0), (100, 100), (100, -1)])
def test_invalid_parameters_raise(size, overlap):
    with pytest.raises(ValueError):
        split_text("text", size, overlap)
