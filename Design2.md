# DESIGN.md

## 1. Overview
_1-2 sentences: what this service does and who calls it._

## 2. Architecture

```
[Client] --> [FastAPI app] --> [PostgreSQL]  (writes notification as PENDING)
                 |
                 v
           [Redis Queue(s)]  (priority-separated: critical/high vs normal/low)
                 |
                 v
           [Worker process(es)] --> [Mocked Email/SMS/Push providers]
                 |
                 v
           [PostgreSQL]  (status updates: SENT / DELIVERED / FAILED)
```
_Replace with your actual diagram (ASCII or mermaid) once the real shape is known._

- **API layer**: FastAPI, validates input, persists PENDING row, enqueues job, returns immediately.
- **Queue**: _RQ / Celery — state which one and why._
- **Worker(s)**: pull jobs by priority, call provider, handle retry/backoff, update status.
- **Providers**: mocked, simulate latency + failure rate.

## 3. Database schema

| Table | Purpose | Key columns |
|---|---|---|
| `users_preferences` | per-user, per-channel opt-in/out | user_id, channel, opted_in |
| `notifications` | one row per notification request | id, user_id, channel, priority, status, template_id, payload, idempotency_key, created_at |
| `notification_status_history` | audit trail of status transitions | notification_id, status, occurred_at, detail |
| `templates` | reusable message templates | id, name, body, required_vars |
| `idempotency_keys` | dedupe table | key, request_hash, response_snapshot, expires_at |

_Explain any indexes/uniqueness constraints you added and why (e.g. unique index on idempotency_key, composite index on (user_id, created_at) for history queries)._

## 4. Failure handling & retries

- Notification is written as `PENDING` to Postgres **before** enqueue — if the queue or worker dies, the row still exists and can be reconciled.
- Retry policy: max 3 retries, exponential backoff (_state your exact delays_), then `FAILED`.
- _Describe what happens on: worker crash mid-send, Redis unavailable, DB unavailable, duplicate delivery risk._

## 5. Idempotency & rate limiting

- Idempotency: _header/body field used, storage, TTL, conflict behavior (409 vs replay)._
- Rate limiting: _algorithm (fixed/sliding window), storage (Redis INCR+EXPIRE or sorted set), limit (100/hr/user), response on breach (429 + Retry-After)._

## 6. Scaling to 1000+ notifications/sec

- _Horizontal worker scaling — stateless workers behind the same queue._
- _DB: connection pooling, read replicas for GET history/status if needed._
- _Queue: partition/shard by priority or by hash(user_id) to preserve ordering per user if that matters._
- _Where's the actual bottleneck at this scale? (likely DB writes or provider rate limits) — say so honestly._

## 7. Trade-offs

| Decision | Alternative considered | Why this choice |
|---|---|---|
| e.g. RQ over Celery | Celery | simpler ops for a take-home scope |
| e.g. Postgres over NoSQL | DynamoDB/Mongo | relational fits status/history queries, ACID for idempotency |
| e.g. Sliding window rate limit | Fixed window | avoids burst-at-boundary problem, small extra Redis cost |

_Add your own rows — this table is the most-read part of the doc for grading, so be honest about what you optimized for given the 4-6 hour budget._