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

export type AggregationType = 'count' | 'sum' | 'avg' | 'min' | 'max'
export type GroupByType = 'minute' | 'hour' | 'day' | 'week' | 'month'
export type TemplateType = 'web_analytics' | 'sales' | 'devops'

export interface QueryResultPoint {
  bucket: string
  value: number
}

export interface QueryResult {
  data: QueryResultPoint[]
  cached: boolean
  cached_at?: string
}

export interface WidgetPosition {
  x: number
  y: number
  w: number
  h: number
}

export interface Widget {
  id: string
  dashboard_id: string
  saved_query_id: string | null
  title: string
  widget_type: WidgetType
  time_range: TimeRange
  position_x: number
  position_y: number
  width: number
  height: number
  query_result?: QueryResult
  created_at: string
  updated_at: string
}

export interface DashboardListItem {
  id: string
  name: string
  description?: string
  is_public: boolean
  widget_count: number
  auto_refresh_interval?: RefreshInterval
  created_at: string
  updated_at: string
}

export interface Dashboard {
  id: string
  organization_id: string
  name: string
  description?: string
  is_public: boolean
  share_token?: string
  auto_refresh_interval?: RefreshInterval
  template_type?: TemplateType
  widgets: Widget[]
  created_at: string
  updated_at: string
}

export interface ShareResponse {
  share_url: string
  share_token: string | null
}

export interface QueryFilter {
  key: string
  operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains'
  value: string
}

export interface SavedQuery {
  id: string
  organization_id: string
  name: string
  description?: string
  query_config: {
    event_name: string
    aggregation: AggregationType
    group_by: GroupByType
    filters: QueryFilter[]
    time_range: TimeRange
  }
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
  accepted: number
  batch_id: string
  message: string
}

export interface CsvUploadResult {
  upload_id: string
  message: string
}

export interface IngestionStats {
  total_today: number
  total_week: number
  total_month: number
  total_all_time: number
}
