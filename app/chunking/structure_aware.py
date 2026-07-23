import os
from typing import List, Dict, Any

from app.chunking.base import Chunker, Chunk
from app.extraction.base import ExtractedContent
from app.pipeline.logger import get_pipeline_logger

log = get_pipeline_logger("chunker")


def _token_count(text: str) -> int:
    return max(1, len(text) // 4)


def _split_oversized(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    # Estimate words per token (~0.75 words per token) to keep chunks within token limit
    step = max(1, int(max_tokens * 0.75))
    overlap = int(overlap_tokens * 0.75)
    i = 0
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

    def chunk(self, content: ExtractedContent) -> List[Chunk]:
        filename = os.path.basename(content.metadata.get("source", ""))
        log.info(f"CHUNK START: filename={filename}, elements={len(content.elements)}, total_text_chars={len(content.text)}")

        results: List[Chunk] = []

        for idx, element in enumerate(content.elements):
            text = getattr(element, "text", "") or ""
            if not text.strip():
                log.debug(f"  element[{idx}] skipped (empty text)")
                continue

            el_meta = getattr(element, "metadata", {}) or {}
            page_num = el_meta.get("page_number")
            page_numbers = [page_num] if page_num is not None else []

            base_metadata: Dict[str, Any] = {
                "filename": filename,
                "page_numbers": page_numbers,
                "section_path": "",
            }

            tokens = _token_count(text)
            log.debug(f"  element[{idx}] page={page_num} tokens≈{tokens} chars={len(text)}")

            if tokens > self.max_tokens:
                parts = _split_oversized(text, self.max_tokens, self.overlap_tokens)
                log.debug(f"    → split into {len(parts)} sub-chunks")
                for part in parts:
                    results.append(Chunk(text=part, metadata=dict(base_metadata)))
            else:
                results.append(Chunk(text=text, metadata=base_metadata))

        log.info(f"CHUNK END: produced {len(results)} chunks")
        return results
