from unittest.mock import patch, MagicMock
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.stages import ExtractStage, SanitizeStage, ChunkStage, EmbedStage, StoreStage
from app.pipeline.sanitizer import PIISanitizer
from app.extraction.base import ExtractedContent
from app.extraction.pdf_extractor import PageElement
from app.chunking.base import Chunk
from app.models.job import Job


def test_orchestrator_pii_sanitization_flow():
    # Setup mock dependencies
    mock_job_store = MagicMock()
    mock_weaviate = MagicMock()
    mock_webhook = MagicMock()

    # Extract stage mock that returns PII
    mock_extract = MagicMock()
    mock_extract.extract.return_value = ExtractedContent(
        text="Contact email test@example.com, PAN is ABCDE1234F.",
        elements=[
            PageElement(text="Contact email test@example.com", metadata={"page_number": 1}),
            PageElement(text="PAN is ABCDE1234F.", metadata={"page_number": 1})
        ],
        metadata={"total_pages": 1}
    )

    # Stages
    extract_stage = ExtractStage(mock_extract)
    
    # Sanitizer configured to mask PII
    sanitizer = PIISanitizer(policy="mask")
    sanitize_stage = SanitizeStage(sanitizer)
    
    # Real chunker and embedding stages to see propagation
    from app.chunking.structure_aware import StructureAwareChunker
    chunk_stage = ChunkStage(StructureAwareChunker(max_tokens=500, overlap_tokens=50))
    embed_stage = EmbedStage()
    
    # Store stage mock
    store_stage = StoreStage(mock_weaviate)

    orchestrator = PipelineOrchestrator(
        job_store=mock_job_store,
        extract_stage=extract_stage,
        sanitize_stage=sanitize_stage,
        chunk_stage=chunk_stage,
        embed_stage=embed_stage,
        store_stage=store_stage,
        webhook_notifier=mock_webhook
    )

    job = Job(
        job_id="test-job-uuid",
        filename="test.pdf",
        file_hash="test-hash",
        file_size=1024,
        mime_type="application/pdf"
    )

    orchestrator.run(job, "/path/to/test.pdf")

    # Verify upsert_chunks was called with masked text
    mock_weaviate.upsert_chunks.assert_called_once()
    saved_chunks = mock_weaviate.upsert_chunks.call_args[0][0]
    
    # We should have two chunks corresponding to elements, both sanitized!
    assert len(saved_chunks) == 2
    assert saved_chunks[0].text == "Contact email [EMAIL]"
    assert saved_chunks[1].text == "PAN is [PAN]."
    assert saved_chunks[0].metadata["original_file_name"] == "test.pdf"
    assert saved_chunks[1].metadata["original_file_name"] == "test.pdf"
    
    # Verify job store and webhooks
    from app.models.job import JobStatus
    mock_job_store.update_status.assert_any_call(
        "test-job-uuid", JobStatus.DONE, chunk_count=2
    )
    mock_webhook.notify.assert_any_call(
        job_id="test-job-uuid",
        status="DONE",
        chunk_count=2
    )
