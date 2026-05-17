# 03-tech-stack.md — Technology Stack & Package Versions

---

## Backend Packages (Python)
Install via: `pip install -r requirements.txt`

### Core Framework
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9        ← file uploads
```

### Database
```
sqlalchemy==2.0.36             ← MUST be 2.0+ for async
asyncpg==0.30.0                ← PostgreSQL async driver
alembic==1.13.0
```

### Validation
```
pydantic==2.9.0                ← MUST be v2 — v1 syntax NOT allowed
pydantic-settings==2.5.0       ← For Settings class
```

### Authentication
```
passlib[bcrypt]==1.7.4         ← Password hashing
python-jose[cryptography]==3.3.0  ← JWT tokens
```

### Task Queue
```
celery==5.4.0
redis==5.1.0                   ← Redis client (Upstash compatible)
flower==2.0.1                  ← Celery monitoring (optional)
```

### Rate Limiting
```
slowapi==0.1.9                 ← FastAPI rate limiting
```

### Email
```
resend==2.4.0                  ← Resend email client
```

### Logging & Observability
```
structlog==24.4.0              ← Structured logging
```

### Testing
```
pytest==8.3.0
pytest-asyncio==0.24.0
httpx==0.27.0                  ← Async HTTP client for testing
pytest-cov==5.0.0              ← Coverage reporting
```

### Code Quality
```
ruff==0.7.0                    ← Linting + formatting
mypy==1.11.0                   ← Type checking
pre-commit==3.8.0              ← Git hooks
```

### PDF Generation (Reports)
```
playwright==1.48.0             ← PDF/PNG snapshots via headless browser
```

---

## Frontend Packages (Node.js)
Install via: `npm install`

### Core Framework
```
next: 14.2.x                   ← App Router (NOT Pages Router)
react: 18.x
react-dom: 18.x
typescript: 5.x
```

### UI & Styling
```
tailwindcss: 3.x
@shadcn/ui                     ← Component library (installed via CLI)
lucide-react: latest           ← Icons
class-variance-authority: latest
clsx: latest
tailwind-merge: latest
```

### State Management
```
zustand: 4.x                   ← Client state ONLY
```

### Data Fetching
```
@tanstack/react-query: 5.x     ← Server state (MUST be v5 — v4 syntax different)
axios: 1.x                     ← HTTP client
```

### Charts
```
recharts: 2.x                  ← All chart implementations
```

### Drag & Drop
```
@dnd-kit/core: 6.x
@dnd-kit/sortable: 8.x
@dnd-kit/utilities: 3.x
```

### Forms
```
react-hook-form: 7.x
@hookform/resolvers: 3.x
zod: 3.x                       ← Form validation (frontend only)
```

### Date Handling
```
date-fns: 3.x
```

### WebSocket
```
Native WebSocket API            ← No additional library needed
```

---

## External Services

### Neon (PostgreSQL)
- URL: https://neon.tech
- Connection string format: `postgresql+asyncpg://user:pass@host/dbname`
- Dev: use `dev` branch connection string
- Prod: use `main` branch connection string
- Enable connection pooling in Neon dashboard
- Use pooled connection string (port 5432 pooled, not 5432 direct)

### Upstash (Redis)
- URL: https://upstash.com
- Connection string format: `rediss://default:pass@host:port` (note: `rediss://` with SSL)
- Dev: create database named `wexa-dev`
- Prod: create database named `wexa-prod`
- ⚠️ ALWAYS use `rediss://` (with SSL) not `redis://`

### Resend (Email)
- URL: https://resend.com
- API key format: `re_xxxxxxxxxxxx`
- From email must be verified domain or use Resend test domain
- Test mode: use `onboarding@resend.dev` as from address

### Railway (Backend Hosting)
- URL: https://railway.app
- Hosts: FastAPI backend + Celery worker + Celery Beat
- Each is a separate Railway service
- Uses `railway.toml` for config

### Vercel (Frontend Hosting)
- URL: https://vercel.com
- Hosts: Next.js frontend only
- Uses `vercel.json` for config
- Auto-deploys from `main` branch

---

## What NOT To Use
```
❌ Django or Django REST Framework (use FastAPI)
❌ SQLAlchemy 1.x (use 2.0 async)
❌ Pydantic v1 (use v2)
❌ TanStack Query v4 (use v5)
❌ Redux (use Zustand)
❌ Chart.js or D3 (use Recharts)
❌ Docker in production (Railway handles containers)
❌ Kubernetes (overkill for this project)
❌ AWS/GCP/Azure (use Railway + Vercel)
❌ SendGrid or Mailgun (use Resend)
❌ socket.io (use native WebSocket)
❌ requests library (use httpx for async)
❌ flask (use FastAPI)
❌ tortoise-orm (use SQLAlchemy)
❌ motor (use asyncpg via SQLAlchemy)
```

---

## Python Version
- Use Python 3.11.x specifically
- Not 3.12 (some Celery compatibility issues)
- Not 3.10 or below (missing features)

## Node Version
- Use Node 20.x LTS
- Not 18.x (missing features)
- Not 22.x (may have compatibility issues)

---

## Environment Variable Names (Quick Reference)
```bash
# Backend
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=rediss://...
SECRET_KEY=...
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@yourdomain.com
ENVIRONMENT=development|production
FRONTEND_URL=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```
