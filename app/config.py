from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    redis_url: str = "redis://redis:6379/0"
    weaviate_url: str = "http://weaviate:8080"
    weaviate_grpc_port: int = 50051
    weaviate_class_name: str = "DocumentChunk"

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    default_webhook_url: str = ""
    chunk_max_tokens: int = 750
    chunk_overlap_tokens: int = 100
    pii_policy: str = "mask"
    weaviate_hybrid_alpha: float = 0.5
    weaviate_reranking: bool = True


settings = Settings()
