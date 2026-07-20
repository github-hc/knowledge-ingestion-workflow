from pathlib import Path

try:
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    Path("tests/fixtures/sample.pdf").write_bytes(b"")
    with open("tests/fixtures/sample.pdf", "wb") as f:
        writer.write(f)
except Exception:
    Path("tests/fixtures/sample.pdf").write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Size 0 /Root 1 0 R >>\nstartxref\n0\n%%EOF"
    )
