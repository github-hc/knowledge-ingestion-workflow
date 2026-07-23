from datetime import datetime
from typing import Optional, List, Dict
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
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None


class WebhookPayload(BaseModel):
    job_id: str
    status: str
    error: Optional[str] = None
    chunk_count: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language search query")
    limit: int = Field(default=5, ge=1, le=50, description="Max number of results")


class QueryResult(BaseModel):
    text: str
    filename: str
    page_numbers: List[int]
    section_path: str
    distance: Optional[float] = None
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    total_pages: Optional[int] = None
    original_file_name: Optional[str] = None


class QueryResponse(BaseModel):
    query: str
    results: List[QueryResult]
    total: int


class DocumentMetadataResponse(BaseModel):
    filename: str
    file_hash: str
    file_size: int
    mime_type: str
    total_pages: int
    original_file_name: str
