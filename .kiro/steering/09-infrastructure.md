# 09-infrastructure.md — Infrastructure, Deployment & Environment

---

## Environment Variables — Complete Reference

### Backend (.env or Railway Variables)
```bash
# ── Database ──
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
# Neon dev branch: postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?ssl=require
# Neon prod branch: postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?ssl=require

# ── Redis ──
REDIS_URL=rediss://default:password@host:port
# ⚠️ MUST be rediss:// (with SSL) for Upstash — not redis://
# Upstash dev:  rediss://default:xxx@xxx.upstash.io:6379
# Upstash prod: rediss://default:xxx@xxx.upstash.io:6379

# ── Authentication ──
SECRET_KEY=minimum-32-chars-random-string-generate-with-secrets-module
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Email ──
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
EMAIL_FROM=noreply@yourdomain.com
# Dev: use onboarding@resend.dev for testing without domain verification

# ── Application ──
ENVIRONMENT=development
# Values: development | production
FRONTEND_URL=http://localhost:3000
# Production: https://your-app.vercel.app

# ── Celery ──
# Uses same REDIS_URL — no separate variable needed

# ── Optional ──
GOOGLE_CLIENT_ID=          # OAuth (optional feature)
GOOGLE_CLIENT_SECRET=      # OAuth (optional feature)
```

### Frontend (.env.local or Vercel Variables)
```bash
# Points to backend
NEXT_PUBLIC_API_URL=http://localhost:8000
# Production: https://your-backend.railway.app

NEXT_PUBLIC_WS_URL=ws://localhost:8000
# Production: wss://your-backend.railway.app
```

---

## Phase 1 — Local Development Setup

### Prerequisites
```bash
# Check versions
python --version    # Must be 3.11.x
node --version      # Must be 20.x
npm --version       # Must be 10.x
git --version
```

### Step by Step Setup
```bash
# 1. Clone repo and setup branches
git clone https://github.com/yourusername/wexa-analytics
cd wexa-analytics
git checkout -b dev
git push -u origin dev

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Create backend .env
cp .env.example .env
# Edit .env with your Neon + Upstash + Resend credentials

# 4. Run migrations
alembic upgrade head

# 5. Seed database
python scripts/seed.py

# 6. Frontend setup
cd ../frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with localhost URLs

# 7. Start all services (use Makefile)
make dev
# OR manually:
# Terminal 1: cd backend && uvicorn app.main:app --reload --port 8000
# Terminal 2: cd backend && celery -A app.workers.celery_app worker --loglevel=info
# Terminal 3: cd backend && celery -A app.workers.celery_app beat --loglevel=info
# Terminal 4: cd frontend && npm run dev
```

### Makefile Commands
```makefile
.PHONY: install run test migrate seed lint

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	make -j4 backend celery-worker celery-beat frontend

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

celery-worker:
	cd backend && celery -A app.workers.celery_app worker --loglevel=info -Q ingestion,alerts,reports

celery-beat:
	cd backend && celery -A app.workers.celery_app beat --loglevel=info

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest --cov=app tests/

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python scripts/seed.py

lint:
	cd backend && ruff check . && mypy app/
	cd frontend && npm run lint

migration:
	cd backend && alembic revision --autogenerate -m "$(name)"
```

---

## Phase 2 — Production Deployment

### Railway Setup (Backend + Celery + Redis)

#### Step 1: Create Railway Project
```
1. Go to railway.app
2. Create new project
3. Connect GitHub repository
4. Select main branch for auto-deploy
```

#### Step 2: Add Redis Service
```
In Railway project → Add Service → Redis
Copy REDIS_URL from Railway dashboard
Note: Railway Redis URL starts with redis:// not rediss://
Upstash is preferred — better free tier
```

#### Step 3: Add FastAPI Service
```
Railway → New Service → GitHub Repo
Root directory: /backend
Build command: pip install -r requirements.txt
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### Step 4: Add Celery Worker Service
```
Railway → New Service → GitHub Repo (same repo)
Root directory: /backend
Build command: pip install -r requirements.txt
Start command: celery -A app.workers.celery_app worker --loglevel=info -Q ingestion,alerts,reports
```

#### Step 5: Add Celery Beat Service
```
Railway → New Service → GitHub Repo (same repo)
Root directory: /backend
Build command: pip install -r requirements.txt
Start command: celery -A app.workers.celery_app beat --loglevel=info
```

#### Step 6: Set Environment Variables
```
In each Railway service → Variables tab
Add all variables from backend .env
ENVIRONMENT=production
FRONTEND_URL=https://your-app.vercel.app
```

### railway.toml (Backend)
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Vercel Setup (Frontend)

#### Step 1: Connect Repository
```
1. Go to vercel.com
2. Import GitHub repository
3. Root directory: /frontend
4. Framework preset: Next.js
5. Branch: main (auto-deploy)
```

#### Step 2: Environment Variables
```
Vercel → Project Settings → Environment Variables
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_WS_URL=wss://your-backend.railway.app
```

#### vercel.json
```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "installCommand": "npm install",
  "regions": ["iad1"]
}
```

---

## Error Recovery Strategies

### When Neon DB Is Down
```python
# SQLAlchemy pool_pre_ping handles this automatically
# If connection fails → retry once → if still fails → return 503

@app.exception_handler(OperationalError)
async def db_error_handler(request, exc):
    logger.error("database_unavailable", error=str(exc))
    return JSONResponse(status_code=503, content={
        "error": {"code": "SERVICE_UNAVAILABLE", "message": "Database temporarily unavailable"}
    })
```

### When Upstash Redis Is Down
```python
# Graceful degradation — app works without Redis
# Rate limiting: skip if Redis unavailable (fail open)
# Caching: skip cache, query DB directly
# Celery: tasks will queue when Redis is back

try:
    await redis.incr(rate_limit_key)
except Exception:
    logger.warning("redis_unavailable_skipping_rate_limit")
    # Continue without rate limiting
```

### When Celery Worker Is Down
```python
# Events ingested → queued in Redis
# When worker comes back → processes backlog automatically
# Upstash persists queue data
# No events lost (within Redis memory limits)
```

---

## Deployment Verification Checklist
```
After deployment, verify:
[ ] GET /api/v1/health returns {"status": "healthy"}
[ ] Can sign up with new account
[ ] Can login and get JWT
[ ] Can ingest event via API key
[ ] Dashboard loads with charts
[ ] Celery worker processes events (check Railway logs)
[ ] Frontend connects to backend (no CORS errors in browser)
[ ] Refresh token cookie is set (check browser devtools)
```
