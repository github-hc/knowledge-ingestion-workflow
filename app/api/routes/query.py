from fastapi import APIRouter, HTTPException, Query as QueryParam
from urllib.parse import urlparse

from app.api.schemas import QueryRequest, QueryResult, QueryResponse
from app.repositories.vector_store import WeaviateRepository
from app.config import settings

router = APIRouter()


def _get_weaviate() -> WeaviateRepository:
    """Build a WeaviateRepository connected to the configured instance."""
    parsed = urlparse(settings.weaviate_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8080
    return WeaviateRepository(
        url=f"http://{host}:{port}",
        class_name=settings.weaviate_class_name,
    )


@router.post("/query", response_model=QueryResponse, summary="Semantic search over ingested documents")
def query_documents(body: QueryRequest) -> QueryResponse:
    """
    Run a semantic (vector) search against all ingested document chunks.

    - **query**: natural-language question or keyword string
    - **limit**: how many top results to return (1–50, default 5)

    Returns the most similar chunks with their source metadata and
    vector-distance score (lower = more similar).
    """
    try:
        repo = _get_weaviate()
        raw_results = repo.query(text=body.query, limit=body.limit)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Weaviate query failed: {exc}",
        )

    results = [
        QueryResult(
            text=r.get("text", ""),
            filename=r.get("filename", ""),
            page_numbers=r.get("page_numbers") or [],
            section_path=r.get("section_path", ""),
            distance=r.get("distance"),
        )
        for r in raw_results
    ]

    return QueryResponse(
        query=body.query,
        results=results,
        total=len(results),
    )
