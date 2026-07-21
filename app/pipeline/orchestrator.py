from typing import Any, List, Optional

from app.extraction.base import ExtractedContent
from app.chunking.base import Chunk
from app.repositories.vector_store import VectorDocument
from app.repositories.job_store import JobStore
from app.models.job import Job, JobStatus
from app.pipeline.stages import (
    ExtractStage,
    ChunkStage,
    EmbedStage,
    StoreStage,
)


class PipelineOrchestrator:
    def __init__(
        self,
        job_store: JobStore,
        extract_stage: ExtractStage,
        chunk_stage: ChunkStage,
        embed_stage: EmbedStage,
        store_stage: StoreStage,
        webhook_notifier: Any,
    ) -> None:
        self.job_store = job_store
        self.extract_stage = extract_stage
        self.chunk_stage = chunk_stage
        self.embed_stage = embed_stage
        self.store_stage = store_stage
        self.webhook_notifier = webhook_notifier

    def run(self, job: Job, file_path: str) -> None:
        try:
            self.job_store.update_status(job.job_id, JobStatus.PROCESSING)

            extracted: ExtractedContent = self.extract_stage.execute(file_path)
            chunks: List[Chunk] = self.chunk_stage.execute(extracted)
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
