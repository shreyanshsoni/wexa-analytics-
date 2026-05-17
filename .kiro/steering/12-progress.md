# 12-progress.md — Current Progress Tracker
# ⚠️ THIS FILE MUST BE UPDATED AFTER EVERY TASK COMPLETED
# ⚠️ THIS IS THE FIRST FILE ANY AI READS AFTER 00-master.md

---

## Current Status
```
Phase:        4 — Dashboards & Widgets
Status:       NOT STARTED — Phase 3 complete, ready to start
Last Updated: 2026-05-17
Last AI:      Claude (claude.ai code)
```

---

## Current Task
```
Task:         Phase 3 kickoff — Data Ingestion
File:         Not started yet
Function:     N/A
Next Action:  Implement ingestion_service.py, then api/v1/ingestion.py
```

---

## Phase 1 — Architecture Setup ✅ COMPLETE
- [x] Monorepo folder structure created
- [x] Backend: pyproject.toml configured (setuptools build, ruff + mypy)
- [x] Backend: FastAPI app created (app/main.py with lifespan)
- [x] Backend: Database connection (core/database.py — asyncpg, pool_size=10)
- [x] Backend: Redis connection (core/redis.py — ssl_cert_reqs=None for Upstash)
- [x] Backend: All SQLAlchemy models created (15 models)
- [x] Backend: Alembic initialized and first migration run (20260517_initial_schema)
- [x] Backend: Celery app configured (workers/celery_app.py)
- [x] Backend: Health check endpoint working (/api/v1/health)
- [x] Backend: Custom exceptions defined (core/exceptions.py)
- [x] Backend: Middleware configured (CORS, correlation ID, exception handlers)
- [x] Backend: Pydantic v2 schemas (auth, org, event, dashboard, widget, alert, report)
- [x] Backend: Repositories (base + user, org, event, dashboard, widget, alert, report)
- [x] Frontend: Next.js app initialized (Next.js 15, TypeScript, Tailwind)
- [x] Frontend: Shadcn/UI installed (button, card, input, label, badge, skeleton, sonner, etc.)
- [x] Frontend: TanStack Query v5 provider in layout.tsx
- [x] Frontend: Zustand stores created (authStore, dashboardStore, uiStore)
- [x] Frontend: API client (axios) configured with token interceptors
- [x] Frontend: Route groups created (auth) + (dashboard) with skeleton pages
- [x] Git: .gitignore in place (no .env files)
- [x] Makefile: All commands defined

## Phase 1 Definition of Done — ALL VERIFIED ✅
- [x] GET /api/v1/health → {"status": "healthy", "checks": {"database": "healthy", "redis": "healthy"}}
- [x] Frontend builds with no TypeScript errors (npm run build)
- [x] alembic history shows initial migration (a4bfc2bf69b6)
- [x] All 15 DB tables created in Neon

## Phase 2 — Authentication & Multi-Tenancy ✅ COMPLETE + POLISHED
- [x] Backend: auth_service.py (signup, login, refresh, logout, accept_invite)
- [x] Backend: organization_service.py (get org, members, invite, remove, update role)
- [x] Backend: api_key_service.py + api_key_repo.py (create, list, revoke, rotate)
- [x] Backend: dependencies.py (get_current_user, get_current_org, RequireOwner/Admin/Analyst/Member)
- [x] Backend: api/v1/auth.py (signup, login, refresh, logout, /me, invite accept)
- [x] Backend: api/v1/organizations.py (me, update, invite, members, remove, update role)
- [x] Backend: api/v1/api_keys.py (list, create, revoke, rotate)
- [x] Backend: schemas updated (ApiResponse wrapper, AuthData, OrgOut, InviteOut, ApiKeyOut)
- [x] Frontend: src/types/api.ts fully typed per API shapes doc
- [x] Frontend: login page with form + JWT store
- [x] Frontend: signup page with org_name field
- [x] Frontend: invite accept page /invite/[token]
- [x] Frontend: dashboard layout with auth guard (redirects to /login if not authenticated)
- [x] ruff ✅ 0 errors, mypy ✅ 0 errors (62 files), pytest ✅ 5/5, tsc ✅, eslint ✅
- [x] **Phase 2 comprehensive tests: 62/62 PASSED** (test files removed after passing)
- [x] bcrypt/passlib compatibility fixed (direct bcrypt usage, no passlib wrapper)
- [x] alembic env.py fixed (async_database_url attribute rename)
- [x] api_key key_prefix column increased VARCHAR(10→16), migration 5268e0893e5f applied
- [x] All Phase 2 test files removed: test_auth.py, test_organizations.py, test_api_keys.py, test_rbac.py
- [x] Frontend: Inter font applied globally (replaces Geist)
- [x] Frontend: Password eye toggle on login, signup, and invite pages
- [x] Frontend: Auth persistence fixed (_hasHydrated + partialize in Zustand persist)
- [x] Frontend: Placeholder pages for all nav routes (dashboards, ingestion, alerts, reports, settings)
- [x] Frontend: Root / redirects to /overview if authenticated, /login if not
- [x] Frontend: Login + signup redirect to /overview if already authenticated
- [x] Git: Fixed broken frontend submodule — frontend now tracked as regular files

## Phase 3 — Data Ingestion ✅ COMPLETE
- [x] Backend: app/schemas/event.py — AliasChoices for "event"/"event_name", stats schema
- [x] Backend: app/services/ingestion_service.py — rate limiting (1000/min org, 100/min key) + Celery dispatch
- [x] Backend: app/workers/tasks/ingestion_tasks.py — real DB writes (single, batch, CSV)
- [x] Backend: app/api/v1/ingestion.py — POST /ingest/events, /ingest/events/batch, /ingest/csv, GET /ingest/stats
- [x] Backend: app/api/router.py — ingestion router registered
- [x] Frontend: ingestion page — API key management, CSV drag-and-drop upload, stats cards, quick-start snippet
- [x] ruff ✅ 0 errors, mypy ✅ 0 errors, tsc ✅ 0 errors

## Phase 4 — Dashboards & Widgets
- [ ] NOT STARTED

## Phase 5 — Alerts (Should Have)
- [ ] NOT STARTED

## Phase 6 — WebSockets (Should Have)
- [ ] NOT STARTED

---

## Git Tags Created
```
phase-1-complete (to be created after commit)
```

---

## Decisions Made This Session
```
1. Resend (email) deferred to Phase 5 — not needed for Must Have tasks
2. Redis ssl_cert_reqs=None for Upstash on macOS (SSL cert verification issue)
3. DATABASE_URL converted to postgresql+asyncpg:// in config.py computed_field
4. Alembic uses async engine (asyncio.run pattern) — no psycopg2 needed
5. layout.tsx uses "use client" for QueryClientProvider — metadata moved out
```

---

## Known Issues / Blockers
```
None
```

---

## External Accounts Status
```
GitHub:   [ ] Created  Repo URL: _______________
Neon:     [x] Created  DB tables created successfully
Upstash:  [x] Created  Redis healthy (ssl_cert_reqs=None fix applied)
Resend:   [ ] Not needed until Phase 5
Railway:  [ ] Phase 2 deploy only
Vercel:   [ ] Phase 2 deploy only
```

---

## Environment Variables Status
```
DATABASE_URL:                    [x] Set in backend/.env
REDIS_URL:                       [x] Set in backend/.env
SECRET_KEY:                      [x] Set in backend/.env (generated)
ACCESS_TOKEN_EXPIRE_MINUTES:     [x] Set (15)
REFRESH_TOKEN_EXPIRE_DAYS:       [x] Set (7)
RESEND_API_KEY:                  [ ] Empty — Phase 5 only
EMAIL_FROM:                      [x] Set (placeholder)
ENVIRONMENT:                     [x] development
FRONTEND_URL:                    [x] http://localhost:3000
NEXT_PUBLIC_API_URL:             [x] Set in frontend/.env.local
NEXT_PUBLIC_WS_URL:              [x] Set in frontend/.env.local
```

---

## Instructions For Next AI Session

When you start a new session:
1. Read this file completely
2. Read `00-master.md`
3. Read `11-build-strategy.md`
4. Read `06-security-auth.md` (domain file for Phase 2)
5. Answer verification questions
6. Wait for user confirmation
7. Start Phase 2 from the first unchecked item

The next task to work on is:
```
PHASE 3 — DATA INGESTION
Read steering/04-data-models.md for event schema details
Start with: backend/app/services/ingestion_service.py
Then: backend/app/api/v1/ingestion.py
Then: background Celery task for async ingestion
```
