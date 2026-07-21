import uuid
import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException

from app.config import settings
from app.models.job import Job, JobStatus
from app.repositories.job_store import JobStore
from app.api.schemas import DocumentUploadResponse, JobDetailResponse
from app.api.routes import ingestion, query

app = FastAPI(title="Doc Ingestion MVP")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")

job_store = JobStore(redis_url=settings.redis_url)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
