export interface ApiResponse<T> {
  data: T
  meta?: {
    request_id: string
    timestamp: string
  }
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    total: number
    page: number
    per_page: number
    total_pages: number
  }
  meta?: { request_id: string; timestamp: string }
}

export interface ApiError {
  error: {
    code: string
    message: string
    details?: unknown[]
    request_id?: string
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
  created_at: string
  updated_at: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  created_at: string
  updated_at: string
}

export interface MemberUser {
  id: string
  email: string
  full_name: string
}

export interface Member {
  id: string
  user: MemberUser
  role: Role
  joined_at: string
}

export interface OrgMe {
  org: Organization
  members: Member[]
}

export interface AuthData {
  access_token: string
  token_type: string
  user: User
  org: Organization
  role: Role
}

export interface TokenData {
  access_token: string
  token_type: string
}

export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  is_active: boolean
  last_used_at: string | null
  created_at: string
}

export interface ApiKeyCreated extends ApiKey {
  key: string
  warning: string
}

export interface Invite {
  invite_id: string
  message: string
  expires_at: string
}

export interface Widget {
  id: string
  title: string
  widget_type: WidgetType
  time_range: TimeRange
  position: { x: number; y: number; w: number; h: number }
  config: Record<string, unknown>
  query_result?: {
    data: Array<{ bucket: string; value: number }>
    cached: boolean
    cached_at?: string
  }
}

export interface Dashboard {
  id: string
  name: string
  description?: string
  is_public: boolean
  share_token?: string
  refresh_interval?: RefreshInterval
  widget_count?: number
  widgets?: Widget[]
  created_at: string
  updated_at: string
}

export interface SavedQuery {
  id: string
  name: string
  description?: string
  query_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface Alert {
  id: string
  name: string
  description?: string
  status: 'active' | 'triggered' | 'resolved' | 'muted'
  condition: Record<string, unknown>
  notification_channels: Record<string, unknown>[]
  muted_until?: string
  created_at: string
  updated_at: string
}

export interface HealthCheck {
  status: 'healthy' | 'unhealthy'
  checks: {
    database: 'healthy' | 'unhealthy'
    redis: 'healthy' | 'unhealthy'
  }
}

export interface IngestResult {
  status: string
  message?: string
  count?: number
  batch_id?: string
}
