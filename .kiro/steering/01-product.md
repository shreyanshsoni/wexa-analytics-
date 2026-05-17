# 01-product.md — Product Definition & Requirements

---

## What We Are Building
A Real-Time Analytics & Reporting Platform for organizations to:
- Ingest data from multiple sources
- Visualize metrics through customizable dashboards
- Set up threshold-based alerts
- Generate scheduled reports
- View live data streams

Think: lightweight Mixpanel or Metabase as a SaaS product.

---

## Who Is Evaluating This
Wexa AI recruitment team evaluating for Senior Full Stack Engineer (Python) position.
Assessment duration: 360 minutes estimated.
Deadline: 2 days from receipt.

---

## Evaluation Criteria Weights
| Criteria | Weight | What They Look For |
|---|---|---|
| Python Code Quality & Architecture | 30% | Clean separation, type hints, async patterns, DI, Pythonic idioms, SOLID |
| Functionality & Completeness | 25% | All must-haves working, edge cases, error states, pipeline reliability |
| UI/UX & Frontend | 10% | Responsive, chart interactions, loading states, optimistic updates, accessibility |

**Key insight:** 30% is code quality alone. Architecture matters more than feature count.

---

## Must Have Features (Build These First — Completely)

### 1. Authentication & Multi-Tenancy
- Email/password signup and login
- Password hashing with passlib/bcrypt
- JWT access token (short-lived, 15 minutes)
- Refresh token in HTTP-only cookie (7 days)
- Organization creation during signup
- Invite-based team onboarding with email
- Role hierarchy: Owner → Admin → Analyst → Viewer
- Permission guards on all API endpoints via FastAPI Depends
- Organization-level data isolation at DB query layer (every query filtered by org_id)

### 2. Data Ingestion
- REST API endpoint for single event ingestion
- REST API endpoint for batch event ingestion
- CSV file upload support
- Webhook receiver endpoint
- Pydantic v2 schema validation for all events
- Async processing via Celery + Redis (never block API)
- Data normalization before storage
- Time-series optimized storage format
- Rate limiting per org and per API key
- API key management: generate, revoke, rotate
- API key hashed before storage (never plain text)

### 3. Dashboards & Widgets
- Create custom dashboards (CRUD)
- Drag-and-drop widget placement (dnd-kit)
- Widget types: line chart, bar chart, pie chart, KPI card, data table
- Each widget connects to a saved query
- Configurable time ranges per widget (1h, 6h, 24h, 7d, 30d, custom)
- Dashboard sharing via public read-only link
- Dashboard sharing team-only access
- Auto-refresh at 30s, 1m, 5m intervals
- Dashboard templates: Web Analytics, Sales, DevOps
- Full-screen presentation mode

---

## Should Have Features (Only After Must Haves 100% Complete)

### 4. Alerts & Notifications
- Define alert rules with metric thresholds
- Example: "Error rate > 5% for 10 minutes"
- Alert evaluation via Celery Beat (every minute)
- Notification channels: in-app, email (Resend), webhook (Slack-compatible)
- Alert history with timestamps and triggered values
- Mute alerts indefinitely
- Snooze alerts with duration
- Alert states: Active → Triggered → Resolved → Muted

### 5. Real-Time Updates
- WebSocket-powered live dashboard updates
- Real-time alert push notifications to connected clients
- Live event stream viewer (tail incoming events)
- Connection state management
- Automatic reconnection with exponential backoff

---

## Optional Features (Skip Unless Everything Else Complete)
- Google OAuth sign-in
- GraphQL API (Strawberry or Ariadne)
- OpenTelemetry instrumentation
- Custom SQL query sandbox
- Data retention policies
- Webhook delivery system with retry logs
- CI/CD pipeline (GitHub Actions)
- Load testing (Locust)
- Feature flags system

---

## What NOT To Build
- No Kubernetes
- No Docker in production (Railway handles this)
- No AWS/GCP/Azure
- No complex DevOps setup
- No mobile app
- No GraphQL (unless bonus time)

---

## Key Business Rules
1. Every piece of data belongs to exactly one organization
2. Users can belong to only one organization (in this version)
3. API keys belong to organizations not individual users
4. Public dashboard links bypass auth but are read-only
5. Viewer role cannot create or modify anything — read only
6. Owner is the only one who can delete the organization
7. Invites expire after 7 days
8. Refresh tokens are rotated on every use (old one invalidated)
9. API keys are shown only once on creation (hashed in DB)
10. Soft deletes everywhere (never hard delete user data)

---

## Success Definition
Submission is successful if:
- [ ] All 3 Must Have modules work end-to-end
- [ ] Code follows clean architecture (Routers→Services→Repositories→Models)
- [ ] All endpoints have proper error handling
- [ ] Type hints throughout Python code
- [ ] Async/await throughout
- [ ] Live demo accessible via URL
- [ ] README is complete and professional
- [ ] Git history is clean and meaningful
