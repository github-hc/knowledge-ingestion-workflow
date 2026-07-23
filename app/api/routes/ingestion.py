from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import uuid
import os
import tempfile

from app.config import settings
from app.models.job import Job, JobStatus
from app.repositories.job_store import JobStore
from app.repositories.vector_store import WeaviateRepository
from app.api.schemas import DocumentUploadResponse, JobDetailResponse
from app.workers.tasks import process_document

router = APIRouter()


def get_job_store() -> JobStore:
    from app.main import job_store
    return job_store


def _get_weaviate() -> WeaviateRepository:
    from urllib.parse import urlparse
    from app.repositories.vector_store import WeaviateRepository
    parsed = urlparse(settings.weaviate_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8080
    return WeaviateRepository(
        url=f"http://{host}:{port}",
        class_name=settings.weaviate_class_name,
    )


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    job_store: JobStore = Depends(get_job_store),
) -> DocumentUploadResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF files are supported")

    import hashlib
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    file_size = len(content)
    mime_type = file.content_type or "application/pdf"

    # 1. Check Weaviate (processed documents)
    weaviate_repo = _get_weaviate()
    if weaviate_repo.check_file_exists(file_hash):
        raise HTTPException(
            status_code=409,
            detail="File has already been uploaded and processed."
        )

    # 2. Check Redis (in-progress or completed jobs)
    existing_job = job_store.get_job_by_hash(file_hash)
    if existing_job:
        if existing_job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
            raise HTTPException(
                status_code=409,
                detail=f"File is currently being processed (job ID: {existing_job.job_id})."
            )
        elif existing_job.status == JobStatus.DONE:
            raise HTTPException(
                status_code=409,
                detail="File has already been uploaded and processed."
            )

    job_id = str(uuid.uuid4())
    webhook_url = file.headers.get("X-Webhook-URL", settings.default_webhook_url)

    job = Job(
        job_id=job_id,
        filename=file.filename or "upload.pdf",
        webhook_url=webhook_url,
        file_hash=file_hash,
        file_size=file_size,
        mime_type=mime_type,
    )
    job_store.create(job)

    suffix = os.path.splitext(file.filename or "upload.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    process_document.apply_async(args=[job_id, tmp_path, webhook_url])

    return DocumentUploadResponse(job_id=job_id, status=JobStatus.PENDING.value)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(
    job_id: str,
    job_store: JobStore = Depends(get_job_store),
) -> JobDetailResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetailResponse(**job.to_dict())
