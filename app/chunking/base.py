from typing import List, Dict, Any
from dataclasses import dataclass

from app.extraction.base import ExtractedContent


@dataclass
class Chunk:
    text: str
    metadata: Dict[str, Any]


class Chunker:
    def chunk(self, content: ExtractedContent) -> List[Chunk]:
        raise NotImplementedError
