from typing import List, Dict, Any

from unstructured.documents.elements import Element
from unstructured.chunking.title import chunk_by_title

from app.chunking.base import Chunker, Chunk
from app.extraction.base import ExtractedContent
from app.config import settings


def _token_count(text: str) -> int:
    return max(1, len(text) // 4)


def _split_oversized(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    i = 0
    step = max_tokens * 4
    overlap = overlap_tokens * 4
    while i < len(words):
        end = min(i + step, len(words))
        chunks.append(" ".join(words[i:end]))
        if end >= len(words):
            break
        i = max(i + 1, end - overlap)
    return chunks


class StructureAwareChunker(Chunker):
    def __init__(
        self,
        max_tokens: int = 750,
        overlap_tokens: int = 100,
        multipage_sections: bool = True,
    ) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.multipage_sections = multipage_sections

    def chunk(self, content: ExtractedContent) -> List[Chunk]:
        elements: List[Element] = list(content.elements)

        chunks = chunk_by_title(
            elements,
            multipage_sections=self.multipage_sections,
        )

        results: List[Chunk] = []
        for c in chunks:
            text = c.text or ""
            if not text.strip():
                continue

            metadata: Dict[str, Any] = {"filename": content.metadata.get("source", "")}
            page_numbers: List[int] = []
            section_path_parts: List[str] = []

            if hasattr(c, "metadata") and c.metadata:
                if hasattr(c.metadata, "page_number") and c.metadata.page_number is not None:
                    page_numbers.append(c.metadata.page_number)
                if hasattr(c.metadata, "filename") and c.metadata.filename:
                    metadata["filename"] = c.metadata.filename

            page_numbers = sorted(set(page_numbers))

            for el in elements:
                if el.text and el.text in text:
                    if hasattr(el, "metadata") and el.metadata:
                        if hasattr(el.metadata, "page_number") and el.metadata.page_number is not None:
                            if el.metadata.page_number not in page_numbers:
                                page_numbers.append(el.metadata.page_number)
                        if hasattr(el, "category") and el.category in {"Title", "Header"}:
                            if el.text.strip() not in section_path_parts:
                                section_path_parts.append(el.text.strip())

            metadata["page_numbers"] = page_numbers
            metadata["section_path"] = " > ".join(section_path_parts) if section_path_parts else ""

            if _token_count(text) > self.max_tokens:
                for part in _split_oversized(text, self.max_tokens, self.overlap_tokens):
                    results.append(Chunk(text=part, metadata=dict(metadata)))
            else:
                results.append(Chunk(text=text, metadata=metadata))

        return results
