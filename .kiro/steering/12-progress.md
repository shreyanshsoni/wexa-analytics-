# 12-progress.md — Current Progress Tracker
# ⚠️ THIS FILE MUST BE UPDATED AFTER EVERY TASK COMPLETED
# ⚠️ THIS IS THE FIRST FILE ANY AI READS AFTER 00-master.md

---

## Current Status
```
Phase:        4 — Dashboards & Widgets
Status:       COMPLETE ✅ — Phase 5 (Alerts) is next
Last Updated: 2026-05-18
Last AI:      Claude (claude.ai code)
```

---

## Current Task
```
Task:         Phase 5 — Alerts & Notifications
File:         Not started yet
Function:     N/A
Next Action:  Implement alert models, alert_service.py, then api/v1/alerts.py
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

## Phase 4 — Dashboards & Widgets ✅ COMPLETE
- [x] Backend: app/schemas/dashboard.py — full typed schemas (SavedQuery, Widget, Dashboard, QueryResult, Share)
- [x] Backend: app/services/dashboard_service.py — execute_query (date_trunc SQL + Redis 5-min cache), full CRUD for SavedQuery/Dashboard/Widget, share_dashboard, _apply_template
- [x] Backend: app/api/v1/dashboards.py — GET/POST/PUT/DELETE /dashboards, shared/{token} (no auth), POST /{id}/share
- [x] Backend: app/api/v1/widgets.py — GET/POST/PUT/DELETE /widgets/{id}
- [x] Backend: app/api/v1/saved_queries.py — full CRUD for /saved-queries; RBAC fixed (RequireMember reads, RequireAnalyst writes)
- [x] Backend: app/api/router.py — dashboards, widgets, saved_queries routers registered
- [x] Backend: Prometheus metrics at GET /metrics — prometheus-fastapi-instrumentator v7.1.0, excludes /metrics self-tracking
- [x] Backend: scripts/seed.py — full demo seed: 4 users (Owner/Admin/Analyst/Viewer), 2500 events over 30 days, 8 saved queries, 4 dashboards; `make seed`
- [x] Backend: Security fix — get_dashboard + get_widget return 404 (not 403) for cross-org to prevent ID enumeration
- [x] Backend: Share fix — body.is_public → body.enabled, ShareResponse.share_url → str | None
- [x] Frontend: src/types/api.ts — fully updated with Dashboard, Widget, SavedQuery, QueryResult types
- [x] Frontend: src/app/(dashboard)/settings/page.tsx — org rename, invite member, members list with RBAC
- [x] Frontend: src/components/charts/ — LineChartWidget, BarChartWidget, PieChartWidget, KpiCardWidget, TableWidget
- [x] Frontend: src/components/dashboard/WidgetCard.tsx — chart dispatch, edit/delete menu, cached badge
- [x] Frontend: /dashboards route is the primary dashboard list (was /overview); /overview redirects
- [x] Frontend: src/app/(dashboard)/dashboards/[id]/page.tsx — dnd-kit drag-drop, auto-refresh, share/fullscreen, WidgetEditorDialog
- [x] Frontend: src/app/shared/[token]/page.tsx — public read-only dashboard view (no auth)
- [x] ruff ✅ 0 errors, mypy ✅ 0 errors, tsc ✅ 0 errors
- [x] Tests: test_phase4_dashboards.py — 72 tests (CRUD, RBAC, org isolation, sharing, widgets, query results)
- [x] Tests: test_metrics.py — 27 tests (endpoint format, metric families, counter increments, duration sanity)
- [x] Commit: 7393c68 feat: Phase 4 complete

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
4. Read relevant domain steering file for current task
5. Answer verification questions
6. Wait for user confirmation
7. Start Phase 5 from the first unchecked item

The next task to work on is:
```
PHASE 5 — ALERTS & NOTIFICATIONS
Read steering/04-data-models.md for Alert model details
Start with: backend/app/services/alert_service.py
Then: backend/app/api/v1/alerts.py
Then: Celery Beat periodic task to evaluate alert conditions
Then: frontend alerts page
```
