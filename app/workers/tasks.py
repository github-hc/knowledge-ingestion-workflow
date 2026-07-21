import os
import tempfile
from typing import Any, Optional

from app.workers.celery_app import celery_app
from app.models.job import Job
from app.extraction.factory import ExtractorFactory
from app.chunking.structure_aware import StructureAwareChunker
from app.repositories.vector_store import WeaviateRepository
from app.repositories.job_store import JobStore
from app.pipeline.stages import ExtractStage, ChunkStage, EmbedStage, StoreStage
from app.pipeline.orchestrator import PipelineOrchestrator
from app.notifications.webhook import WebhookNotifier
from app.config import settings


def _build_orchestrator() -> PipelineOrchestrator:
    weaviate = WeaviateRepository(
        url=settings.weaviate_url,
        class_name=settings.weaviate_class_name,
    )
    job_store = JobStore(redis_url=settings.redis_url)
    webhook_notifier = WebhookNotifier(default_url=settings.default_webhook_url)

    return PipelineOrchestrator(
        job_store=job_store,
        extract_stage=ExtractStage(ExtractorFactory.get("application/pdf")),
        chunk_stage=ChunkStage(
            StructureAwareChunker(
                max_tokens=settings.chunk_max_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
            )
        ),
        embed_stage=EmbedStage(),
        store_stage=StoreStage(weaviate),
        webhook_notifier=webhook_notifier,
    )


_orchestrator: Optional[PipelineOrchestrator] = None


def _get_orchestrator() -> PipelineOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = _build_orchestrator()
    return _orchestrator


@celery_app.task(bind=True, name="process_document")
def process_document(self, job_id: str, file_path: str, webhook_url: str = "") -> dict:
    orchestrator = _get_orchestrator()
    job = orchestrator.job_store.get(job_id)
    if not job:
        return {"status": "FAILED", "error": f"Job {job_id} not found"}

    orchestrator.run(job, file_path)

    try:
        os.remove(file_path)
    except OSError:
        pass

    # Re-fetch from store to get the status updated by the orchestrator.
    updated_job = orchestrator.job_store.get(job_id)
    final_status = updated_job.status.value if updated_job else "UNKNOWN"
    return {"job_id": job_id, "status": final_status}
