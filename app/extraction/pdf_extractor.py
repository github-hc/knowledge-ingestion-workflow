from typing import List, Dict, Any
from unstructured.partition.pdf import partition_pdf

from app.extraction.base import DocumentExtractor, ExtractedContent


class PDFExtractor(DocumentExtractor):
    def extract(self, file_path: str) -> ExtractedContent:
        elements = partition_pdf(
            filename=file_path,
            strategy="hi_res",
            extract_images_in_pdf=False,
        )

        text_parts: List[str] = []
        for el in elements:
            if el.text:
                text_parts.append(el.text)

        return ExtractedContent(
            text="\n".join(text_parts),
            elements=elements,
            metadata={"source": file_path, "format": "pdf"},
        )
