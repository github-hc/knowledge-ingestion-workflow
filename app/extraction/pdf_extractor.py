from typing import List, Any
from dataclasses import dataclass

import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract_text

from app.extraction.base import DocumentExtractor, ExtractedContent
from app.pipeline.logger import get_pipeline_logger

log = get_pipeline_logger("extractor")


@dataclass
class PageElement:
    """Lightweight stand-in for unstructured elements, preserving the interface."""
    text: str
    metadata: dict


class PDFExtractor(DocumentExtractor):
    def extract(self, file_path: str) -> ExtractedContent:
        log.info("=" * 60)
        log.info(f"EXTRACT START: {file_path}")

        total_pages = 0
        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
        except Exception:
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                total_pages = len(reader.pages)
            except Exception:
                total_pages = 0

        elements: List[PageElement] = []

        # Try pdfplumber first
        try:
            elements = self._extract_with_pdfplumber(file_path)
            log.info(f"pdfplumber produced {len(elements)} page elements")
            for el in elements:
                log.info(f"  page {el.metadata.get('page_number')}: {len(el.text)} chars | preview: {repr(el.text[:80])}")
        except Exception as e:
            log.warning(f"pdfplumber FAILED entirely: {e}")

        # Fall back to pdfminer if pdfplumber produced nothing
        if not elements:
            log.info("pdfplumber returned 0 elements — falling back to pdfminer")
            elements = self._extract_with_pdfminer(file_path)
            log.info(f"pdfminer produced {len(elements)} elements")
            for el in elements:
                log.info(f"  chars={len(el.text)} | preview: {repr(el.text[:80])}")

        total_chars = sum(len(el.text) for el in elements)
        log.info(f"EXTRACT END: {len(elements)} elements, {total_chars} total chars")

        return ExtractedContent(
            text="\n".join(el.text for el in elements),
            elements=elements,
            metadata={"source": file_path, "format": "pdf", "total_pages": total_pages},
        )

    def _extract_with_pdfplumber(self, file_path: str) -> List[PageElement]:
        elements: List[PageElement] = []
        with pdfplumber.open(file_path) as pdf:
            log.info(f"pdfplumber: {len(pdf.pages)} pages in PDF")
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                    log.debug(f"  plumber page {page_num}: {len(text)} chars")
                except Exception as e:
                    log.warning(f"  plumber page {page_num} FAILED: {e}")
                    text = ""
                if text.strip():
                    elements.append(
                        PageElement(
                            text=text.strip(),
                            metadata={"page_number": page_num},
                        )
                    )
        return elements

    def _extract_with_pdfminer(self, file_path: str) -> List[PageElement]:
        try:
            full_text = pdfminer_extract_text(file_path) or ""
            log.info(f"pdfminer: extracted {len(full_text)} chars total")
            log.info(f"pdfminer preview: {repr(full_text[:200])}")
        except Exception as e:
            log.error(f"pdfminer FAILED: {e}")
            full_text = ""

        if not full_text.strip():
            log.warning("pdfminer returned empty text!")
            return []

        return [PageElement(text=full_text.strip(), metadata={"page_number": 1})]
