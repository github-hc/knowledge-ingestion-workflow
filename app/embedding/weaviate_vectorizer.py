from typing import Dict, Any


WEAVIATE_CLASS_SCHEMA: Dict[str, Any] = {
    "class": "DocumentChunk",
    "vectorizer": "text2vec-transformers",
    "properties": [
        {"name": "text", "dataType": ["text"]},
        {"name": "filename", "dataType": ["text"]},
        {"name": "page_numbers", "dataType": ["int[]"]},
        {"name": "section_path", "dataType": ["text"]},
    ],
}
