from urllib.parse import urlparse

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery
from typing import List, Dict, Any, Optional

from app.repositories.vector_store import VectorStoreRepository, VectorDocument
from app.config import settings


class WeaviateRepository(VectorStoreRepository):
    def __init__(self, url: str, class_name: str) -> None:
        self.url = url
        self.class_name = class_name
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080
        self._client = weaviate.connect_to_custom(
            http_host=host,
            http_port=port,
            http_secure=False,
            grpc_host=host,
            grpc_port=50051,
            grpc_secure=False,
        )

    def ensure_collection(self) -> None:
        if self._client.collections.exists(self.class_name):
            return
        self._client.collections.create(
            name=self.class_name,
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="filename", data_type=DataType.TEXT),
                Property(name="page_numbers", data_type=DataType.INT_ARRAY),
                Property(name="section_path", data_type=DataType.TEXT),
            ],
        )

    def delete_collection(self) -> None:
        if self._client.collections.exists(self.class_name):
            self._client.collections.delete(self.class_name)

    def upsert_chunks(self, chunks: List[VectorDocument]) -> None:
        collection = self._client.collections.get(self.class_name)
        with collection.batch.dynamic() as batch:
            for chunk in chunks:
                batch.add_object(
                    properties={
                        "text": chunk.text,
                        "filename": chunk.metadata.get("filename", ""),
                        "page_numbers": chunk.metadata.get("page_numbers", []),
                        "section_path": chunk.metadata.get("section_path", ""),
                    }
                )

    def query(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
        collection = self._client.collections.get(self.class_name)
        response = collection.query.near_text(
            query=text,
            limit=limit,
            return_metadata=MetadataQuery(distance=True),
        )
        results: List[Dict[str, Any]] = []
        for obj in response.objects:
            results.append({
                "text": obj.properties.get("text", ""),
                "filename": obj.properties.get("filename", ""),
                "page_numbers": obj.properties.get("page_numbers", []),
                "section_path": obj.properties.get("section_path", ""),
                "distance": obj.metadata.distance if obj.metadata else None,
            })
        return results
