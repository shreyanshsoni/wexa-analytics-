# 14-coding-order.md — Exact File Creation Order

---

## ⚠️ CRITICAL RULE
Always create files in the EXACT order listed below.
Each file depends on files created before it.
Creating files out of order causes import errors.

---

## Phase 1 — Architecture Setup (File Creation Order)

### Step 1: Root Level Files
```
1.  wexa-analytics/.gitignore
2.  wexa-analytics/Makefile
3.  wexa-analytics/README.md               (skeleton only)
4.  wexa-analytics/CHANGELOG.md            (skeleton only)
```

### Step 2: Backend Foundation
```
5.  backend/pyproject.toml
6.  backend/requirements.txt
7.  backend/.env.example                   (template, no real values)
8.  backend/app/__init__.py
9.  backend/app/core/__init__.py
10. backend/app/core/config.py             (Settings class — ALL env vars)
11. backend/app/core/database.py           (async engine + session)
12. backend/app/core/redis.py              (Upstash connection)
13. backend/app/core/exceptions.py        (custom exception hierarchy)
14. backend/app/core/security.py           (JWT, bcrypt, API key utils)
15. backend/app/core/middleware.py         (CORS, correlation ID)
16. backend/app/core/dependencies.py      (get_db, get_redis)
```

### Step 3: Database Models (ORDER MATTERS — foreign keys)
```
17. backend/app/models/__init__.py
18. backend/app/models/base.py             (TimestampMixin, Base)
19. backend/app/models/user.py             (no foreign keys)
20. backend/app/models/organization.py    (no foreign keys)
21. backend/app/models/membership.py      (needs user + org)
22. backend/app/models/invite.py          (needs user + org)
23. backend/app/models/refresh_token.py   (needs user)
24. backend/app/models/api_key.py         (needs user + org)
25. backend/app/models/event.py           (needs org — partitioned)
26. backend/app/models/saved_query.py     (needs org)
27. backend/app/models/dashboard.py       (needs user + org)
28. backend/app/models/widget.py          (needs dashboard + saved_query)
29. backend/app/models/alert.py           (needs user + org + saved_query)
30. backend/app/models/alert_history.py   (needs alert)
31. backend/app/models/report.py          (needs dashboard + user + org)
```

### Step 4: Alembic Setup
```
32. backend/alembic.ini
33. backend/alembic/env.py                (async migration runner)
34. backend/alembic/script.py.mako
35. RUN: alembic revision --autogenerate -m "initial schema"
36. RUN: alembic upgrade head
```

### Step 5: Schemas (Pydantic v2)
```
37. backend/app/schemas/__init__.py
38. backend/app/schemas/common.py          (base response schemas)
39. backend/app/schemas/auth.py
40. backend/app/schemas/organization.py
41. backend/app/schemas/event.py
42. backend/app/schemas/dashboard.py
43. backend/app/schemas/widget.py
44. backend/app/schemas/alert.py
45. backend/app/schemas/report.py
```

### Step 6: Repositories (DB layer)
```
46. backend/app/repositories/__init__.py
47. backend/app/repositories/base.py       (generic CRUD)
48. backend/app/repositories/user_repo.py
49. backend/app/repositories/organization_repo.py
50. backend/app/repositories/event_repo.py
51. backend/app/repositories/dashboard_repo.py
52. backend/app/repositories/widget_repo.py
53. backend/app/repositories/alert_repo.py
54. backend/app/repositories/report_repo.py
```

### Step 7: Celery Setup
```
55. backend/app/workers/__init__.py
56. backend/app/workers/celery_app.py      (Celery instance)
57. backend/app/workers/beat_schedule.py   (Celery Beat schedule)
58. backend/app/workers/tasks/__init__.py
59. backend/app/workers/tasks/ingestion_tasks.py  (placeholder)
60. backend/app/workers/tasks/alert_tasks.py      (placeholder)
61. backend/app/workers/tasks/report_tasks.py     (placeholder)
```

### Step 8: API Router + Health Check
```
62. backend/app/api/__init__.py
63. backend/app/api/router.py              (main router)
64. backend/app/api/v1/__init__.py
65. backend/app/api/v1/health.py           (GET /health)
66. backend/app/main.py                    (FastAPI app entry point)
```

### Step 9: Test Foundation
```
67. backend/tests/__init__.py
68. backend/tests/conftest.py
```

### Step 10: Frontend Foundation
```
69. frontend/package.json
70. frontend/tsconfig.json
71. frontend/tailwind.config.ts
72. frontend/next.config.ts
73. frontend/.env.local.example
74. INSTALL: npx shadcn@latest init
75. frontend/src/app/layout.tsx            (root layout + providers)
76. frontend/src/app/page.tsx              (redirect to /login or /overview)
77. frontend/src/app/(auth)/login/page.tsx (skeleton)
78. frontend/src/app/(auth)/signup/page.tsx (skeleton)
79. frontend/src/app/(dashboard)/layout.tsx (protected layout)
80. frontend/src/app/(dashboard)/overview/page.tsx (skeleton)
81. frontend/src/types/api.ts              (from 13-api-shapes.md)
82. frontend/src/lib/api.ts               (axios instance)
83. frontend/src/store/authStore.ts
84. frontend/src/store/dashboardStore.ts
85. frontend/src/store/uiStore.ts
86. frontend/src/components/shared/LoadingSpinner.tsx
87. frontend/src/components/shared/ErrorBoundary.tsx
```

### Step 11: Scripts
```
88. backend/scripts/__init__.py
89. backend/scripts/seed.py
```

### ✅ Phase 1 Complete — Test:
```bash
make dev
# All 4 services start
# GET localhost:8000/api/v1/health → {"status": "healthy"}
# localhost:3000 → loads (redirects to login)
```

---

## Phase 2 — Auth (File Creation Order)

```
1.  backend/app/services/__init__.py
2.  backend/app/services/auth_service.py
3.  backend/app/services/organization_service.py
4.  backend/app/core/dependencies.py       (add auth dependencies)
5.  backend/app/api/v1/auth.py
6.  backend/app/api/v1/organizations.py
7.  backend/app/api/v1/api_keys.py
8.  backend/app/api/router.py              (include new routers)
9.  backend/tests/test_auth.py
10. frontend/src/app/(auth)/login/page.tsx     (full implementation)
11. frontend/src/app/(auth)/signup/page.tsx    (full implementation)
12. frontend/src/app/(auth)/invite/[token]/page.tsx
13. frontend/src/components/auth/LoginForm.tsx
14. frontend/src/components/auth/SignupForm.tsx
15. frontend/src/hooks/useAuth.ts
16. frontend/src/app/(dashboard)/layout.tsx    (add auth check)
17. frontend/src/app/(dashboard)/settings/page.tsx (member management)
```

---

## Phase 3 — Data Ingestion (File Creation Order)

```
1.  backend/app/services/ingestion_service.py
2.  backend/app/workers/tasks/ingestion_tasks.py  (full implementation)
3.  backend/app/api/v1/ingestion.py
4.  backend/app/api/router.py              (include ingestion router)
5.  backend/tests/test_ingestion.py
6.  frontend/src/app/(dashboard)/ingestion/page.tsx
7.  frontend/src/components/ingestion/CSVUpload.tsx
8.  frontend/src/components/ingestion/APIKeyManager.tsx
9.  frontend/src/hooks/useIngestion.ts
```

---

## Phase 4 — Dashboards (File Creation Order)

```
1.  backend/app/services/dashboard_service.py
2.  backend/app/services/widget_service.py
3.  backend/app/services/query_service.py  (time series query engine)
4.  backend/app/api/v1/dashboards.py
5.  backend/app/api/v1/widgets.py
6.  backend/app/api/v1/saved_queries.py
7.  backend/app/api/router.py              (include dashboard routers)
8.  backend/tests/test_dashboards.py
9.  frontend/src/components/charts/LineChart.tsx
10. frontend/src/components/charts/BarChart.tsx
11. frontend/src/components/charts/PieChart.tsx
12. frontend/src/components/charts/KPICard.tsx
13. frontend/src/components/charts/DataTable.tsx
14. frontend/src/components/dashboard/DashboardGrid.tsx
15. frontend/src/components/dashboard/WidgetCard.tsx
16. frontend/src/components/dashboard/WidgetEditor.tsx
17. frontend/src/components/dashboard/TimeRangeSelector.tsx
18. frontend/src/app/(dashboard)/dashboards/page.tsx
19. frontend/src/app/(dashboard)/dashboards/[id]/page.tsx
20. frontend/src/app/(auth)/shared/[token]/page.tsx  (public view)
21. frontend/src/hooks/useDashboard.ts
22. frontend/src/hooks/useWidgets.ts
```

---

## What Breaks If Order Is Wrong

| Wrong Order | Error |
|---|---|
| Models before Base | ImportError: cannot import Base |
| Widget before Dashboard | ForeignKeyViolation in migration |
| Router before main.py | ImportError in FastAPI |
| Service before Repository | AttributeError: no repo methods |
| Frontend hooks before API client | Cannot find api module |
| Shadcn components before init | Component import fails |
| Migration before all models | Missing tables in DB |

---

## Quick Reference — Where Each Thing Lives

| What | File |
|---|---|
| App entry point | `backend/app/main.py` |
| All env variables | `backend/app/core/config.py` |
| DB session | `backend/app/core/database.py` |
| Redis client | `backend/app/core/redis.py` |
| Custom exceptions | `backend/app/core/exceptions.py` |
| JWT + bcrypt | `backend/app/core/security.py` |
| FastAPI Depends | `backend/app/core/dependencies.py` |
| All routes registered | `backend/app/api/router.py` |
| Celery instance | `backend/app/workers/celery_app.py` |
| Celery Beat schedule | `backend/app/workers/beat_schedule.py` |
| Axios instance | `frontend/src/lib/api.ts` |
| Auth state | `frontend/src/store/authStore.ts` |
| All TypeScript types | `frontend/src/types/api.ts` |
