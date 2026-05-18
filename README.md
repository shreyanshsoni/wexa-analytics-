# Wexa Analytics

A production-grade **Real-Time Analytics & Reporting Platform** built for the Wexa AI Senior Full Stack Engineer (Python) Technical Assessment.

Think lightweight Mixpanel/Metabase — organizations ingest events from multiple sources, visualize metrics on customizable dashboards, and manage their team with fine-grained role-based access.

---

## Live Demo

| Service | URL |
|---|---|
| Frontend | _deploy to Vercel — URL here_ |
| Backend API | _deploy to Railway — URL here_ |
| API Docs | `<backend-url>/docs` |
| Health Check | `<backend-url>/api/v1/health` |
| Metrics | `<backend-url>/metrics` |

**Demo credentials (after `make seed`):**

| Role | Email | Password |
|---|---|---|
| Owner | owner@wexa.demo | Demo1234! |
| Admin | admin@wexa.demo | Demo1234! |
| Analyst | analyst@wexa.demo | Demo1234! |
| Viewer | viewer@wexa.demo | Demo1234! |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS, Shadcn/UI |
| **State** | Zustand, TanStack Query v5 |
| **Charts** | Recharts |
| **Backend** | FastAPI, Python 3.11+ with full type hints |
| **ORM** | SQLAlchemy 2.0 async (asyncpg driver) |
| **Migrations** | Alembic |
| **Validation** | Pydantic v2 |
| **Task Queue** | Celery + Celery Beat |
| **Cache / Queue broker** | Redis (Upstash) |
| **Database** | PostgreSQL (Neon) |
| **Email** | Resend |
| **Logging** | structlog with correlation ID middleware |
| **Metrics** | Prometheus via `prometheus-fastapi-instrumentator` |

---

## Architecture

### Layered separation (Routers → Services → Repositories → Models)

```
backend/app/
├── api/v1/              # FastAPI routers — thin, only HTTP concerns
│   ├── auth.py          # POST /auth/signup, /login, /refresh, /logout, /me
│   ├── organizations.py # GET/PUT /organizations/me, members, invites
│   ├── api_keys.py      # GET/POST /api-keys, revoke, rotate
│   ├── ingestion.py     # POST /ingest/events, /batch, /csv, /webhook
│   ├── dashboards.py    # CRUD /dashboards, share, /shared/{token}
│   ├── widgets.py       # CRUD /widgets/{id}
│   ├── saved_queries.py # CRUD /saved-queries
│   └── health.py        # GET /health
│
├── services/            # Business logic — no HTTP, no raw SQL
│   ├── auth_service.py
│   ├── organization_service.py
│   ├── api_key_service.py
│   ├── ingestion_service.py   # rate limiting, Celery dispatch
│   └── dashboard_service.py   # query engine, Redis cache, sharing
│
├── repositories/        # All SQL lives here — one class per model
│   ├── base.py          # Generic CRUD (get, list, create, update, delete)
│   ├── event_repo.py    # count_by_org_in_range, time-series aggregation
│   ├── dashboard_repo.py
│   ├── widget_repo.py
│   └── ...
│
├── models/              # SQLAlchemy ORM models
│   ├── base.py          # BaseModel: id (UUID), created_at, updated_at, deleted_at
│   ├── event.py         # Composite indexes on (org_id, timestamp) and (org_id, event_name)
│   ├── dashboard.py
│   ├── widget.py
│   └── ...
│
├── core/
│   ├── config.py        # Pydantic Settings — all env vars, computed async_database_url
│   ├── dependencies.py  # FastAPI Depends: DbDep, RedisDep, ApiKeyDep, RequireOwner/Admin/...
│   ├── exceptions.py    # WexaError hierarchy → centralized exception handlers
│   ├── middleware.py    # CORS, correlation ID injection, structlog context binding
│   └── security.py      # JWT sign/verify, bcrypt hash/verify, token hashing
│
└── workers/
    ├── celery_app.py    # Celery config: Upstash Redis broker, NullPool pattern
    ├── beat_schedule.py # Scheduled tasks: alert evaluation (60s), token cleanup (02:00)
    └── tasks/
        ├── ingestion_tasks.py  # process_event, process_batch_events, process_csv_upload
        ├── alert_tasks.py      # evaluate_alerts, cleanup_expired_tokens
        └── report_tasks.py     # generate_report
```

### Key design decisions

**Async throughout** — every endpoint, every DB query, every Redis call is `async/await`. SQLAlchemy 2.0 with `asyncpg` driver. No sync code in the hot path.

**NullPool in Celery tasks** — Celery workers call `asyncio.run()` which closes the event loop after each task. Pooled `asyncpg` connections become invalid on the next task. Fix: create a fresh `create_async_engine` with `NullPool` inside each task, dispose in `finally`.

**Rate limiting via Redis** — custom `INCR + EXPIRE` pattern. 1 000 events/min per org, 100 events/min per API key. No external library dependency needed.

**Redis query cache** — `dashboard_service.execute_query()` caches results under `query:{org_id}:{query_id}:{time_range}` with a 5-minute TTL. Cache is invalidated on widget update.

**Org-level data isolation** — every repository method filters by `organization_id`. Cross-org requests return 404 (not 403) to prevent resource ID enumeration.

**Soft deletes** — `BaseModel` carries `deleted_at: datetime | None`. Hard deletes are never used.

---

## Features

### Authentication & Multi-Tenancy
- Email/password signup with bcrypt hashing
- JWT access tokens (15 min) + refresh tokens in HTTP-only cookies (7 days)
- Organization created at signup; invite-based team onboarding via email (Resend)
- Role hierarchy: **Owner → Admin → Analyst → Viewer**
- All endpoints guarded with FastAPI `Depends` — `RequireOwner`, `RequireAdmin`, `RequireAnalyst`, `RequireMember`

### Data Ingestion
- `POST /ingest/events` — single event
- `POST /ingest/events/batch` — up to 1 000 events per request
- `POST /ingest/csv` — CSV file upload (max 10 MB), processed async via Celery
- `POST /ingest/webhook` — flexible payload receiver; event name resolved from `event`→`event_name`→`type`→`action`; auth via `X-Webhook-Secret` header
- `GET /ingest/stats` — events today / 7d / 30d / all-time
- All ingestion events validated by Pydantic v2, stored to PostgreSQL via Celery tasks with retry + exponential backoff

### Dashboards & Widgets
- Create, rename, delete custom dashboards
- Drag-and-drop widget placement (dnd-kit), positions persisted to DB
- 5 widget types: **Line chart, Bar chart, Pie chart, KPI card, Table**
- Each widget links to a saved query with its own time range (24h / 7d / 30d)
- Auto-refresh at 30s / 1m / 5m intervals (configurable per dashboard)
- Public share link — `/shared/{token}` is fully read-only, no auth required
- Full-screen presentation mode
- Dashboard templates: **Executive Overview, Web Analytics, DevOps, Sales** (seeded)

### API Key Management
- Create, revoke, rotate keys per organization
- Keys stored as SHA-256 hashes; only the prefix is stored in plaintext
- Full key shown once on creation/rotation

---

## API Reference

Interactive docs available at `http://localhost:8000/docs` (Swagger UI) and `/redoc`.

### Authentication
```
POST   /api/v1/auth/signup          Create account + organization
POST   /api/v1/auth/login           Get access token + refresh cookie
POST   /api/v1/auth/refresh         Rotate refresh token
POST   /api/v1/auth/logout          Clear refresh cookie
GET    /api/v1/auth/me              Current user + org + role
POST   /api/v1/auth/invite/accept   Accept invite token
```

### Ingestion
```
POST   /api/v1/ingest/events        Single event   (X-API-Key header)
POST   /api/v1/ingest/events/batch  Batch events   (X-API-Key header)
POST   /api/v1/ingest/csv           CSV upload     (JWT, Analyst+)
POST   /api/v1/ingest/webhook       Webhook event  (X-Webhook-Secret header)
GET    /api/v1/ingest/stats         Event counts   (JWT, Member+)
```

### Dashboards
```
GET    /api/v1/dashboards           List org dashboards
POST   /api/v1/dashboards           Create dashboard
GET    /api/v1/dashboards/{id}      Get dashboard + widgets + query results
PUT    /api/v1/dashboards/{id}      Update dashboard
DELETE /api/v1/dashboards/{id}      Delete dashboard
POST   /api/v1/dashboards/{id}/share Toggle public sharing
GET    /api/v1/dashboards/shared/{token}  Public read-only view (no auth)
```

### Widgets & Saved Queries
```
POST   /api/v1/widgets              Add widget to dashboard
PUT    /api/v1/widgets/{id}         Update widget (title, type, time range, position)
DELETE /api/v1/widgets/{id}         Remove widget
GET    /api/v1/saved-queries        List org saved queries
POST   /api/v1/saved-queries        Create saved query  (Analyst+)
PUT    /api/v1/saved-queries/{id}   Update saved query  (Analyst+)
DELETE /api/v1/saved-queries/{id}   Delete saved query  (Analyst+)
```

### Error envelope

All errors follow a consistent JSON shape:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded (100/min). Retry after 60 seconds."
  }
}
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (`postgresql://...`) |
| `REDIS_URL` | Yes | — | Redis connection string (`rediss://...` for TLS) |
| `SECRET_KEY` | Yes | — | JWT signing secret — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `ENVIRONMENT` | No | `development` | `development` / `production` / `testing` |
| `FRONTEND_URL` | No | `http://localhost:3000` | Allowed CORS origin |
| `RESEND_API_KEY` | No | `""` | Resend API key for invite emails |
| `EMAIL_FROM` | No | `noreply@wexa.ai` | From address for invite emails |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Backend base URL e.g. `http://localhost:8000` |
| `NEXT_PUBLIC_WS_URL` | No | WebSocket base URL e.g. `ws://localhost:8000` |

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A PostgreSQL database (Neon free tier works)
- A Redis instance (Upstash free tier works)

### Steps

```bash
# 1. Clone
git clone <repo-url>
cd wexa-analytics

# 2. Backend env
cp backend/.env.example backend/.env
# Edit backend/.env — fill in DATABASE_URL, REDIS_URL, SECRET_KEY

# 3. Frontend env
cp frontend/.env.local.example frontend/.env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

# 4. Install all dependencies
make install

# 5. Run database migrations
make migrate

# 6. (Optional) Seed demo data
make seed
# Creates 4 demo users, 2 500 events over 30 days, 4 dashboards, 9 saved queries

# 7. Start all services (4 separate terminals)
make backend    # FastAPI on :8000
make worker     # Celery worker  (-Q ingestion,celery)
make beat       # Celery Beat scheduler
make frontend   # Next.js on :3000
```

### Verify everything is running

```bash
# Health check
curl http://localhost:8000/api/v1/health
# → {"status":"healthy","checks":{"database":"healthy","redis":"healthy"}}

# Metrics
curl http://localhost:8000/metrics
# → Prometheus text format

# Send a test event
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"event": "page_view", "properties": {"url": "/home"}}'
```

---

## Available Make Commands

```bash
make backend    # Start FastAPI (uvicorn --reload)
make worker     # Start Celery worker
make beat       # Start Celery Beat
make frontend   # Start Next.js dev server
make migrate    # Run Alembic migrations (upgrade head)
make migration  # Create new migration  (name="describe change")
make rollback   # Roll back one migration
make seed       # Wipe DB and insert demo data
make test       # Run pytest test suite
make lint       # Ruff lint check
make lint-fix   # Ruff auto-fix
make typecheck  # mypy type check
make install    # Install backend venv + frontend node_modules
make setup      # install + migrate in one command
```

---

## Background Processing

Celery is used for all heavy/async work:

| Task | Queue | Trigger | Retry |
|---|---|---|---|
| `ingestion.process_event` | `ingestion` | On each API event | 3× exponential backoff (max 300s) |
| `ingestion.process_batch_events` | `ingestion` | On batch ingest | 3× exponential backoff |
| `ingestion.process_csv_upload` | `ingestion` | On CSV upload | 3× exponential backoff |
| `alert_tasks.evaluate_alerts` | `celery` | Every 60s (Beat) | — |
| `alert_tasks.cleanup_expired_tokens` | `celery` | Daily at 02:00 (Beat) | — |

The worker must listen to **both** queues:
```bash
celery -A app.workers.celery_app worker -Q ingestion,celery
```

---

## Project Structure

```
wexa-analytics/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routers
│   │   ├── core/            # Config, security, middleware, exceptions
│   │   ├── models/          # SQLAlchemy ORM models (15 models)
│   │   ├── repositories/    # Data access layer
│   │   ├── schemas/         # Pydantic v2 request/response schemas
│   │   ├── services/        # Business logic
│   │   └── workers/         # Celery app + tasks + Beat schedule
│   ├── alembic/             # DB migrations
│   ├── scripts/
│   │   └── seed.py          # Demo data seed script
│   ├── tests/               # pytest test suite
│   ├── pyproject.toml       # Dependencies + ruff + mypy config
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/      # Login, signup, invite accept
│   │   │   ├── (dashboard)/ # Dashboards, ingestion, settings
│   │   │   └── shared/      # Public dashboard viewer
│   │   ├── components/
│   │   │   ├── charts/      # LineChart, BarChart, PieChart, KpiCard, Table
│   │   │   └── dashboard/   # WidgetCard, drag-drop wrapper
│   │   ├── store/           # Zustand stores (auth, dashboard, ui)
│   │   ├── lib/             # Axios API client with interceptors
│   │   └── types/           # TypeScript API types
│   └── .env.example
│
├── Makefile
└── README.md
```

---

## Code Quality

All three checks pass with zero errors:

```bash
make lint       # ruff — 0 warnings
make typecheck  # mypy — 0 errors (strict mode on app/)
cd frontend && npx tsc --noEmit  # tsc — 0 errors
```
