from unittest.mock import MagicMock

from app.models.job import Job, JobStatus
from app.repositories.job_store import JobStore


def test_job_store_create_and_get():
    mock_redis = MagicMock()
    store = JobStore.__new__(JobStore)
    store._client = mock_redis
    store._prefix = "job:"

    job = Job(job_id="123", filename="a.pdf")
    store.create(job)
    mock_redis.set.assert_called_once()

    saved = mock_redis.set.call_args[0][0]
    assert saved == "job:123"


def test_job_store_update_status():
    mock_redis = MagicMock()
    store = JobStore.__new__(JobStore)
    store._client = mock_redis
    store._prefix = "job:"

    serialized = (
        '{"job_id":"123","filename":"a.pdf","webhook_url":null,'
        '"status":"PENDING","created_at":"2024-01-01T00:00:00+00:00",'
        '"updated_at":"2024-01-01T00:00:00+00:00","chunk_count":null,"error":null}'
    )
    mock_redis.get.return_value = serialized

    updated = store.update_status("123", JobStatus.DONE, chunk_count=5)
    assert updated is not None
    assert updated.status == JobStatus.DONE
    assert updated.chunk_count == 5
