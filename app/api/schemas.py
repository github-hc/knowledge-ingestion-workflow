from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    job_id: str
    status: str


class JobDetailResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    created_at: str
    updated_at: str
    chunk_count: Optional[int] = None
    error: Optional[str] = None


class WebhookPayload(BaseModel):
    job_id: str
    status: str
    error: Optional[str] = None
    chunk_count: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
