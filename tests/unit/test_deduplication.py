from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.job import Job, JobStatus
from app.api.routes.ingestion import get_job_store

import pytest

mock_job_store = MagicMock()

@pytest.fixture(autouse=True)
def setup_overrides():
    app.dependency_overrides[get_job_store] = lambda: mock_job_store
    yield
    if get_job_store in app.dependency_overrides:
        del app.dependency_overrides[get_job_store]

client = TestClient(app)


@patch("app.api.routes.ingestion.process_document.apply_async")
@patch("app.api.routes.ingestion._get_weaviate")
def test_upload_deduplication_flow(mock_get_weaviate, mock_apply_async):
    # Setup mock Weaviate
    mock_weaviate = MagicMock()
    mock_get_weaviate.return_value = mock_weaviate

    # File mock content
    file_content = b"%PDF-1.4 sample file content"
    files = {"file": ("sample.pdf", file_content, "application/pdf")}

    # Case 1: First upload of a fresh file (not in Weaviate, not in Redis)
    mock_weaviate.check_file_exists.return_value = False
    mock_job_store.get_job_by_hash.return_value = None

    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING"
    mock_job_store.create.assert_called_once()
    mock_apply_async.assert_called_once()

    # Reset mock call counts
    mock_job_store.create.reset_mock()
    mock_apply_async.reset_mock()

    # Case 2: Upload duplicate file that is currently in progress (PENDING/PROCESSING in Redis)
    mock_weaviate.check_file_exists.return_value = False
    active_job = Job(job_id="active-123", filename="sample.pdf")
    active_job.status = JobStatus.PROCESSING
    mock_job_store.get_job_by_hash.return_value = active_job

    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 409
    assert "currently being processed" in response.json()["detail"]
    mock_job_store.create.assert_not_called()
    mock_apply_async.assert_not_called()

    # Case 3: Upload duplicate file that has already been processed (exists in Weaviate)
    mock_weaviate.check_file_exists.return_value = True
    mock_job_store.get_job_by_hash.return_value = None  # Even if Redis is empty/cleared

    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 409
    assert "already been uploaded and processed" in response.json()["detail"]
    mock_job_store.create.assert_not_called()
    mock_apply_async.assert_not_called()

    # Case 4: Upload file that previously failed (FAILED in Redis) - should allow retry
    mock_weaviate.check_file_exists.return_value = False
    failed_job = Job(job_id="failed-123", filename="sample.pdf")
    failed_job.status = JobStatus.FAILED
    mock_job_store.get_job_by_hash.return_value = failed_job

    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING"
    mock_job_store.create.assert_called_once()
    mock_apply_async.assert_called_once()

    # Reset mock call counts
    mock_job_store.create.reset_mock()
    mock_apply_async.reset_mock()

    # Case 5: Upload duplicate file that has already been processed in Redis (DONE) but not in Weaviate (e.g. 0 chunks)
    mock_weaviate.check_file_exists.return_value = False
    done_job = Job(job_id="done-123", filename="sample.pdf")
    done_job.status = JobStatus.DONE
    mock_job_store.get_job_by_hash.return_value = done_job

    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 409
    assert "already been uploaded and processed" in response.json()["detail"]
    mock_job_store.create.assert_not_called()
    mock_apply_async.assert_not_called()


def test_upsert_chunks_raises_value_error_if_file_exists():
    from app.repositories.vector_store import WeaviateRepository, VectorDocument
    import pytest

    with patch("app.repositories.vector_store.weaviate.connect_to_custom") as mock_connect:
        repo = WeaviateRepository(url="http://localhost:8080", class_name="DocumentChunk")
        repo.check_file_exists = MagicMock(return_value=True)

        chunks = [
            VectorDocument(text="hello", metadata={"file_hash": "existing-hash"})
        ]

        with pytest.raises(ValueError, match="already exists in Weaviate"):
            repo.upsert_chunks(chunks)


def test_list_documents_route():
    from app.api.routes.ingestion import _get_weaviate
    mock_weaviate = MagicMock()
    mock_weaviate.list_all_documents.return_value = [
        {
            "filename": "test.pdf",
            "file_hash": "hash123",
            "file_size": 5000,
            "mime_type": "application/pdf",
            "total_pages": 3,
            "original_file_name": "original_test.pdf",
        }
    ]
    app.dependency_overrides[_get_weaviate] = lambda: mock_weaviate

    response = client.get("/api/v1/documents")
    # Clean up override
    del app.dependency_overrides[_get_weaviate]

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "test.pdf"
    assert data[0]["file_hash"] == "hash123"
    assert data[0]["file_size"] == 5000
    assert data[0]["original_file_name"] == "original_test.pdf"


def test_query_route_hybrid_mapping():
    from app.api.routes.query import _get_weaviate
    mock_weaviate = MagicMock()
    mock_weaviate.query.return_value = [
        {
            "text": "test chunk content",
            "filename": "tmp_test.pdf",
            "page_numbers": [1],
            "section_path": "Root",
            "distance": None,
            "score": 0.875,
            "file_hash": "hash123",
            "file_size": 1000,
            "mime_type": "application/pdf",
            "total_pages": 5,
            "original_file_name": "original.pdf",
        }
    ]
    app.dependency_overrides[_get_weaviate] = lambda: mock_weaviate

    response = client.post("/api/v1/query", json={"query": "test query", "limit": 2})
    # Clean up override
    del app.dependency_overrides[_get_weaviate]

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test query"
    assert len(data["results"]) == 1
    assert data["results"][0]["text"] == "test chunk content"
    assert data["results"][0]["score"] == 0.875
    assert data["results"][0]["distance"] is None
    assert data["results"][0]["original_file_name"] == "original.pdf"

