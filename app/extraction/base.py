from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ExtractedContent:
    text: str
    elements: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> ExtractedContent:
        """Extract structured content from a document file.

        Args:
            file_path: Absolute path to the document file.

        Returns:
            ExtractedContent containing combined text, per-element
            structured data, and document-level metadata.
        """
        ...
