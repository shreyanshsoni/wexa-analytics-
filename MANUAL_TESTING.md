# Wexa Analytics — Complete Manual Testing Guide
## Phases 1 → 4 with Edge Cases & Expected Results

> **Setup:** Backend on `localhost:8000`, frontend on `localhost:3000`.  
> Have a terminal open for curl commands. Replace `wxa_YOUR_KEY` with a real API key from the Ingestion page.

---

## Phase 1 — Health & Infrastructure

### 1.1 Health Check
| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `http://localhost:8000/api/v1/health` in browser | `{"status":"healthy","checks":{"database":"healthy","redis":"healthy"}}` |
| 2 | `POST http://localhost:8000/api/v1/health` via curl | `405 Method Not Allowed` |
| 3 | Hit health while logged out (no auth header) | `200 OK` — health is always public |

### 1.2 API Docs
| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `http://localhost:8000/docs` | FastAPI Swagger UI loads with all endpoints listed |

---

## Phase 2 — Authentication & Multi-Tenancy

### 2.1 Signup — Happy Path
1. Navigate to `/signup`
2. Fill: Full Name = `Jane Smith`, Email = `jane@acme.com`, Org = `Acme Corp`, Password = `TestPass1`
3. Click **Create Account**

**Expected:**
- Redirected to `/overview`
- Sidebar shows org name "Acme Corp"
- No flash of login page (auth persisted immediately)

---

### 2.2 Signup — Validation Errors
| Step | Action | Expected |
|------|--------|----------|
| 1 | Submit with blank email | Form error: email required |
| 2 | Submit with `not-an-email` | Form error: invalid email format |
| 3 | Submit without password | `422` validation error |
| 4 | Submit without org name | `422` validation error |
| 5 | Submit same email a second time | Toast / error: `409 — email already registered` |
| 6 | Password without uppercase | `422` — "must contain at least one uppercase letter" |
| 7 | Password without digit | `422` — "must contain at least one digit" |

---

### 2.3 Password Eye Toggle (Signup & Login)
1. Go to `/signup` → type any password → click the **eye icon**
**Expected:** Password characters become visible. Click again → hidden.

---

### 2.4 Login — Happy Path
1. Navigate to `/login` → enter valid credentials → click **Sign In**

**Expected:**
- Redirected to `/overview`
- Access token in DevTools → Application → Local Storage (`wexa-auth`)
- `refresh_token` cookie set (httpOnly, visible in DevTools → Cookies)

---

### 2.5 Login — Error Cases
| Step | Action | Expected |
|------|--------|----------|
| 1 | Wrong password | `401` — "Invalid email or password" |
| 2 | Email never registered | `401` — "Invalid email or password" (no user enumeration) |
| 3 | Empty email | `422` validation error |
| 4 | Empty password | `422` validation error |

---

### 2.6 Auth Persistence — Page Reload
1. Log in → land on `/overview`
2. Press **F5** (hard reload)

**Expected:** Stays on `/overview`, not redirected to login. User/org still visible.

---

### 2.7 Auth Redirect (Already Logged In)
1. While logged in, navigate to `/login` or `/signup`
**Expected:** Automatically redirected to `/overview`. Auth pages never render.

---

### 2.8 Root Route Smart Redirect
- Logged in → navigate to `/` → **Expected:** Redirected to `/overview`
- Logged out → navigate to `/` → **Expected:** Redirected to `/login`

---

### 2.9 Logout
1. Click **Sign out** in the sidebar
2. After logout, press browser **Back** button

**Expected:**
- Redirected to `/login`
- Back button does NOT return to dashboard
- `refresh_token` cookie deleted

---

### 2.10 Token Refresh (Session Continuity)
1. Log in. In DevTools → Application → Local Storage → `wexa-auth`, corrupt the `access_token` value (edit it to be invalid)
2. Perform any action (navigate to a tab)

**Expected:** Token silently refreshed using the refresh cookie. No forced logout, no error shown.

---

### 2.11 Token Fully Expired (Both Tokens Dead)
1. Log in → corrupt the access token (as above)
2. Also clear the `refresh_token` cookie in DevTools
3. Try to navigate to any protected page

**Expected:** Redirected to `/login`. No infinite redirect loop.

---

### 2.12 Settings — View Org Info
1. Log in as owner → navigate to `/settings`

**Expected:**
- "Organization" card shows current org name + slug (read-only)
- "Invite Member" card visible (owner/admin only)
- "Team Members" card shows you with **owner** badge (amber color)
- Member count shown (e.g. "1 member")

---

### 2.13 Settings — Rename Organization
1. In the Organization card, change name to "My Renamed Org" → click **Save**

**Expected:** Toast "Organization name updated". Input reflects new name. Slug unchanged.

2. Clear the name field completely → try to click Save

**Expected:** Save button is disabled.

---

### 2.14 Settings — Invite a New Member (Email Never Used)
1. As owner → Settings → Invite Member card
2. Enter a **new email** → select role **Viewer** → click **Send invite**

**Expected:** Toast "Invite sent successfully". Email field clears.

3. The invited person receives an email from `Wexa Analytics <onboarding@resend.dev>` with:
   - Subject: "You've been invited to join {OrgName} on Wexa Analytics"
   - Blue "Accept Invitation" button linking to `http://localhost:3000/invite/{token}`
   - Raw URL shown at the bottom of the email

---

### 2.15 Accept Invite — New User (No Existing Account)
1. Invited person opens `http://localhost:3000/invite/{token}` (incognito window)

**Expected:**
- Page shows **"Accept your invite"** heading
- Their email shown in a disabled (greyed) field — cannot be changed
- **Full name** input (required)
- **Password** input with eye toggle, labeled "Choose a password"
- Button: **"Join organization"**

2. Fill in Full Name + strong password → click Join organization

**Expected:**
- Toast "Welcome to {OrgName}!"
- Redirected to `/overview` — logged in as new user with Viewer role

---

### 2.16 Accept Invite — Existing User (Re-invited After Removal)
1. Owner removes a member from Settings
2. Owner re-invites the same email
3. Removed member opens the new invite link in incognito

**Expected:**
- Page shows **"Rejoin organization"** heading
- Their email shown in a disabled field
- **No "Full name" field** (they already have a name)
- Password input labeled **"Your existing password"**
- Button: **"Confirm & rejoin"**

4. Enter their **existing password** → click Confirm & rejoin

**Expected:** Toast "Welcome to {OrgName}!" → redirected to `/overview` → logged in

5. Enter the **wrong password** → click Confirm & rejoin

**Expected:** Error toast "Incorrect password for existing account"

---

### 2.17 Login After Removal (Edge Case — No Org)
1. Remove a member from the org (but do NOT re-invite them yet)
2. That user tries to log in on `/login` with correct credentials

**Expected:**
- Login fails with message: "Your account is not part of any organization. Please use an invitation link sent to your email to join one."
- They are NOT logged in — must accept a re-invite to regain access

---

### 2.18 Invite — Invalid Token
1. Navigate to `http://localhost:3000/invite/totally-fake-token`

**Expected:** "Invite not found" card with message "This invite link is invalid or has expired."

---

### 2.19 Invite — Already Used Token
1. Accept an invite successfully
2. Try opening the same invite URL again

**Expected:** "Invite not found" — token is single-use

---

### 2.20 RBAC — Viewer Cannot Manage Org
1. Log in as a Viewer → navigate to `/settings`

**Expected:**
- "Invite Member" card is completely **hidden**
- Org name input is **disabled** (greyed out, cannot type)
- Save button is **hidden**
- Members list visible but **read-only** — no trash icons

---

### 2.21 Settings — Remove Member
1. As owner → Settings → click trash icon next to a non-owner member

**Expected:** Toast "Member removed". Member disappears from list.

**Verify no trash icon on:**
- Owner row
- Your own row

---

### 2.22 API Keys — Create
1. Navigate to `/ingestion`
2. In the API Keys panel → click **Create New Key** → enter a name → Create

**Expected:**
- Key appears in list
- Banner shows **full raw key** starting with `wxa_` — shown only once
- Copy-to-clipboard button present
- List shows key prefix (e.g. `wxa_abc1...`) and name

---

### 2.23 API Keys — Raw Key Shown Once
1. Create key → note raw key → dismiss banner → reload page

**Expected:** Raw key is gone. Only prefix visible. No way to retrieve it again.

---

### 2.24 API Keys — Revoke
1. Click **Revoke** on an active key → confirm

**Expected:** Key shows as inactive. Using revoked key for ingestion → `401 Unauthorized`.

---

### 2.25 API Keys — Rotate
1. Click **Rotate** on a key

**Expected:** Old key deleted. New key created with same name. New raw key shown once.

---

### 2.26 Org Isolation
1. Create Org A (sign up with Email A)
2. Open incognito → create Org B (sign up with Email B)
3. In Org A: create API key named `org-a-key`
4. In Org B: check API key list

**Expected:** Org B does NOT see `org-a-key`.

---

## Phase 3 — Data Ingestion

### 3.1 Ingest Test Data (Run First — Gives Charts Real Data)
```bash
API_KEY="wxa_YOUR_KEY_HERE"

for i in $(seq 1 20); do
  curl -s -X POST http://localhost:8000/api/v1/ingest/events \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"event_name\": \"page_view\", \"properties\": {\"url\": \"/page$i\"}}" > /dev/null
done

for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8000/api/v1/ingest/events \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"event_name\": \"button_click\", \"properties\": {\"btn\": \"buy\"}}" > /dev/null
done

for i in $(seq 1 5); do
  curl -s -X POST http://localhost:8000/api/v1/ingest/events \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"event_name\": \"purchase\", \"properties\": {\"amount\": $((i * 10))}}" > /dev/null
done

echo "Done — 35 events ingested"
```
**Expected:** All return `202`. After ~5 seconds (Celery), stats on `/ingestion` show 35 in Today count.

---

### 3.2 Ingest Single Event
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "X-API-Key: wxa_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"event_name": "page_view", "properties": {"url": "/home"}}'
```
**Expected:** `202`, body has `accepted: 1` and a `batch_id` UUID.

---

### 3.3 Event Field Alias (`event` vs `event_name`)
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "X-API-Key: wxa_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"event": "button_click"}'
```
**Expected:** `202` — both `event` and `event_name` field names accepted.

---

### 3.4 Ingest Without API Key
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "Content-Type: application/json" \
  -d '{"event_name": "test"}'
```
**Expected:** `401 Unauthorized`

---

### 3.5 Ingest With JWT (Not API Key)
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_name": "test"}'
```
**Expected:** `401` — ingestion requires API key, not JWT.

---

### 3.6 Ingest Missing Event Name
```bash
curl -X POST http://localhost:8000/api/v1/ingest/events \
  -H "X-API-Key: wxa_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"properties": {"url": "/home"}}'
```
**Expected:** `422 Unprocessable Entity`

---

### 3.7 Batch Ingestion
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

### 3.8 Batch Too Large (>1000 events)
**Expected:** `422 Unprocessable Entity`

---

### 3.9 CSV Upload — Happy Path
1. Create `test_events.csv`:
```csv
event_name,user_id,page
page_view,user_1,/home
button_click,user_2,/pricing
sign_up,user_3,/signup
```
2. Go to `/ingestion` → drag file onto the CSV drop zone

**Expected:**
- Filename shown in drop zone
- Upload button appears bottom-right
3. Click **Upload**
**Expected:** Spinner while uploading → drop zone resets to empty → toast "CSV accepted" → stats increment

---

### 3.10 CSV Upload — Upload Again Without Reload
1. Immediately after a successful upload (no page reload), drag another CSV file

**Expected:** Works immediately — no page reload needed. Second file selects cleanly.

---

### 3.11 CSV Upload — Wrong File Type
1. Drag a `.txt` or `.xlsx` file onto the CSV drop zone

**Expected:** Error toast or rejected — drop zone stays empty.

---

### 3.12 Ingestion Stats — Org Isolation
1. Org A ingests 5 events
2. Log in as Org B → check stats

**Expected:** Org B stats show `0`. Org A events not visible.

---

### 3.13 Rate Limiting (per API key: 100/min)
```bash
for i in $(seq 1 105); do
  curl -s -X POST http://localhost:8000/api/v1/ingest/events \
    -H "X-API-Key: wxa_YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"event_name\": \"stress_$i\"}" &
done; wait
```
**Expected:** First 100 → `202`. Requests 101+ → `429 Too Many Requests`.

---

## Phase 4 — Dashboards & Widgets

### 4.1 Overview — Empty State
1. Fresh account → navigate to `/overview`

**Expected:** Dashed box with chart icon, "No dashboards yet", "Create your first dashboard" text, **New Dashboard** button in both the empty state and the top-right header.

---

### 4.2 Create Blank Dashboard
1. Click **New Dashboard** → name "My First Dashboard" → leave template as **Blank** → Create

**Expected:** Toast "Dashboard created" → redirected to `/dashboards/{id}` → empty widget state with "No widgets yet. Click Edit then Add widget to get started."

---

### 4.3 Create Template — Web Analytics
1. New Dashboard → name "Analytics" → select **Web Analytics** → Create

**Expected:** Redirected to dashboard with **5 pre-built widgets**: "Page Views Over Time", "Total Visitors", "Sign Ups", "Button Clicks by Day", "Event Breakdown". Charts show real data if 3.1 was run.

---

### 4.4 Create Template — Sales
1. New Dashboard → **Sales** template → Create

**Expected:** **4 widgets**: Purchases Over Time, Total Purchases, Checkouts, Daily Sales.

---

### 4.5 Create Template — DevOps
1. New Dashboard → **DevOps** template → Create

**Expected:** **5 widgets**: Error Rate Over Time, Total Errors, Requests, Request Volume, Error Breakdown.

---

### 4.6 Dashboard List — Card Content
1. Go to `/overview` with multiple dashboards created

**Expected:** Each card shows: name, lock (private) or globe (public) icon, widget count ("5 widgets" / "1 widget"), last updated date. Cards are clickable.

---

### 4.7 Sidebar — Dashboards Link Active State
1. Open a dashboard at `/dashboards/{id}`

**Expected:** "Dashboards" in the sidebar is **highlighted/active** (not just on `/overview`).

---

### 4.8 Enter Edit Mode
1. Open any dashboard → click **Edit**

**Expected:** Button turns solid, shows "Done". **Add widget** button appears. Each widget card shows **⋯** menu icon.

2. Click **Done**

**Expected:** ⋯ menus gone, "Add widget" gone, widgets not draggable.

---

### 4.9 Add Widget — Existing Query
1. In edit mode → **Add widget**
2. Enter title → Chart type: **Line chart** → Time range: **Last 24 hours** → Existing query tab → pick a query → **Add Widget**

**Expected:** Toast "Widget added" → widget appears in grid.

---

### 4.10 Add Widget — New Query
1. Add widget → switch to **New query** tab
2. Fill: title "Click Chart", Event name `button_click`, Aggregation **Count**, Group by **Hour** → Add Widget

**Expected:** Toast "Widget added" → widget rendered. That saved query now also appears in the "Existing query" dropdown on next Add Widget.

---

### 4.11 Add Widget — Disabled States
| Case | Expected |
|------|----------|
| Title empty | Add Widget button disabled |
| Existing query tab, no queries exist | Add Widget button disabled |
| New query tab, event name empty | Add Widget button disabled |

---

### 4.12 All 5 Chart Types Render
| Type | Expected |
|------|----------|
| Line chart | Smooth line, X=time, Y=count |
| Bar chart | Vertical bars per bucket |
| Pie chart | Slices with legend |
| KPI card | Large total number + % change |
| Table | 2-column sticky-header, scrollable |
| Any type with no data | Centered "No data" message — no crash |

---

### 4.13 Redis Cache Badge
1. Open a dashboard with widgets
2. Reload the page within 5 minutes

**Expected:** Widget titles show **(cached)** on second load — confirming Redis cache hit.

---

### 4.14 Edit a Widget
1. Edit mode → ⋯ on a widget → **Edit** → change title + chart type → **Update**

**Expected:** Toast "Widget updated". Title and chart type change immediately.

---

### 4.15 Delete a Widget
1. Edit mode → ⋯ → **Delete**

**Expected:** Widget removed, toast "Widget deleted". If last widget → empty state shows.

---

### 4.16 Drag and Drop — Reorder
1. Enter edit mode → hover a widget → cursor becomes grab hand ✋
2. Drag widget over another position → drop

**Expected:** Widgets reorder. Dragged widget shows 50% opacity while dragging. Order persists after page refresh.

---

### 4.17 Drag Disabled in View Mode
1. Without clicking Edit, try to drag a widget

**Expected:** Nothing moves. Normal cursor.

---

### 4.18 Share Dashboard
1. On a private dashboard → click **Share**

**Expected:** Toast "Share link copied to clipboard". Button changes to **"Copy link"**. Globe icon appears on overview card.

---

### 4.19 Public Shared Page — Logged Out
1. Copy the share link → open in incognito → paste URL

**Expected:** Page loads without login. Shows dashboard name, all widgets read-only. Top-right shows "Read-only · Wexa Analytics". No Edit/Share/Add widget controls.

---

### 4.20 Invalid / Revoked Share Token
1. Navigate to `http://localhost:3000/shared/fake-token-xyz`

**Expected:** "Dashboard not found" error page with helpful message.

2. Unshare a dashboard → try the old link in incognito

**Expected:** Same "Dashboard not found" error.

---

### 4.21 Fullscreen Mode
1. Click the maximize icon (⬜) in toolbar

**Expected:** Dashboard fills entire screen. Minimize icon appears.

2. Click minimize or press Escape

**Expected:** Returns to normal layout.

---

### 4.22 Page Reload Persists Everything
1. Add widgets → drag to reorder → hard refresh (`Cmd+Shift+R`)

**Expected:** All widgets present, in the same order, data re-fetched.

---

## End-to-End Golden Path

The complete flow — run this in order to verify everything works together:

| Step | Action | Expected |
|------|--------|----------|
| 1 | Sign up with a new email + org | Lands on `/overview` |
| 2 | Go to `/ingestion` → create API key | Raw key shown once |
| 3 | Run 3.1 bulk ingest (35 events) | Stats show 35 today |
| 4 | New Dashboard → Web Analytics template | 5 widgets with real data |
| 5 | Reload page within 5 min | "(cached)" badge on widgets |
| 6 | Edit mode → drag to reorder | Widgets reorder, persists on reload |
| 7 | Add widget → new query → `page_view` count → line chart | Chart shows data |
| 8 | Click **Share** | Toast "link copied" |
| 9 | Open share link in incognito | Read-only dashboard visible |
| 10 | Go to `/settings` → rename org | Toast success |
| 11 | Invite a new email as Viewer | Toast "Invite sent", email received |
| 12 | Invited person opens link → fills name + password | "Welcome!" toast → lands on `/overview` as Viewer |
| 13 | As owner → Settings → remove that member | Member removed from list |
| 14 | Removed member tries to login | Error: "not part of any organization" |
| 15 | Owner re-invites same email | New invite email received |
| 16 | Removed member opens new invite link | Shows "Rejoin organization" form (no name field) |
| 17 | Enters existing password → Confirm & rejoin | Welcome toast → logged in |
| 18 | Log out → try share link in incognito | Still works (still public) |
| 19 | Unshare the dashboard | Button reverts to "Share" |
| 20 | Try old share link in incognito | "Dashboard not found" |

---

## Known Limitations (Not Bugs)

| Item | Note |
|------|------|
| Resend `onboarding@resend.dev` FROM address | Can only deliver to the email registered on your Resend account unless a custom domain is verified |
| Auto-refresh (30s/1m/5m) | Only activates if `auto_refresh_interval` is set on the dashboard (not set by default via UI) |
| WebSocket real-time | Phase 6 — not built yet. Dashboard updates require manual refresh or auto-refresh polling |
| Alerts | Phase 5 — not built yet |
