from typing import Any, List, Optional

from app.extraction.base import ExtractedContent
from app.chunking.base import Chunk
from app.repositories.vector_store import VectorDocument
from app.repositories.job_store import JobStore
from app.models.job import Job, JobStatus
from app.pipeline.stages import (
    ExtractStage,
    SanitizeStage,
    ChunkStage,
    EmbedStage,
    StoreStage,
)


class PipelineOrchestrator:
    def __init__(
        self,
        job_store: JobStore,
        extract_stage: ExtractStage,
        sanitize_stage: SanitizeStage,
        chunk_stage: ChunkStage,
        embed_stage: EmbedStage,
        store_stage: StoreStage,
        webhook_notifier: Any,
    ) -> None:
        self.job_store = job_store
        self.extract_stage = extract_stage
        self.sanitize_stage = sanitize_stage
        self.chunk_stage = chunk_stage
        self.embed_stage = embed_stage
        self.store_stage = store_stage
        self.webhook_notifier = webhook_notifier

    def run(self, job: Job, file_path: str) -> None:
        try:
            self.job_store.update_status(job.job_id, JobStatus.PROCESSING)

            extracted: ExtractedContent = self.extract_stage.execute(file_path)

            # Sanitize extracted text and element text before chunking
            extracted.text = self.sanitize_stage.execute(extracted.text)
            for el in extracted.elements:
                el.text = self.sanitize_stage.execute(el.text)

            chunks: List[Chunk] = self.chunk_stage.execute(extracted)

            total_pages = extracted.metadata.get("total_pages", 0)
            for chunk in chunks:
                chunk.metadata["file_hash"] = job.file_hash
                chunk.metadata["file_size"] = job.file_size
                chunk.metadata["mime_type"] = job.mime_type
                chunk.metadata["total_pages"] = total_pages

            documents: List[VectorDocument] = self.embed_stage.execute(chunks)
            chunk_count = self.store_stage.execute(documents)

            self.job_store.update_status(
                job.job_id, JobStatus.DONE, chunk_count=chunk_count
            )
            self.webhook_notifier.notify(
                job_id=job.job_id,
                status=JobStatus.DONE.value,
                chunk_count=chunk_count,
            )
        except Exception as exc:
            self.job_store.update_status(
                job.job_id, JobStatus.FAILED, error=str(exc)
            )
            self.webhook_notifier.notify(
                job_id=job.job_id,
                status=JobStatus.FAILED.value,
                error=str(exc),
            )
