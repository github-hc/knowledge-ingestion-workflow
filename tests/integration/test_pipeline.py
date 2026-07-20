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


def test_upload_and_job_status():
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
