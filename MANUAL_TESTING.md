# Wexa Analytics — Manual Frontend Testing Guide
## Phases 1, 2 & 3 — Complete Edge-Case Checklist

> **How to use this guide**  
> Start the frontend dev server (`cd frontend && npm run dev`) and open [http://localhost:3000](http://localhost:3000).  
> Work through each section top-to-bottom. Every step lists the exact action, expected result, and what to look for if something is wrong.

---

## Phase 1 — Health & Infrastructure

### 1.1 Health API (curl / browser)
| Step | Action | Expected |
|------|--------|----------|
| 1 | Open browser → `http://localhost:8000/api/v1/health` | JSON: `{"status":"healthy","checks":{"database":"healthy","redis":"healthy"}}` |
| 2 | Try `POST http://localhost:8000/api/v1/health` (via curl) | `405 Method Not Allowed` |
| 3 | Hit health while logged out — no auth header | `200 OK` (health is public) |

---

## Phase 2 — Authentication & Multi-Tenancy

### 2.1 Signup — Happy Path
1. Navigate to `/signup`
2. Fill: Full Name = `Jane Smith`, Email = `jane@acme.com`, Org = `Acme Corp`, Password = `TestPass1`
3. Click **Create Account**

**Expected:**
- Redirected to `/overview` (dashboard)
- Top-left shows org name (e.g., "Acme Corp")
- User avatar / initials visible in sidebar
- No flash of login page (auth persisted immediately)

---

### 2.2 Signup — Validation Errors
| Step | Action | Expected |
|------|--------|----------|
| 1 | Submit signup with blank email | Form error: "email required" or `422` |
| 2 | Submit with `not-an-email` as email | Form error: invalid email format |
| 3 | Submit without password | Form error: password required |
| 4 | Submit without org name | Form error: org name required |
| 5 | Submit completely empty form | All fields highlighted as required |
| 6 | Submit same email twice (second signup) | Toast / error: `409 — email already registered` |

---

### 2.3 Signup — Password Eye Toggle
1. Go to `/signup`
2. Type any password
3. Click the **eye icon** on the right of the password field

**Expected:** Password characters become visible. Click again → hidden.  
Eye icon is visible and clickable (not cut off or overlapping text).

---

### 2.4 Login — Happy Path
1. Navigate to `/login`
2. Enter valid credentials from step 2.1
3. Click **Sign In**

**Expected:**
- Redirected to `/overview`
- No page flicker
- Access token stored (visible in DevTools → Application → Local Storage: key `wexa-auth`)
- `refresh_token` cookie set (httpOnly, visible in DevTools → Application → Cookies)

---

### 2.5 Login — Error Cases
| Step | Action | Expected |
|------|--------|----------|
| 1 | Wrong password for existing email | `401` — "Invalid credentials" message |
| 2 | Email that was never registered | `401` — "Invalid credentials" (same message — no user enumeration) |
| 3 | Empty password field | `422` — validation error before request |
| 4 | Empty email field | `422` — validation error before request |

---

### 2.6 Login — Password Eye Toggle
1. Go to `/login`, type any text in the password field
2. Click the eye icon

**Expected:** Password toggles between shown/hidden. Same UX as signup.

---

### 2.7 Auth Persistence — Page Reload
1. Log in successfully → land on `/overview`
2. Press **F5** (hard reload)

**Expected:**
- Page stays on `/overview` — NOT redirected to `/login`
- User name / org still visible in the UI
- No blank white flash before content appears

---

### 2.8 Auth Persistence — Manual URL Navigation
1. Log in → land on `/overview`
2. In the browser address bar, manually type `/overview` and press Enter

**Expected:** Dashboard loads directly. No redirect to login.

---

### 2.9 Back-Button Navigation
1. Log in → land on `/overview`
2. Click any sidebar link (e.g., **Ingestion**)
3. Press the browser **Back** button

**Expected:**
- Returns to `/overview`
- Dashboard content visible immediately (no blank screen, no redirect to login)
- No manual refresh needed

---

### 2.10 Auth Redirect (Already Logged In)
1. Log in → you are now on `/overview`
2. Navigate to `/login` (type it in address bar)

**Expected:**
- Automatically redirected to `/overview`
- Login page never renders/flickers (redirect happens before paint)

3. Same test for `/signup`

---

### 2.11 Root Route Smart Redirect
1. When logged in: navigate to `/`

**Expected:** Immediately redirected to `/overview`

2. Log out, then navigate to `/`

**Expected:** Redirected to `/login`

---

### 2.12 Logout
1. Log in
2. Click the logout button (sidebar or menu)
3. After logout, try pressing browser **Back** button

**Expected:**
- Redirected to `/login` after logout
- Back button does NOT return to protected dashboard (auth is cleared)
- `refresh_token` cookie deleted (check DevTools → Cookies)

---

### 2.13 Token Refresh (Session Continuity)
1. Log in (access token lasts 15 min)
2. Stay on the app for more than 15 min (or test via DevTools by modifying the stored token to an expired one)
3. Perform any authenticated action

**Expected:** Token silently refreshed using the refresh cookie. No forced logout.

---

### 2.14 Organization — View Org Settings
1. Log in as owner
2. Navigate to `/settings` (or wherever org settings live)

**Expected:**
- Org name visible
- Members list shows at least one member (the owner)
- Your role shows as **owner**

---

### 2.15 Organization — Invite Member
1. As owner, navigate to org settings
2. Click **Invite Member**
3. Enter a new email address, select role = **Viewer**
4. Submit

**Expected:**
- Success toast / `201` response
- (Invite email sent via Resend in production; in dev, retrieve token from DB)

Test invalid cases:
| Case | Input | Expected |
|------|-------|----------|
| Bad email | `not-an-email` | `422` — invalid email |
| Bad role | `superadmin` | `422` — invalid role |

---

### 2.16 RBAC — Viewer Cannot Manage Org
1. As owner, invite someone as **Viewer** and complete the accept invite flow
2. Log in as the Viewer account
3. Try to rename the org

**Expected:** `403 Forbidden` — error message shown

4. As Viewer, try to invite another member

**Expected:** `403 Forbidden`

---

### 2.17 API Keys — Create
1. Navigate to `/ingestion`
2. In the API Keys panel, click **Create New Key**
3. Enter a name, click **Create**

**Expected:**
- New key appears in the list immediately
- A banner shows the **full raw key** (starting with `wxa_`) — this is shown **only once**
- Copy-to-clipboard button present
- Key prefix visible in the list (e.g., `wxa_abc1...`)

---

### 2.18 API Keys — Raw Key Shown Once
1. Create a new API key, note the raw key shown in the banner
2. Close or dismiss the banner
3. Reload the page

**Expected:** The raw key is gone. The list shows only the `key_prefix`. There is NO way to see the raw key again.

---

### 2.19 API Keys — Revoke
1. In the API Keys list, click **Revoke** on an active key
2. Confirm the action

**Expected:**
- Key remains in the list but shows as **Inactive** / greyed out
- The `is_active` field is `false`
- Attempting to use the revoked key for ingestion returns `401`

---

### 2.20 API Keys — Rotate
1. Click **Rotate** on an active key

**Expected:**
- Old key removed from list (soft-deleted, `deleted_at` set)
- New key created with same name, shown in list
- **New raw key displayed once** in the banner

---

### 2.21 Org Isolation — Two Orgs Cannot See Each Other
1. Create Org A (sign up with email A)
2. Open an incognito window, create Org B (sign up with email B)
3. In Org A: create an API key named `org-a-key`
4. In Org B: check the API key list

**Expected:** Org B's list does NOT contain `org-a-key`.

---

## Phase 3 — Data Ingestion

### 3.1 Ingestion Stats — Initial View
1. Log in → navigate to `/ingestion`
2. Look at the stats cards at the top

**Expected:** Four cards: **Today**, **Last 7 days**, **Last 30 days**, **All Time**. All start at `0` for a fresh org.

---

### 3.2 Ingest a Single Event (via API key)
1. From the Ingestion page, copy your API key
2. In terminal:
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "X-API-Key: wxa_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"event_name": "page_view", "properties": {"url": "/home"}}'
```

**Expected:** HTTP `202`, response body has `accepted: 1` and a `batch_id` UUID.

3. Return to the browser `/ingestion` page

**Expected:** "Today" stat increments by 1 (may need to wait a few seconds for Celery to process).

---

### 3.3 Event Alias Field (`event` vs `event_name`)
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "X-API-Key: wxa_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"event": "button_click"}'
```
**Expected:** `202` — both `event` and `event_name` fields are accepted.

---

### 3.4 Ingest Without API Key
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "Content-Type: application/json" \
  -d '{"event_name": "test"}'
```
**Expected:** `401 Unauthorized`

---

### 3.5 Ingest With Invalid API Key
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "X-API-Key: wxa_fakekeynotreal" \
  -H "Content-Type: application/json" \
  -d '{"event_name": "test"}'
```
**Expected:** `401 Unauthorized`

---

### 3.6 Ingest With JWT (Should Fail)
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "Authorization: Bearer YOUR_JWT_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_name": "test"}'
```
**Expected:** `401 Unauthorized` — ingestion endpoints require API key, not JWT.

---

### 3.7 Ingest Missing Event Name
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "X-API-Key: wxa_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"properties": {"url": "/home"}}'
```
**Expected:** `422 Unprocessable Entity` with validation error.

---

### 3.8 Batch Ingestion
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events/batch \
  -H "X-API-Key: wxa_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"event_name": "click", "properties": {"btn": "buy"}},
      {"event_name": "view", "properties": {"page": "/pricing"}},
      {"event_name": "scroll", "properties": {"depth": 80}}
    ]
  }'
```
**Expected:** `202`, `accepted: 3`

---

### 3.9 Batch Too Large
Send a batch with more than 1000 events.

**Expected:** `422 Unprocessable Entity`

---

### 3.10 CSV Upload — Happy Path (UI)
1. Navigate to `/ingestion`
2. In the CSV Upload panel, drag a `.csv` file onto the drop zone  
   (Minimum valid CSV:)
   ```csv
   event_name,user_id,page
   page_view,123,/home
   button_click,456,/pricing
   ```
3. Drop the file or click to browse and select it

**Expected:**
- Upload progress or "uploading..." indicator
- On success: toast "CSV accepted — processing in background"
- An `upload_id` returned

---

### 3.11 CSV Upload — Wrong File Type
1. In the CSV Upload panel, try to upload a `.txt` or `.xlsx` file

**Expected:** `422` — "File must be a .csv file" error message shown in UI

---

### 3.12 CSV Upload — Over 10 MB
1. Create a CSV file larger than 10 MB
2. Try to upload it

**Expected:** `422` — "CSV file exceeds 10 MB limit"

---

### 3.13 CSV Upload — Viewer Cannot Upload
1. Log in as a **Viewer** role user
2. Navigate to `/ingestion`
3. Try to upload a CSV

**Expected:** `403 Forbidden` — Viewers don't have CSV upload permission  
UI should either hide the upload button for viewers or show an error message.

---

### 3.14 CSV Upload — No Auth
```bash
curl -X POST http://localhost:8000/api/v1/ingest/csv \
  -F "file=@events.csv"
```
**Expected:** `401 Unauthorized` (CSV requires JWT, not API key)

---

### 3.15 Stats Endpoint — Shape
```bash
curl http://localhost:8000/api/v1/ingest/stats \
  -H "Authorization: Bearer YOUR_JWT"
```
**Expected:**
```json
{
  "data": {
    "total_today": 3,
    "total_week": 3,
    "total_month": 3,
    "total_all_time": 3
  }
}
```

---

### 3.16 Stats Endpoint — Org Isolation
1. Org A sends 5 events
2. Log in as Org B, check stats

**Expected:** Org B stats show `0` — Org A's events are not visible.

---

### 3.17 Rate Limiting
Send 101+ events in rapid succession with the same API key:
```bash
for i in $(seq 1 105); do
  curl -s -X POST http://localhost:8000/api/v1/ingest/events \
    -H "X-API-Key: wxa_YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"event_name\": \"stress_test_$i\"}" &
done
wait
```
**Expected:** First 100 requests: `202`. Requests 101+: `429 Too Many Requests`.

---

### 3.18 Quick-Start Snippet (UI)
1. Navigate to `/ingestion`
2. Locate the curl snippet card

**Expected:**
- Code snippet shows `X-API-Key` header
- Backend URL matches `http://localhost:8000/api/v1/ingest/events`
- `event_name` and `properties` shown in the example body

---

## General UI/UX Checklist

| Check | Expected |
|-------|----------|
| Font is Inter (not Geist) throughout the whole app | Clean sans-serif — no chunky monospace in UI text |
| No horizontal scroll on any page | All pages fit viewport at 1280px+ |
| Sidebar links navigate without full-page reload | URL changes, content swaps — no blank screen |
| All protected routes (`/overview`, `/ingestion`, etc.) redirect to `/login` when not authenticated | Direct URL access while logged-out → `/login` |
| All auth routes (`/login`, `/signup`) redirect to `/overview` when already authenticated | No double-render of auth forms |
| Stats cards auto-refresh every 30s | After ingesting events, wait 30s — stats update without manual reload |

---

## Regression Checklist After Any Code Change

Run the full backend test suite:
```bash
cd backend
.venv/bin/pytest tests/ -v
```

All 69 tests must pass:
- Phase 1: 7 tests (health)
- Phase 2 Auth: 25 tests (signup/login/refresh/logout/me)
- Phase 2 Orgs: 20 tests (org mgmt + RBAC)
- Phase 2 API Keys: 15 tests (key lifecycle)
- Phase 3 Ingestion: 30 tests (events/batch/csv/stats/rate-limit)
