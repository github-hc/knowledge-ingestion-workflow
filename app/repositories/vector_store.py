from urllib.parse import urlparse

import httpx
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from app.config import settings
from app.pipeline.logger import get_pipeline_logger

log = get_pipeline_logger("vector_store")


@dataclass
class VectorDocument:
    text: str
    metadata: Dict[str, Any]


class VectorStoreRepository:
    def upsert_chunks(self, chunks: List[VectorDocument]) -> None:
        raise NotImplementedError

    def query(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def ensure_collection(self) -> None:
        raise NotImplementedError

    def delete_collection(self) -> None:
        raise NotImplementedError

    def check_file_exists(self, file_hash: str) -> bool:
        raise NotImplementedError


class WeaviateRepository(VectorStoreRepository):
    def __init__(self, url: str, class_name: str) -> None:
        self.url = url
        self.class_name = class_name
        parsed = urlparse(url)
        self._host = parsed.hostname or "localhost"
        self._port = parsed.port or 8080
        grpc_port = settings.weaviate_grpc_port
        log.info(f"WeaviateRepository init: http={self._host}:{self._port} grpc={self._host}:{grpc_port}")
        self._client = weaviate.connect_to_custom(
            http_host=self._host,
            http_port=self._port,
            http_secure=False,
            grpc_host=self._host,
            grpc_port=grpc_port,
            grpc_secure=False,
            skip_init_checks=True,
        )

    def ensure_collection(self) -> None:
        exists = self._client.collections.exists(self.class_name)
        log.info(f"ensure_collection: class={self.class_name} exists={exists}")
        if exists:
            try:
                collection = self._client.collections.get(self.class_name)
                config = collection.config.get()
                prop_names = [p.name for p in config.properties]
                if "file_hash" in prop_names:
                    return
                log.info(f"Collection {self.class_name} is outdated (missing 'file_hash'). Recreating...")
                self._client.collections.delete(self.class_name)
            except Exception as e:
                log.warning(f"Failed to check collection properties: {e}. Recreating to be safe...")
                try:
                    self._client.collections.delete(self.class_name)
                except Exception:
                    pass

        log.info(f"Creating collection: {self.class_name}")
        self._client.collections.create(
            name=self.class_name,
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="filename", data_type=DataType.TEXT),
                Property(name="page_numbers", data_type=DataType.INT_ARRAY),
                Property(name="section_path", data_type=DataType.TEXT),
                Property(name="file_hash", data_type=DataType.TEXT),
                Property(name="file_size", data_type=DataType.INT),
                Property(name="mime_type", data_type=DataType.TEXT),
                Property(name="total_pages", data_type=DataType.INT),
            ],
        )

    def delete_collection(self) -> None:
        if self._client.collections.exists(self.class_name):
            self._client.collections.delete(self.class_name)

    def check_file_exists(self, file_hash: str) -> bool:
        graphql_query = """
        {{
          Get {{
            {class_name}(
              where: {{
                path: ["file_hash"]
                operator: Equal
                valueString: "{file_hash}"
              }}
              limit: 1
            ) {{
              filename
            }}
          }}
        }}
        """.format(
            class_name=self.class_name,
            file_hash=file_hash,
        )

        base_url = f"http://{self._host}:{self._port}"
        try:
            response = httpx.post(
                f"{base_url}/v1/graphql",
                json={"query": graphql_query},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                log.error(f"GraphQL check errors: {data['errors']}")
                return False
            objects = data.get("data", {}).get("Get", {}).get(self.class_name, [])
            return len(objects) > 0
        except Exception as e:
            log.error(f"Error checking file existence in Weaviate: {e}")
            return False

    def upsert_chunks(self, chunks: List[VectorDocument]) -> None:
        log.info(f"UPSERT START: {len(chunks)} documents to store")
        if not chunks:
            log.warning("upsert_chunks called with 0 documents — nothing stored!")
            return

        file_hash = chunks[0].metadata.get("file_hash")
        if file_hash and self.check_file_exists(file_hash):
            raise ValueError(f"File with hash {file_hash} already exists in Weaviate.")

        base_url = f"http://{self._host}:{self._port}"
        failed = 0

        for i, chunk in enumerate(chunks):
            props = {
                "text": chunk.text,
                "filename": chunk.metadata.get("filename", ""),
                "page_numbers": chunk.metadata.get("page_numbers", []),
                "section_path": chunk.metadata.get("section_path", ""),
                "file_hash": chunk.metadata.get("file_hash", ""),
                "file_size": chunk.metadata.get("file_size", 0),
                "mime_type": chunk.metadata.get("mime_type", ""),
                "total_pages": chunk.metadata.get("total_pages", 0),
            }
            log.debug(f"  posting object[{i}]: filename={props['filename']} text_chars={len(props['text'])}")
            try:
                response = httpx.post(
                    f"{base_url}/v1/objects",
                    json={"class": self.class_name, "properties": props},
                    timeout=30.0,
                )
                response.raise_for_status()
                log.debug(f"  object[{i}] inserted OK: {response.status_code}")
            except Exception as e:
                log.error(f"  object[{i}] insert FAILED: {e}")
                failed += 1

        log.info(f"UPSERT END: {len(chunks)} submitted, {failed} failed, {len(chunks) - failed} stored")
        if failed > 0:
            raise RuntimeError(f"Failed to insert {failed} chunks into Weaviate.")

    def query(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
        log.info(f"QUERY: '{text}' limit={limit}")
        graphql_query = """
        {{
          Get {{
            {class_name}(
              nearText: {{ concepts: {concepts} }}
              limit: {limit}
            ) {{
              text
              filename
              page_numbers
              section_path
              file_hash
              file_size
              mime_type
              total_pages
              _additional {{ distance }}
            }}
          }}
        }}
        """.format(
            class_name=self.class_name,
            concepts=str([text]).replace("'", '"'),
            limit=limit,
        )

        base_url = f"http://{self._host}:{self._port}"
        response = httpx.post(
            f"{base_url}/v1/graphql",
            json={"query": graphql_query},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            log.error(f"GraphQL errors: {data['errors']}")
            raise RuntimeError(f"GraphQL error: {data['errors']}")

        objects = data.get("data", {}).get("Get", {}).get(self.class_name, [])
        log.info(f"QUERY RESULT: {len(objects)} objects returned")

        results: List[Dict[str, Any]] = []
        for obj in objects:
            results.append({
                "text": obj.get("text", ""),
                "filename": obj.get("filename", ""),
                "page_numbers": obj.get("page_numbers", []),
                "section_path": obj.get("section_path", ""),
                "distance": obj.get("_additional", {}).get("distance"),
                "file_hash": obj.get("file_hash", ""),
                "file_size": obj.get("file_size", 0),
                "mime_type": obj.get("mime_type", ""),
                "total_pages": obj.get("total_pages", 0),
            })
        return results
