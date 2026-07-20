from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import uuid
import os
import tempfile

from app.config import settings
from app.models.job import Job, JobStatus
from app.repositories.job_store import JobStore
from app.api.schemas import DocumentUploadResponse, JobDetailResponse
from app.workers.tasks import process_document

router = APIRouter()


def get_job_store() -> JobStore:
    from app.main import job_store
    return job_store


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    job_store: JobStore = Depends(get_job_store),
) -> DocumentUploadResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF files are supported")

    job_id = str(uuid.uuid4())
    webhook_url = file.headers.get("X-Webhook-URL", settings.default_webhook_url)

    job = Job(job_id=job_id, filename=file.filename or "upload.pdf", webhook_url=webhook_url)
    job_store.create(job)

    suffix = os.path.splitext(file.filename or "upload.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
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
