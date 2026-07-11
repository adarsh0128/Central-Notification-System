# Notification Service Backend

A production-quality, multi-channel notification microservice backend built with FastAPI, SQLAlchemy 2.0, Alembic, Celery, and Redis.

---

## Tech Stack & Rationale

- **FastAPI**: Handles high-performance asynchronous web requests and generates OpenAPI specifications.
- **SQLAlchemy 2.0 & Alembic**: Delivers standard async database ORM mapping and schema migration management.
- **PostgreSQL**: Reliable, ACID-compliant relational storage supporting JSONB fields.
- **Celery & Redis**: Executes background processing, priority queue routing, delayed retries, sliding-window rate limiting, and idempotency key locking.

---

## Project Structure

```text
notification-service/
  app/
    api/            # FastAPI routers (thin controllers)
    services/       # Business logic (rate limiting, idempotency, etc.)
    repositories/   # Database access layer
    models/         # SQLAlchemy models
    schemas/        # Pydantic request/response validation
    workers/        # Celery application & task runners
    providers/      # Mocked EMAIL, SMS, and PUSH delivery clients
    core/           # Config settings, logging wrappers, DB session pool
  tests/
    unit/           # Unit tests
    integration/    # Integration tests
  alembic/          # Database migrations
  DESIGN.md         # System architecture & scalability details
  README.md         # Setup and run guide
  Dockerfile        # Multi-purpose Docker image
  docker-compose.yml# Container infrastructure
  openapi.json      # OpenAPI specifications
  .env.example      # Sample configurations
```

---

## Local Setup

### Option A: Using Docker & Docker Compose (Recommended)

1. **Clone the repository** and navigate to the project directory.
2. **Build and start all containers**:
   ```bash
   docker-compose up --build
   ```
   This will spin up:
   - PostgreSQL (`notification_db`) listening on port `5433`
   - Redis (`notification_redis`) listening on port `6379`
   - FastAPI server (`notification_web`) listening on port `8000`
   - Celery worker (`notification_worker`)
   - Celery Beat scheduler (`notification_beat`)
3. **Database migrations** are automatically run on startup inside the web container.

### Option B: Local Setup (without Docker)

1. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment variables**:
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   *Make sure you have a running PostgreSQL instance on port 5433 (or update `.env`) and a running Redis instance on port 6379.*
4. **Run migrations**:
   ```bash
   alembic upgrade head
   ```
5. **Run FastAPI Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
6. **Run Celery Worker**:
   ```bash
   celery -A app.workers.celery_app worker --loglevel=info -Q critical,high,default,low -c 4
   ```
7. **Run Celery Beat Scheduler**:
   ```bash
   celery -A app.workers.celery_app beat --loglevel=info
   ```

---

## How to Run Tests

Ensure your virtual environment is active and running dependencies:

```bash
# Run all tests (unit + integration)
PYTHONPATH=. pytest
```

---

## API Documentation

- **Swagger UI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Static OpenAPI JSON**: Located in the project root as `openapi.json`.

---

## Assumptions Made

1. **User Database**: This notification service operates as an independent service and does not manage users or credentials directly. It expects a user ID as a string (`userId`). If user preference records are missing, we default to assuming the user has opted-in to all channels (`EMAIL`, `SMS`, `PUSH`).
2. **Delivery Targets**:
   - For `EMAIL`, mock delivery targets are constructed dynamically as `{userId}@example.com`.
   - For `SMS`, a standard mock telephone number `+15555555555` is used.
   - For `PUSH`, a mock token format `push_token_{userId}` is used.
3. **Idempotency Headers**: The `x-idempotency-key` header is used to manage request idempotency. Keys expire automatically after 24 hours.
#
