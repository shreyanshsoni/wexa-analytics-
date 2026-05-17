# 04-features.md — Feature Implementation Details

---

## Feature 1: Authentication & Multi-Tenancy

### Signup Flow
```
POST /api/v1/auth/signup
1. Validate email uniqueness
2. Hash password with bcrypt (rounds=12)
3. Create user record
4. Create organization record
5. Create Owner membership (user → org)
6. Generate JWT access token (15 min)
7. Generate refresh token (7 days, stored in DB hashed)
8. Set refresh token as HTTP-only cookie
9. Return access token in response body + user + org data
```

### Login Flow
```
POST /api/v1/auth/login
1. Find user by email
2. Verify bcrypt password
3. Generate new JWT access token
4. Rotate refresh token (invalidate old, create new)
5. Set new refresh token as HTTP-only cookie
6. Return access token in response body
```

### Token Refresh Flow
```
POST /api/v1/auth/refresh
1. Read refresh token from HTTP-only cookie
2. Find refresh token in DB (must not be expired or revoked)
3. Verify token hash matches
4. Generate new access token
5. Rotate refresh token (invalidate old, create new)
6. Set new cookie
7. Return new access token
```

### Invite Flow
```
POST /api/v1/organizations/invite
1. Owner or Admin sends invite with email + role
2. Generate secure random invite token
3. Store invite: token_hash, email, role, org_id, expires_at (+7 days)
4. Send email via Resend with invite link
5. Link format: {FRONTEND_URL}/invite/{raw_token}

GET /api/v1/auth/invite/{token}
1. Validate token (not expired, not used)
2. Return invite details (org name, role, inviter name)

POST /api/v1/auth/invite/{token}/accept
1. Validate token
2. Create user account (or link existing)
3. Create membership with invited role
4. Mark invite as used
5. Return JWT tokens
```

### Role Hierarchy
```
Owner    → full control, can delete org, can manage all members
Admin    → can manage members (except owner), manage API keys, full data access
Analyst  → can create/edit dashboards, alerts, reports, ingest data
Viewer   → read-only access to dashboards and reports only
```

---

## Feature 2: Data Ingestion

### Single Event Ingestion
```
POST /api/v1/ingest/events
Headers: X-API-Key: {api_key}

1. Validate API key (hash incoming key, lookup in DB)
2. Check rate limit: 1000 events/min per org (Redis counter)
3. Check rate limit: 100 events/min per API key (Redis counter)
4. Validate event schema (Pydantic)
5. Drop to Celery queue immediately
6. Return 202 Accepted
```

### Batch Event Ingestion
```
POST /api/v1/ingest/events/batch
Headers: X-API-Key: {api_key}
Body: { events: [...] } max 1000 events per batch

1. Validate API key
2. Check rate limits
3. Validate each event schema
4. Drop entire batch to single Celery task
5. Return 202 Accepted with batch_id
```

### CSV Upload
```
POST /api/v1/ingest/csv
Headers: Authorization: Bearer {jwt}
Body: multipart/form-data with file

1. Validate JWT (must be Analyst or above)
2. Validate file: must be .csv, max 10MB
3. Save file temporarily
4. Drop Celery task with file path
5. Return 202 Accepted with upload_id
6. Celery task: parse CSV, validate each row, normalize, store
```

### Webhook Receiver
```
POST /api/v1/ingest/webhook/{webhook_id}
1. Lookup webhook config by webhook_id
2. Validate webhook signature (HMAC-SHA256)
3. Parse payload
4. Normalize to standard event format
5. Drop to Celery queue
6. Return 200 OK immediately
```

### Event Normalization (Celery Task)
```
Raw event structure (what comes in):
{
  "event": "page_view",
  "timestamp": "2024-01-01T00:00:00Z",  ← optional, defaults to now
  "properties": {
    "url": "/dashboard",
    "user_id": "user_123",
    ...any key-value pairs
  }
}

Normalized structure (what gets stored):
{
  "id": uuid,
  "org_id": uuid,
  "event_name": "page_view",
  "timestamp": datetime,
  "properties": {...},   ← JSONB column
  "source": "api|csv|webhook",
  "created_at": datetime
}
```

### API Key Management
```
API Key Generation:
1. Generate cryptographically secure random string (32 bytes)
2. Format: "wxa_{base64url_encoded_bytes}"
3. Hash with SHA-256 before storing in DB
4. Return raw key ONCE to user (never again)
5. Store: key_hash, key_prefix (first 8 chars for display), name, org_id

API Key Validation (on every ingest request):
1. Extract from X-API-Key header
2. Hash with SHA-256
3. Lookup hash in DB
4. Check: not revoked, org matches
5. Update last_used_at timestamp

API Key Revocation:
POST /api/v1/api-keys/{id}/revoke
- Set revoked_at timestamp
- All future requests with this key: 401

API Key Rotation:
POST /api/v1/api-keys/{id}/rotate
- Generate new key
- Revoke old key
- Return new raw key once
```

---

## Feature 3: Dashboards & Widgets

### Saved Query Structure
```python
{
  "id": uuid,
  "org_id": uuid,
  "name": "Page Views Over Time",
  "event_name": "page_view",          ← filter by event name
  "aggregation": "count|sum|avg|min|max",
  "group_by": "hour|day|week|month",  ← time bucket
  "filters": [                         ← additional property filters
    {"key": "properties->>'url'", "operator": "eq", "value": "/home"}
  ],
  "time_range": "1h|6h|24h|7d|30d"   ← default time range
}
```

### Query Execution
```sql
-- Example: count page_views per hour for last 24 hours
SELECT
  date_trunc('hour', timestamp) as bucket,
  COUNT(*) as value
FROM events
WHERE org_id = :org_id
  AND event_name = 'page_view'
  AND timestamp >= NOW() - INTERVAL '24 hours'
  AND deleted_at IS NULL
GROUP BY bucket
ORDER BY bucket ASC
```

### Widget Position Storage
```python
# Widget position stored as JSON in widget table
{
  "x": 0,        ← grid column (0-11)
  "y": 0,        ← grid row
  "w": 6,        ← width in columns
  "h": 4         ← height in rows
}
```

### Dashboard Sharing
```
Team-only sharing:
- Default for all dashboards
- Requires valid JWT with org membership

Public link sharing:
POST /api/v1/dashboards/{id}/share
- Generate unique share_token (random 32 bytes, base64url)
- Store share_token in dashboard record
- Public URL: {FRONTEND_URL}/shared/{share_token}

GET /api/v1/dashboards/shared/{share_token}
- No auth required
- Returns dashboard + widgets + query results
- Read-only (no editing)
```

### Auto-Refresh Implementation
```typescript
// Frontend: polling-based auto refresh
const intervals = {
  '30s': 30000,
  '1m': 60000,
  '5m': 300000,
}

useEffect(() => {
  if (!autoRefresh) return
  const timer = setInterval(() => {
    queryClient.invalidateQueries(['dashboard', id])
  }, intervals[refreshInterval])
  return () => clearInterval(timer)
}, [autoRefresh, refreshInterval])
```

### Dashboard Templates
```
Web Analytics Template:
- Page views over time (line chart)
- Unique visitors (KPI card)
- Top pages (table)
- Traffic sources (pie chart)
- Bounce rate (KPI card)

Sales Template:
- Revenue over time (bar chart)
- Total revenue (KPI card)
- Conversion rate (KPI card)
- Top products (table)
- Revenue by region (pie chart)

DevOps Template:
- Error rate over time (line chart)
- P99 latency (KPI card)
- Request volume (KPI card)
- Error breakdown (pie chart)
- Slowest endpoints (table)
```

---

## Feature 4: Alerts (Should Have)

### Alert Rule Definition
```python
{
  "id": uuid,
  "org_id": uuid,
  "name": "High Error Rate",
  "saved_query_id": uuid,    ← query to evaluate
  "condition": "gt|lt|gte|lte|eq",
  "threshold": 5.0,
  "duration_minutes": 10,    ← must be true for this long
  "status": "active|triggered|resolved|muted",
  "muted_until": datetime,   ← null if not muted
  "notification_channels": ["email", "webhook", "in_app"]
}
```

### Alert State Machine
```
Active → Triggered (threshold breached for duration_minutes)
Triggered → Resolved (threshold no longer breached)
Active → Muted (user mutes it)
Muted → Active (mute expires or user unmutes)
```

### Slack Webhook Payload Format
```json
{
  "text": "🚨 Alert Triggered: High Error Rate",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Alert:* High Error Rate\n*Value:* 7.2%\n*Threshold:* 5%\n*Organization:* Acme Corp"
      }
    }
  ]
}
```

---

## Feature 5: WebSockets (Should Have)

### WebSocket Connection
```
URL: ws://localhost:8000/api/v1/ws/{org_id}
Auth: JWT passed as query param ?token={jwt}
```

### Event Types (Server → Client)
```json
{ "type": "new_event", "data": { event object } }
{ "type": "alert_triggered", "data": { alert object } }
{ "type": "dashboard_update", "data": { "dashboard_id": uuid } }
{ "type": "ping", "data": {} }
```

### Reconnection Strategy (Frontend)
```typescript
const MAX_RETRIES = 5
const BASE_DELAY = 1000  // 1 second
// Exponential backoff: 1s, 2s, 4s, 8s, 16s
delay = BASE_DELAY * Math.pow(2, retryCount)
```
