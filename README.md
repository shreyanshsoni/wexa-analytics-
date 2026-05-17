# Wexa Analytics

Real-Time Analytics & Reporting Platform — Wexa AI Technical Assessment.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14+, TypeScript, Tailwind, Shadcn/UI, Recharts |
| State | Zustand + TanStack Query v5 |
| Backend | FastAPI, Python 3.11+ |
| ORM | SQLAlchemy 2.0 async |
| Database | PostgreSQL (Neon) |
| Cache/Queue | Redis (Upstash) |
| Task Queue | Celery + Celery Beat |

## Setup

```bash
# 1. Clone and enter
git clone <repo>
cd wexa-analytics

# 2. Copy env file and fill in values
cp backend/.env.example backend/.env

# 3. Install everything
make install

# 4. Run migrations
make migrate

# 5. Start services (4 separate terminals)
make backend    # FastAPI on :8000
make worker     # Celery worker
make beat       # Celery Beat
make frontend   # Next.js on :3000
```

## Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## Architecture

Clean layered architecture: Router → Service → Repository → Model
