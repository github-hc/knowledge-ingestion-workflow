from celery import Celery
from app.config import settings

celery_app = Celery(
    "doc-ingestion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_track_started = True
# gRPC uses C threads internally which are incompatible with Celery's default
# prefork pool (which uses fork()). Using 'solo' pool avoids the fork entirely
# and prevents SIGSEGV crashes when gRPC is initialized in the worker.
celery_app.conf.worker_pool = "solo"
celery_app.conf.broker_connection_retry_on_startup = True
