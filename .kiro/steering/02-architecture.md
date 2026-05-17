# 02-architecture.md — Project Architecture & Structure

---

## Monorepo Structure
```
wexa-analytics/                    ← git root
├── CLAUDE.md                      ← Claude Code auto-reads
├── README.md                      ← Professional project readme
├── CONTRIBUTING.md                ← Contribution guidelines
├── CHANGELOG.md                   ← Version/phase changelog
├── Makefile                       ← One-command operations
├── .gitignore                     ← Never commit .env files
├── .kiro/
│   └── steering/                  ← All steering files live here
├── backend/                       ← FastAPI Python application
└── frontend/                      ← Next.js application
```

---

## Backend Structure (FastAPI)
```
backend/
├── pyproject.toml                 ← Python project config, linting, testing
├── alembic.ini                    ← Alembic migration config
├── alembic/
│   ├── env.py                     ← Async alembic environment
│   └── versions/                  ← Migration files (auto-generated)
├── scripts/
│   ├── seed.py                    ← Database seeding script
│   └── generate_api_key.py        ← Utility script
├── tests/
│   ├── conftest.py                ← Shared fixtures
│   ├── test_auth.py
│   ├── test_ingestion.py
│   └── test_dashboards.py
└── app/
    ├── main.py                    ← FastAPI app entry point
    ├── core/
    │   ├── config.py              ← Settings via pydantic-settings
    │   ├── database.py            ← Async SQLAlchemy engine + session
    │   ├── redis.py               ← Upstash Redis connection
    │   ├── security.py            ← JWT, bcrypt, API key utilities
    │   ├── dependencies.py        ← FastAPI Depends (auth, org, role)
    │   ├── exceptions.py          ← Custom exception classes
    │   └── middleware.py          ← CORS, logging, correlation ID
    ├── models/                    ← SQLAlchemy ORM models
    │   ├── base.py                ← Base model with id, created_at, updated_at, deleted_at
    │   ├── user.py
    │   ├── organization.py
    │   ├── membership.py
    │   ├── invite.py
    │   ├── api_key.py
    │   ├── event.py
    │   ├── dashboard.py
    │   ├── widget.py
    │   ├── saved_query.py
    │   ├── alert.py
    │   ├── alert_history.py
    │   └── report.py
    ├── schemas/                   ← Pydantic v2 request/response schemas
    │   ├── auth.py
    │   ├── organization.py
    │   ├── event.py
    │   ├── dashboard.py
    │   ├── widget.py
    │   ├── alert.py
    │   └── report.py
    ├── repositories/              ← DB query layer (raw DB operations only)
    │   ├── base.py                ← Generic CRUD repository
    │   ├── user_repo.py
    │   ├── organization_repo.py
    │   ├── event_repo.py
    │   ├── dashboard_repo.py
    │   ├── widget_repo.py
    │   ├── alert_repo.py
    │   └── report_repo.py
    ├── services/                  ← Business logic layer
    │   ├── auth_service.py
    │   ├── organization_service.py
    │   ├── ingestion_service.py
    │   ├── dashboard_service.py
    │   ├── widget_service.py
    │   ├── query_service.py
    │   ├── alert_service.py
    │   └── report_service.py
    ├── api/
    │   ├── router.py              ← Main API router (includes all sub-routers)
    │   └── v1/                    ← API version 1
    │       ├── auth.py            ← /api/v1/auth/*
    │       ├── organizations.py   ← /api/v1/organizations/*
    │       ├── ingestion.py       ← /api/v1/ingest/*
    │       ├── dashboards.py      ← /api/v1/dashboards/*
    │       ├── widgets.py         ← /api/v1/widgets/*
    │       ├── alerts.py          ← /api/v1/alerts/*
    │       ├── reports.py         ← /api/v1/reports/*
    │       └── health.py          ← /api/v1/health
    └── workers/
        ├── celery_app.py          ← Celery application instance
        ├── tasks/
        │   ├── ingestion_tasks.py ← Process events, CSV files
        │   ├── alert_tasks.py     ← Evaluate alert rules
        │   └── report_tasks.py    ← Generate PDF/PNG reports
        └── beat_schedule.py       ← Celery Beat schedule config
```

---

## Frontend Structure (Next.js 14+)
```
frontend/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── .env.local                     ← Never commit this
├── public/
└── src/
    ├── app/                       ← Next.js App Router
    │   ├── layout.tsx             ← Root layout
    │   ├── page.tsx               ← Landing/redirect page
    │   ├── (auth)/                ← Route group — no sidebar
    │   │   ├── login/page.tsx
    │   │   ├── signup/page.tsx
    │   │   └── invite/[token]/page.tsx
    │   └── (dashboard)/           ← Route group — with sidebar
    │       ├── layout.tsx         ← Dashboard layout with sidebar
    │       ├── overview/page.tsx
    │       ├── dashboards/
    │       │   ├── page.tsx       ← Dashboard list
    │       │   └── [id]/page.tsx  ← Single dashboard view
    │       ├── ingestion/page.tsx
    │       ├── alerts/page.tsx
    │       ├── reports/page.tsx
    │       └── settings/page.tsx
    ├── components/
    │   ├── ui/                    ← Shadcn/UI components (auto-generated)
    │   ├── charts/                ← Recharts wrappers
    │   │   ├── LineChart.tsx
    │   │   ├── BarChart.tsx
    │   │   ├── PieChart.tsx
    │   │   └── KPICard.tsx
    │   ├── dashboard/
    │   │   ├── DashboardGrid.tsx  ← dnd-kit drag-drop grid
    │   │   ├── WidgetCard.tsx
    │   │   └── WidgetEditor.tsx
    │   ├── auth/
    │   │   ├── LoginForm.tsx
    │   │   └── SignupForm.tsx
    │   └── shared/
    │       ├── Sidebar.tsx
    │       ├── Header.tsx
    │       ├── LoadingSpinner.tsx
    │       └── ErrorBoundary.tsx
    ├── lib/
    │   ├── api.ts                 ← Axios instance with interceptors
    │   ├── auth.ts                ← Auth utilities
    │   └── utils.ts               ← Shared utilities
    ├── store/
    │   ├── authStore.ts           ← Zustand auth state
    │   ├── dashboardStore.ts      ← Zustand dashboard state
    │   └── uiStore.ts             ← Zustand UI state (modals, sidebar)
    ├── hooks/
    │   ├── useAuth.ts
    │   ├── useDashboard.ts
    │   └── useWebSocket.ts
    └── types/
        ├── api.ts                 ← API response types
        ├── dashboard.ts
        └── auth.ts
```

---

## Architecture Layers (Backend)
```
HTTP Request
     ↓
Router (api/v1/*.py)
  - Validates request via Pydantic schema
  - Calls service layer
  - Returns response schema
  - NEVER contains business logic
  - NEVER queries database directly
     ↓
Service (services/*.py)
  - Contains ALL business logic
  - Orchestrates repository calls
  - Handles transactions
  - Calls Celery tasks for async work
  - NEVER directly accesses DB models
     ↓
Repository (repositories/*.py)
  - ONLY database operations
  - Raw SQLAlchemy queries
  - Always filtered by org_id (multitenancy)
  - NEVER contains business logic
     ↓
Model (models/*.py)
  - SQLAlchemy ORM definitions
  - NO business logic
  - NO validation logic
```

---

## API Versioning Strategy
- All endpoints under `/api/v1/`
- Version in URL path (not header)
- Future versions: `/api/v2/` as separate router
- Never break existing v1 endpoints

---

## Naming Conventions
| Type | Convention | Example |
|---|---|---|
| Python files | snake_case | `user_service.py` |
| Python classes | PascalCase | `UserService` |
| Python functions | snake_case | `get_user_by_email` |
| Python variables | snake_case | `user_id` |
| DB tables | snake_case plural | `users`, `organizations` |
| DB columns | snake_case | `created_at`, `org_id` |
| API endpoints | kebab-case | `/api/v1/api-keys` |
| TypeScript files | PascalCase for components | `LoginForm.tsx` |
| TypeScript files | camelCase for utils | `authUtils.ts` |
| Env variables | UPPER_SNAKE_CASE | `DATABASE_URL` |

---

## Data Flow (End to End)
```
Event Ingestion:
Client → POST /api/v1/ingest/events (API Key auth)
       → Validate Pydantic schema
       → Check rate limit (Redis)
       → Drop raw event to Celery queue (Redis)
       → Return 202 Accepted immediately
       → Celery worker picks up task
       → Normalize event
       → Store in PostgreSQL events table
       → WebSocket push to live dashboard (Phase 6)

Dashboard Load:
Browser → GET /api/v1/dashboards/{id} (JWT auth)
        → Check org membership
        → Fetch dashboard + widgets config
        → For each widget: execute saved query against events
        → Cache query result in Redis (5 min TTL)
        → Return all data in single response
        → Frontend renders charts
```
