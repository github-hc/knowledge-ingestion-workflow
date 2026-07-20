import httpx
import logging
from typing import Optional

from app.api.schemas import WebhookPayload

logger = logging.getLogger(__name__)


class WebhookNotifier:
    def __init__(self, default_url: Optional[str] = None) -> None:
        self.default_url = default_url

    def notify(
        self,
        job_id: str,
        status: str,
        error: Optional[str] = None,
        chunk_count: Optional[int] = None,
        webhook_url: Optional[str] = None,
    ) -> None:
        url = webhook_url or self.default_url
        if not url:
            logger.info("No webhook URL configured for job %s", job_id)
            return

        payload = WebhookPayload(
            job_id=job_id,
            status=status,
            error=error,
            chunk_count=chunk_count,
        )

        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(url, json=payload.model_dump())
        except Exception as exc:
            logger.error("Webhook delivery failed for job %s: %s", job_id, exc)
