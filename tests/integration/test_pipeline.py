import os
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_sample_pdf(path: str) -> None:
    try:
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with open(path, "wb") as f:
            writer.write(f)
    except Exception:
        Path(path).write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Size 0 /Root 1 0 R >>\nstartxref\n0\n%%EOF")


from app.api.routes.ingestion import get_job_store


@patch("app.repositories.vector_store.WeaviateRepository.check_file_exists")
def test_upload_and_job_status(mock_check_file_exists):
    mock_check_file_exists.return_value = False
    
    mock_job_store = MagicMock()
    mock_job_store.get_job_by_hash.return_value = None
    app.dependency_overrides[get_job_store] = lambda: mock_job_store

    pdf_path = "/tmp/test_sample.pdf"
    _create_sample_pdf(pdf_path)

    with patch("app.api.routes.ingestion.process_document.apply_async") as mock_task:
        mock_task.return_value = MagicMock()
        with open(pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "PENDING"
    
    # Clean up overrides
    if get_job_store in app.dependency_overrides:
        del app.dependency_overrides[get_job_store]
