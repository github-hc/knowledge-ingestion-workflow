from unittest.mock import MagicMock

from app.chunking.structure_aware import StructureAwareChunker, _token_count, _split_oversized
from app.extraction.base import ExtractedContent


def test_token_count():
    assert _token_count("hello world") == 3
    assert _token_count("") == 1


def test_split_oversized():
    text = " ".join(["word"] * 1000)
    parts = _split_oversized(text, max_tokens=100, overlap_tokens=10)
    assert len(parts) > 1
    for part in parts:
        assert _token_count(part) <= 100


def test_structure_aware_chunker_returns_chunks():
    mock_el1 = MagicMock()
    mock_el1.text = "Title 1"
    mock_el1.category = "Title"
    mock_el1.metadata = MagicMock(page_number=1, filename="test.pdf")

    mock_el2 = MagicMock()
    mock_el2.text = "Some body text here."
    mock_el2.category = "NarrativeText"
    mock_el2.metadata = MagicMock(page_number=1, filename="test.pdf")

    chunker = StructureAwareChunker(max_tokens=100, overlap_tokens=10)
    content = ExtractedContent(
        text="Title 1\nSome body text here.",
        elements=[mock_el1, mock_el2],
        metadata={"source": "test.pdf", "format": "pdf"},
    )
    chunks = chunker.chunk(content)
    assert isinstance(chunks, list)
    assert all(hasattr(c, "text") for c in chunks)
    assert all(hasattr(c, "metadata") for c in chunks)
