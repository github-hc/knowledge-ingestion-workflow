# Doc Ingestion MVP

Upload a PDF → extract → chunk → embed → store in Weaviate → webhook on completion.

## Architecture
<img width="1292" height="1330" alt="image" src="https://github.com/user-attachments/assets/6c413429-4caa-46a9-862b-7b0bc8882370" />

## Setup

```bash
cp .env.example .env
```

## Option A: Docker Compose (all services)

```bash
docker compose up -d
```

Then in another terminal:
```bash
docker compose exec app uvicorn app.main:app --reload
docker compose exec worker celery -A app.workers.celery_app worker --loglevel=info
```

## Option B: Local (app + worker only)

Prerequisites: Redis and Weaviate running locally.
Weaviate defaults to port 8080; if Docker Desktop is using it, Compose maps Weaviate to host port 8081.

```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — Weaviate (if not using Docker)
# Download from https://weaviate.io/developers/weaviate/installation

# Terminal 3 — API
uvicorn app.main:app --reload

# Terminal 4 — Worker
CELERY_BROKER_URL=redis://localhost:6379/0 celery -A app.workers.celery_app worker --loglevel=info
```

## Test

```bash
pytest
```

## API

- `POST /api/v1/documents` — upload PDF, returns `{ job_id, status }`
- `GET /api/v1/jobs/{id}` — get job status and chunk count
