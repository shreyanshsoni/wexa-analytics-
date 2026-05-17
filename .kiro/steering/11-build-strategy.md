# 11-build-strategy.md — Build Strategy, Phases & Handoff Protocol

---

## ⚠️ CRITICAL RULE
Never start the next phase until:
1. Current phase passes ALL definition of done criteria
2. User explicitly says "proceed to next phase"
3. Progress.md is updated
4. Git commit with phase tag is made

---

## Phase Definitions & Done Criteria

---

### 🔴 Phase 1 — Architecture Setup
**Goal:** Working skeleton that proves the architecture is sound

#### Tasks:
- [ ] Monorepo folder structure created exactly as per `02-architecture.md`
- [ ] Backend: FastAPI app runs on port 8000
- [ ] Backend: Database connection to Neon works
- [ ] Backend: Redis connection to Upstash works
- [ ] Backend: Celery worker starts without errors
- [ ] Backend: Health check endpoint returns healthy
- [ ] Backend: All SQLAlchemy models created
- [ ] Backend: Alembic migrations run successfully
- [ ] Backend: pyproject.toml with ruff + mypy configured
- [ ] Frontend: Next.js app runs on port 3000
- [ ] Frontend: Shadcn/UI installed and configured
- [ ] Frontend: TanStack Query provider set up
- [ ] Frontend: Zustand stores created
- [ ] Frontend: Axios API client with interceptors set up
- [ ] Git: Repository initialized with dev branch
- [ ] Git: .gitignore in place (no .env files committed)
- [ ] Makefile: All commands working

#### Definition of Done:
```
✅ make dev starts all 4 services without errors
✅ GET /api/v1/health returns {"status": "healthy", "checks": {"database": "healthy", "redis": "healthy"}}
✅ Frontend loads at localhost:3000 without errors
✅ No TypeScript errors
✅ No Python mypy errors
✅ alembic history shows initial migration
```

#### 🔔 STOP — Notify User:
```
🎉 PHASE 1 COMPLETE — Architecture Setup

✅ What's working:
- All services start successfully
- DB connection healthy
- Redis connection healthy
- Frontend loads

🧪 Please verify manually:
- Run: make dev
- Check: localhost:3000 loads
- Check: localhost:8000/api/v1/health returns healthy
- Check: localhost:8000/docs shows FastAPI swagger UI

🚀 Ready for Phase 2?
Type "proceed" to continue to Auth & Multi-tenancy
```

---

### 🔴 Phase 2 — Authentication & Multi-Tenancy
**Goal:** Complete auth system with roles and org isolation

#### Tasks:
- [ ] POST /api/v1/auth/signup (creates user + org + owner membership)
- [ ] POST /api/v1/auth/login (returns JWT + sets refresh cookie)
- [ ] POST /api/v1/auth/refresh (rotates refresh token)
- [ ] POST /api/v1/auth/logout (clears cookie)
- [ ] GET /api/v1/organizations/me (returns org details)
- [ ] POST /api/v1/organizations/invite (sends invite email)
- [ ] GET /api/v1/auth/invite/{token} (returns invite details)
- [ ] POST /api/v1/auth/invite/{token}/accept (joins org)
- [ ] Role-based dependency injection (require_owner, require_admin, require_analyst, require_member)
- [ ] Org isolation on all queries (every query has org_id filter)
- [ ] Frontend: Login page working
- [ ] Frontend: Signup page working
- [ ] Frontend: Auth state in Zustand
- [ ] Frontend: Protected routes redirect to login
- [ ] Frontend: Token refresh interceptor working
- [ ] Tests: Auth endpoints covered

#### Definition of Done:
```
✅ Can signup → creates user, org, owner membership
✅ Can login → gets access token + refresh cookie set
✅ Refresh token rotates on use (old one invalidated)
✅ Viewer cannot access admin endpoints (returns 403)
✅ Two orgs cannot see each other's data
✅ Invite email sent (check Resend dashboard)
✅ Invite token expires after 7 days
✅ Frontend: login/signup pages work
✅ Frontend: redirects to dashboard after login
✅ Frontend: protected routes redirect to login
✅ All auth tests pass
```

#### 🔔 STOP — Notify User:
```
🎉 PHASE 2 COMPLETE — Auth & Multi-Tenancy

✅ What's working:
[list completed items]

🧪 Please test manually:
1. Signup at localhost:3000/signup
2. Login at localhost:3000/login
3. Check refresh cookie in browser devtools
4. Try accessing protected route without login → should redirect

🚀 Ready for Phase 3?
Type "proceed" to continue to Data Ingestion
```

---

### 🔴 Phase 3 — Data Ingestion
**Goal:** Working data pipeline from API to database

#### Tasks:
- [ ] POST /api/v1/ingest/events (single event, API key auth)
- [ ] POST /api/v1/ingest/events/batch (batch events)
- [ ] POST /api/v1/ingest/csv (CSV upload, JWT auth)
- [ ] Pydantic v2 validation on all event inputs
- [ ] API key generation endpoint
- [ ] API key revocation endpoint
- [ ] API key rotation endpoint
- [ ] Rate limiting: 1000 events/min per org (Redis)
- [ ] Rate limiting: 100 events/min per API key (Redis)
- [ ] Celery task: normalize and store events
- [ ] Celery task: process CSV files
- [ ] Events stored in partitioned events table
- [ ] Frontend: API key management page
- [ ] Frontend: CSV upload UI
- [ ] Frontend: Ingestion stats display
- [ ] Tests: Ingestion endpoints + Celery tasks

#### Definition of Done:
```
✅ Can generate API key (shown once, hashed in DB)
✅ POST /ingest/events with API key stores event in DB
✅ Batch ingestion works (up to 1000 events)
✅ CSV upload triggers Celery task and processes file
✅ Rate limiting blocks after limit exceeded (returns 429)
✅ Invalid events return clear validation errors
✅ Events in DB have correct org_id
✅ Celery worker logs show event processing
✅ All ingestion tests pass
```

#### 🔔 STOP — Notify User:
```
🎉 PHASE 3 COMPLETE — Data Ingestion

✅ What's working:
[list completed items]

🧪 Please test manually:
1. Generate API key in frontend
2. curl -X POST localhost:8000/api/v1/ingest/events \
   -H "X-API-Key: YOUR_KEY" \
   -H "Content-Type: application/json" \
   -d '{"event": "page_view", "properties": {"url": "/home"}}'
3. Check DB has event record
4. Check Celery worker terminal shows processing

🚀 Ready for Phase 4?
Type "proceed" to continue to Dashboards & Widgets
```

---

### 🔴 Phase 4 — Dashboards & Widgets
**Goal:** Working dashboards with charts pulling real event data

#### Tasks:
- [ ] POST/GET/PUT/DELETE /api/v1/dashboards (CRUD)
- [ ] POST /api/v1/dashboards/{id}/share (public link)
- [ ] GET /api/v1/dashboards/shared/{token} (public view)
- [ ] POST/GET/PUT/DELETE /api/v1/widgets (CRUD)
- [ ] POST/GET/PUT/DELETE /api/v1/saved-queries (CRUD)
- [ ] Query execution engine (time series aggregation)
- [ ] Redis caching for query results (5 min TTL)
- [ ] Dashboard templates (Web Analytics, Sales, DevOps)
- [ ] Frontend: Dashboard list page
- [ ] Frontend: Dashboard view with real charts (Recharts)
- [ ] Frontend: Drag-and-drop widget placement (dnd-kit)
- [ ] Frontend: Widget editor (connect to saved query)
- [ ] Frontend: Time range selector per widget
- [ ] Frontend: Auto-refresh (30s, 1m, 5m)
- [ ] Frontend: Dashboard sharing UI
- [ ] Frontend: Full screen mode
- [ ] Frontend: Public dashboard view (no auth)
- [ ] Tests: Dashboard + widget endpoints

#### Definition of Done:
```
✅ Can create dashboard with widgets
✅ Widgets show real data from ingested events
✅ Charts render correctly (line, bar, pie, KPI, table)
✅ Drag and drop repositions widgets and saves positions
✅ Time range changes update chart data
✅ Auto-refresh polls for new data
✅ Public share link works without login
✅ Dashboard templates create pre-configured dashboards
✅ Full screen mode works
✅ All dashboard tests pass
```

#### 🔔 STOP — MAJOR MILESTONE — Notify User:
```
🎉 PHASE 4 COMPLETE — ALL MUST-HAVE FEATURES DONE!

✅ All 3 Must-Have modules working:
- Authentication & Multi-tenancy ✅
- Data Ingestion ✅
- Dashboards & Widgets ✅

🚀 THIS IS A VALID SUBMISSION POINT
You can submit now and meet the minimum requirements.

🧪 Please test the full flow:
1. Signup → creates account
2. Generate API key → ingest events
3. Create dashboard → add widgets → see charts
4. Share dashboard → open public link

📋 Before submitting:
- Update README.md
- Ensure live demo is deployed
- Clean git history

Type "deploy" to deploy to production
Type "continue" to work on Should-Have features (Alerts + WebSockets)
Type "both" to deploy AND continue
```

---

### 🟡 Phase 5 — Alerts & Notifications
**Goal:** Working alert system with notifications

#### Done Criteria:
```
✅ Can create alert rule with threshold
✅ Celery Beat evaluates alerts every minute
✅ Alert triggers when threshold breached
✅ Email notification sent via Resend
✅ Slack-compatible webhook notification sent
✅ In-app notification stored and displayed
✅ Alert history shows triggered events
✅ Can mute and snooze alerts
✅ Alert status transitions correctly
```

---

### 🟢 Phase 6 — WebSockets & Real-Time
**Goal:** Live dashboard updates

#### Done Criteria:
```
✅ WebSocket connection established with JWT auth
✅ New events push update to live dashboard
✅ Alert triggers push to connected clients
✅ Live event stream viewer shows incoming events
✅ Auto-reconnection with exponential backoff works
✅ Multiple clients can connect simultaneously
```

---

## Emergency Submission Protocol

If deadline is approaching and phases are incomplete:

```
SUBMIT whatever is 100% complete
NEVER submit partial phase
BETTER to submit 3 perfect features than 6 broken ones

Submission priority:
1. Phase 4 complete → submit (all Must Haves done)
2. Phase 3 complete → submit (2 of 3 Must Haves done)
3. Phase 2 complete → submit (architecture + auth done)
4. Phase 1 complete → submit (shows architecture skills)
```

---

## AI Handoff Protocol

### Before Switching AI:
```
1. Complete current task fully (never leave half-done)
2. Run tests: make test
3. Fix any failing tests
4. Update 12-progress.md with:
   - Current phase number
   - Completed tasks (checkboxes)
   - Exact current task being worked on
   - Next task to do
   - Any decisions made this session
   - Any blockers or issues found
   - Exact file path and function name being worked on
5. Git commit: git commit -m "chore: progress update - [description]"
6. Git push: git push origin dev
7. Tell user: "Updated progress.md and committed. Safe to switch AI."
```

### After Switching AI — Verification Questions:
```
The new AI must answer ALL of these before coding:
1. What phase are we in right now?
2. What tasks are completed in this phase?
3. What is the NEXT task to implement?
4. What file and function were being worked on last?
5. Are there any blockers or decisions pending?

If any answer is wrong → correct it before proceeding
```

---

## Self-Verification Checklist (Run Before Marking Any Task Done)

```python
# Backend task checklist
assert all_functions_have_type_hints()
assert all_async_functions_use_await()
assert no_sync_sqlalchemy_used()
assert all_queries_filter_by_org_id()
assert all_endpoints_have_error_handling()
assert no_hardcoded_values()
assert tests_written_and_passing()
assert structlog_used_not_print()
assert progress_md_updated()

# Frontend task checklist
assert no_any_typescript_types()
assert loading_states_implemented()
assert error_states_implemented()
assert no_hardcoded_api_urls()
assert responsive_design_checked()
```
