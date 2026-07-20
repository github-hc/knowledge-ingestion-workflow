from typing import Dict, Optional

from app.extraction.base import DocumentExtractor, ExtractedContent
from app.extraction.pdf_extractor import PDFExtractor


class ExtractorFactory:
    _extractors: Dict[str, DocumentExtractor] = {
        "application/pdf": PDFExtractor(),
    }

    @classmethod
    def register(cls, mime_type: str, extractor: DocumentExtractor) -> None:
        cls._extractors[mime_type] = extractor

    @classmethod
    def get(cls, mime_type: str) -> Optional[DocumentExtractor]:
        return cls._extractors.get(mime_type)
