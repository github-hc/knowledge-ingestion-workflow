import json
import redis
from typing import Optional
from datetime import datetime
from threading import Lock

from app.models.job import Job, JobStatus


class JobStore:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._prefix = "job:"

    def _key(self, job_id: str) -> str:
        return f"{self._prefix}{job_id}"

    def _serialize(self, job: Job) -> str:
        return json.dumps({
            "job_id": job.job_id,
            "filename": job.filename,
            "webhook_url": job.webhook_url,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "chunk_count": job.chunk_count,
            "error": job.error,
            "file_hash": job.file_hash,
            "file_size": job.file_size,
            "mime_type": job.mime_type,
        })

    def _deserialize(self, data: str) -> Job:
        payload = json.loads(data)
        job = Job(
            job_id=payload["job_id"],
            filename=payload["filename"],
            webhook_url=payload.get("webhook_url"),
            file_hash=payload.get("file_hash"),
            file_size=payload.get("file_size"),
            mime_type=payload.get("mime_type"),
        )
        job.status = JobStatus(payload["status"])
        job.created_at = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
        job.updated_at = datetime.fromisoformat(payload["updated_at"].replace("Z", "+00:00"))
        job.chunk_count = payload.get("chunk_count")
        job.error = payload.get("error")
        return job

    def create(self, job: Job) -> Job:
        self._client.set(self._key(job.job_id), self._serialize(job))
        if job.file_hash:
            self._client.set(f"hash:{job.file_hash}", job.job_id)
        return job

    def get_job_by_hash(self, file_hash: str) -> Optional[Job]:
        job_id = self._client.get(f"hash:{file_hash}")
        if not job_id:
            return None
        return self.get(job_id)

    def get(self, job_id: str) -> Optional[Job]:
        data = self._client.get(self._key(job_id))
        if not data:
            return None
        return self._deserialize(data)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        chunk_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Optional[Job]:
        job = self.get(job_id)
        if not job:
            return None
        job.status = status
        job.updated_at = datetime.utcnow()
        if chunk_count is not None:
            job.chunk_count = chunk_count
        if error is not None:
            job.error = error
        self._client.set(self._key(job_id), self._serialize(job))
        return job
