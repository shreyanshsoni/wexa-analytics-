# 13-api-shapes.md — Exact API Request & Response Shapes

---

## Standard Response Formats

### Success Response
```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Error Response (ALL errors follow this format)
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": [],
    "request_id": "uuid"
  }
}
```

### Paginated Response
```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "total_pages": 5
  },
  "meta": { "request_id": "uuid" }
}
```

---

## Auth Endpoints

### POST /api/v1/auth/signup
Request:
```json
{
  "email": "user@example.com",
  "password": "minimum8chars",
  "full_name": "John Doe",
  "org_name": "Acme Corp"
}
```
Response 201:
```json
{
  "data": {
    "access_token": "eyJhbGci...",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "is_active": true
    },
    "org": {
      "id": "uuid",
      "name": "Acme Corp",
      "slug": "acme-corp"
    },
    "role": "owner"
  }
}
```
Cookie set: `refresh_token` (HTTP-only)

### POST /api/v1/auth/login
Request:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
Response 200:
```json
{
  "data": {
    "access_token": "eyJhbGci...",
    "token_type": "bearer",
    "user": { "id": "uuid", "email": "...", "full_name": "..." },
    "org": { "id": "uuid", "name": "...", "slug": "..." },
    "role": "owner"
  }
}
```
Cookie set: `refresh_token` (HTTP-only, rotated)

### POST /api/v1/auth/refresh
Request: No body (reads cookie)
Response 200:
```json
{
  "data": {
    "access_token": "eyJhbGci...",
    "token_type": "bearer"
  }
}
```

### POST /api/v1/auth/logout
Request: No body
Response 200:
```json
{ "data": { "message": "Logged out successfully" } }
```
Cookie cleared: `refresh_token`

---

## Organization Endpoints

### GET /api/v1/organizations/me
Response 200:
```json
{
  "data": {
    "org": { "id": "uuid", "name": "...", "slug": "..." },
    "members": [
      {
        "id": "uuid",
        "user": { "id": "uuid", "email": "...", "full_name": "..." },
        "role": "owner",
        "joined_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### POST /api/v1/organizations/invite
Request:
```json
{
  "email": "newmember@example.com",
  "role": "analyst"
}
```
Response 201:
```json
{
  "data": {
    "message": "Invite sent successfully",
    "invite_id": "uuid",
    "expires_at": "2024-01-08T00:00:00Z"
  }
}
```

---

## API Key Endpoints

### GET /api/v1/api-keys
Response 200:
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Production Key",
      "key_prefix": "wxa_xxxx",
      "last_used_at": "2024-01-01T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z",
      "revoked_at": null
    }
  ]
}
```

### POST /api/v1/api-keys
Request:
```json
{ "name": "Production Key" }
```
Response 201:
```json
{
  "data": {
    "id": "uuid",
    "name": "Production Key",
    "key": "wxa_xxxx....",
    "key_prefix": "wxa_xxxx",
    "created_at": "2024-01-01T00:00:00Z",
    "warning": "Save this key now — it will not be shown again"
  }
}
```

---

## Ingestion Endpoints

### POST /api/v1/ingest/events
Headers: `X-API-Key: wxa_xxxx`
Request:
```json
{
  "event": "page_view",
  "timestamp": "2024-01-01T00:00:00Z",
  "properties": {
    "url": "/dashboard",
    "user_id": "user_123",
    "session_id": "sess_456"
  }
}
```
Response 202:
```json
{
  "data": {
    "status": "queued",
    "message": "Event queued for processing"
  }
}
```

### POST /api/v1/ingest/events/batch
Headers: `X-API-Key: wxa_xxxx`
Request:
```json
{
  "events": [
    { "event": "page_view", "properties": {} },
    { "event": "click", "properties": { "element": "button" } }
  ]
}
```
Response 202:
```json
{
  "data": {
    "status": "queued",
    "count": 2,
    "batch_id": "uuid"
  }
}
```

---

## Dashboard Endpoints

### GET /api/v1/dashboards
Response 200:
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Web Analytics",
      "description": "...",
      "widget_count": 5,
      "is_shared": true,
      "auto_refresh_interval": "1m",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### POST /api/v1/dashboards
Request:
```json
{
  "name": "My Dashboard",
  "description": "Optional description",
  "template_type": "web_analytics"
}
```
Response 201:
```json
{
  "data": {
    "id": "uuid",
    "name": "My Dashboard",
    "description": "...",
    "share_token": null,
    "auto_refresh_interval": null,
    "widgets": [],
    "created_at": "..."
  }
}
```

### GET /api/v1/dashboards/{id}
Response 200:
```json
{
  "data": {
    "id": "uuid",
    "name": "Web Analytics",
    "auto_refresh_interval": "1m",
    "widgets": [
      {
        "id": "uuid",
        "title": "Page Views",
        "widget_type": "line_chart",
        "time_range": "24h",
        "position": { "x": 0, "y": 0, "w": 6, "h": 4 },
        "query_result": {
          "data": [
            { "bucket": "2024-01-01T00:00:00Z", "value": 142 },
            { "bucket": "2024-01-01T01:00:00Z", "value": 98 }
          ],
          "cached": true,
          "cached_at": "2024-01-01T00:05:00Z"
        }
      }
    ]
  }
}
```

### POST /api/v1/dashboards/{id}/share
Request:
```json
{ "enabled": true }
```
Response 200:
```json
{
  "data": {
    "share_url": "https://app.wexa.ai/shared/abc123xyz",
    "share_token": "abc123xyz"
  }
}
```

---

## Widget Endpoints

### POST /api/v1/widgets
Request:
```json
{
  "dashboard_id": "uuid",
  "title": "Page Views Over Time",
  "widget_type": "line_chart",
  "saved_query_id": "uuid",
  "time_range": "24h",
  "position": { "x": 0, "y": 0, "w": 6, "h": 4 }
}
```
Response 201:
```json
{
  "data": {
    "id": "uuid",
    "title": "Page Views Over Time",
    "widget_type": "line_chart",
    "time_range": "24h",
    "position": { "x": 0, "y": 0, "w": 6, "h": 4 }
  }
}
```

---

## Saved Query Endpoints

### POST /api/v1/saved-queries
Request:
```json
{
  "name": "Page Views Per Hour",
  "event_name": "page_view",
  "aggregation": "count",
  "group_by": "hour",
  "filters": [
    { "key": "url", "operator": "eq", "value": "/home" }
  ]
}
```
Response 201:
```json
{
  "data": {
    "id": "uuid",
    "name": "Page Views Per Hour",
    "event_name": "page_view",
    "aggregation": "count",
    "group_by": "hour",
    "filters": [...]
  }
}
```

---

## TypeScript Types (Frontend)

### Shared Types (src/types/api.ts)
```typescript
export interface ApiResponse<T> {
  data: T
  meta?: {
    request_id: string
    timestamp: string
  }
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    total: number
    page: number
    per_page: number
    total_pages: number
  }
}

export interface ApiError {
  error: {
    code: string
    message: string
    details?: unknown[]
    request_id: string
  }
}

export type Role = 'owner' | 'admin' | 'analyst' | 'viewer'
export type WidgetType = 'line_chart' | 'bar_chart' | 'pie_chart' | 'kpi_card' | 'table'
export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d'
export type RefreshInterval = '30s' | '1m' | '5m'

export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
}

export interface Organization {
  id: string
  name: string
  slug: string
}

export interface Widget {
  id: string
  title: string
  widget_type: WidgetType
  time_range: TimeRange
  position: { x: number; y: number; w: number; h: number }
  query_result?: {
    data: Array<{ bucket: string; value: number }>
    cached: boolean
  }
}

export interface Dashboard {
  id: string
  name: string
  description?: string
  auto_refresh_interval?: RefreshInterval
  share_token?: string
  widgets: Widget[]
  created_at: string
  updated_at: string
}
```
