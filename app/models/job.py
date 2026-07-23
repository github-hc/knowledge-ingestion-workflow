from enum import Enum
from datetime import datetime
from typing import Optional


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class Job:
    def __init__(
        self,
        job_id: str,
        filename: str,
        webhook_url: Optional[str] = None,
        file_hash: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
    ) -> None:
        self.job_id = job_id
        self.filename = filename
        self.webhook_url = webhook_url
        self.file_hash = file_hash
        self.file_size = file_size
        self.mime_type = mime_type
        self.status: JobStatus = JobStatus.PENDING
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()
        self.chunk_count: Optional[int] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "filename": self.filename,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z",
            "chunk_count": self.chunk_count,
            "error": self.error,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
        }
