from unittest.mock import MagicMock

from app.extraction.base import DocumentExtractor, ExtractedContent
from app.extraction.pdf_extractor import PDFExtractor
from app.extraction.factory import ExtractorFactory


def test_pdf_extractor_returns_extracted_content():
    extractor = PDFExtractor()
    result = extractor.extract("tests/fixtures/sample.pdf")
    assert isinstance(result, ExtractedContent)
    assert isinstance(result.text, str)
    assert isinstance(result.elements, list)
    assert isinstance(result.metadata, dict)


def test_factory_returns_pdf_extractor():
    extractor = ExtractorFactory.get("application/pdf")
    assert isinstance(extractor, PDFExtractor)


def test_factory_returns_none_for_unknown_mime():
    assert ExtractorFactory.get("application/msword") is None
