# Doc Ingestion MVP

Upload a PDF → extract → chunk → embed → store in Weaviate → webhook on completion.
## Architecture
<img width="1292" height="1330" alt="image" src="https://github.com/user-attachments/assets/6c413429-4caa-46a9-862b-7b0bc8882370" />


## Setup

```bash
cp .env.example .env
docker compose up -d
```

## Run

```bash
uvicorn app.main:app --reload
celery -A app.workers.celery_app worker --loglevel=infodoc
```

## Test

```bash
pytest
```

## API

- `POST /api/v1/documents` — upload PDF, returns `{ job_id, status }`
- `GET /api/v1/jobs/{id}` — get job status and chunk count
