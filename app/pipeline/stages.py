from typing import Protocol, runtime_checkable, List, Any

from app.chunking.base import Chunk
from app.repositories.vector_store import VectorDocument
from app.extraction.base import ExtractedContent


@runtime_checkable
class Stage(Protocol):
    def execute(self, payload: Any) -> Any:
        ...


class ExtractStage:
    def __init__(self, extractor) -> None:
        self.extractor = extractor

    def execute(self, file_path: str) -> ExtractedContent:
        return self.extractor.extract(file_path)


class ChunkStage:
    def __init__(self, chunker) -> None:
        self.chunker = chunker

    def execute(self, extracted: ExtractedContent) -> List[Chunk]:
        return self.chunker.chunk(extracted)


class EmbedStage:
    def execute(self, chunks: List[Chunk]) -> List[VectorDocument]:
        return [
            VectorDocument(text=chunk.text, metadata=chunk.metadata) for chunk in chunks
        ]


class StoreStage:
    def __init__(self, repository) -> None:
        self.repository = repository

    def execute(self, documents: List[VectorDocument]) -> int:
        self.repository.ensure_collection()
        self.repository.upsert_chunks(documents)
        return len(documents)


class SanitizeStage:
    def __init__(self, sanitizer) -> None:
        self.sanitizer = sanitizer

    def execute(self, text: str) -> str:
        return self.sanitizer.sanitize(text)
