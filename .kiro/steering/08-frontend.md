# 08-frontend.md — Frontend Implementation Details

---

## Next.js App Router Structure

### Route Groups
```
(auth)    → public routes, no sidebar, no auth required
(dashboard) → protected routes, with sidebar, auth required
```

### Protected Route Implementation
```typescript
// src/app/(dashboard)/layout.tsx
import { redirect } from 'next/navigation'
import { getServerSession } from '@/lib/auth'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await getServerSession()
  if (!session) redirect('/login')

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
```

### Loading & Error Boundaries (Every Route)
```typescript
// src/app/(dashboard)/dashboards/loading.tsx
export default function Loading() {
  return <DashboardSkeleton />
}

// src/app/(dashboard)/dashboards/error.tsx
'use client'
export default function Error({
  error,
  reset,
}: {
  error: Error
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full">
      <p className="text-destructive">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  )
}
```

---

## Zustand Store Structure

### Auth Store
```typescript
// src/store/authStore.ts
interface AuthState {
  user: User | null
  org: Organization | null
  role: Role | null
  accessToken: string | null
  isLoading: boolean

  setAuth: (user: User, org: Organization, role: Role, token: string) => void
  setToken: (token: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  org: null,
  role: null,
  accessToken: null,
  isLoading: true,

  setAuth: (user, org, role, token) => set({ user, org, role, accessToken: token }),
  setToken: (token) => set({ accessToken: token }),
  clearAuth: () => set({ user: null, org: null, role: null, accessToken: null }),
}))
```

### Dashboard Store (UI State Only)
```typescript
// src/store/dashboardStore.ts
interface DashboardState {
  isEditMode: boolean
  selectedWidgetId: string | null
  isFullscreen: boolean

  setEditMode: (mode: boolean) => void
  setSelectedWidget: (id: string | null) => void
  setFullscreen: (value: boolean) => void
}

// NOTE: Dashboard DATA lives in TanStack Query cache, not Zustand
// Zustand = UI state only (edit mode, selected widget, etc.)
// TanStack Query = server data (dashboard data, widget data, etc.)
```

---

## TanStack Query v5 Patterns

### API Client Setup
```typescript
// src/lib/api.ts
import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  withCredentials: true,    // REQUIRED for refresh token cookie
})

// Request interceptor — attach access token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor — handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      try {
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
          {},
          { withCredentials: true }
        )
        useAuthStore.getState().setToken(data.access_token)
        // Retry original request
        return api(error.config)
      } catch {
        useAuthStore.getState().clearAuth()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
```

### Query Patterns (TanStack Query v5)
```typescript
// src/hooks/useDashboard.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

// ✅ CORRECT — v5 syntax
export function useDashboard(id: string) {
  return useQuery({
    queryKey: ['dashboard', id],
    queryFn: () => api.get(`/api/v1/dashboards/${id}`).then(r => r.data),
    staleTime: 5 * 60 * 1000,    // 5 minutes
  })
}

export function useCreateDashboard() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateDashboardInput) =>
      api.post('/api/v1/dashboards', data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboards'] })
    },
  })
}

// ❌ WRONG — v4 syntax (DO NOT USE)
useQuery(['dashboard', id], fetchFn)
useMutation(mutationFn, { onSuccess: ... })
```

### Optimistic Updates Pattern
```typescript
export function useUpdateWidget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWidgetInput }) =>
      api.put(`/api/v1/widgets/${id}`, data).then(r => r.data),

    // Optimistic update — update UI before server responds
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: ['dashboard'] })
      const previous = queryClient.getQueryData(['dashboard', data.dashboardId])

      queryClient.setQueryData(['dashboard', data.dashboardId], (old: any) => ({
        ...old,
        widgets: old.widgets.map((w: any) =>
          w.id === id ? { ...w, ...data } : w
        ),
      }))

      return { previous }
    },

    // Rollback on error
    onError: (err, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          ['dashboard', variables.data.dashboardId],
          context.previous
        )
      }
    },

    // Refetch after success or error
    onSettled: (data, error, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['dashboard', variables.data.dashboardId]
      })
    },
  })
}
```

---

## Chart Implementations (Recharts)

### Line Chart Widget
```typescript
// src/components/charts/LineChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface LineChartWidgetProps {
  data: Array<{ bucket: string; value: number }>
  title: string
}

export function LineChartWidget({ data, title }: LineChartWidgetProps) {
  return (
    <div className="h-full w-full">
      <h3 className="text-sm font-medium text-muted-foreground mb-2">{title}</h3>
      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

### KPI Card Widget
```typescript
// src/components/charts/KPICard.tsx
export function KPICard({ title, value, change, unit }: KPICardProps) {
  const isPositive = change >= 0
  return (
    <div className="flex flex-col justify-center h-full p-4">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className="text-3xl font-bold mt-1">
        {value.toLocaleString()}{unit}
      </p>
      <p className={cn("text-sm mt-1", isPositive ? "text-green-500" : "text-red-500")}>
        {isPositive ? "↑" : "↓"} {Math.abs(change)}% vs last period
      </p>
    </div>
  )
}
```

---

## Drag & Drop (dnd-kit)

### Dashboard Grid
```typescript
// src/components/dashboard/DashboardGrid.tsx
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { SortableContext, rectSortingStrategy } from '@dnd-kit/sortable'

export function DashboardGrid({ widgets, isEditMode }) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor)
  )

  const handleDragEnd = async (event) => {
    const { active, over } = event
    if (active.id !== over?.id) {
      // Update widget positions
      await updateWidgetPositions(active.id, over.id)
    }
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={widgets.map(w => w.id)} strategy={rectSortingStrategy}>
        <div className="grid grid-cols-12 gap-4">
          {widgets.map(widget => (
            <SortableWidget key={widget.id} widget={widget} isEditMode={isEditMode} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  )
}
```

---

## WebSocket Client Hook
```typescript
// src/hooks/useWebSocket.ts
export function useWebSocket(orgId: string) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const MAX_RETRIES = 5

  const connect = useCallback(() => {
    const token = useAuthStore.getState().accessToken
    const ws = new WebSocket(
      `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/ws/${orgId}?token=${token}`
    )

    ws.onopen = () => {
      setIsConnected(true)
      retryCountRef.current = 0
    }

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      handleMessage(message)
    }

    ws.onclose = () => {
      setIsConnected(false)
      // Exponential backoff reconnection
      if (retryCountRef.current < MAX_RETRIES) {
        const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000)
        retryCountRef.current++
        setTimeout(connect, delay)
      }
    }

    wsRef.current = ws
  }, [orgId])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  return { isConnected }
}
```

---

## Shadcn Components To Use
```
Authentication: Card, Input, Button, Label, Form
Navigation: Sheet (mobile sidebar)
Dashboard: Dialog (create dashboard), Select (time range)
Widgets: DropdownMenu (widget options), Skeleton (loading)
Alerts: Badge (alert status), Switch (enable/disable)
Tables: Table, TableHeader, TableBody, TableRow, TableCell
Notifications: Toast (success/error messages)
```

## Responsive Design Rules
```
Mobile:  < 768px  → stack layout, no drag-drop, simplified charts
Tablet:  768-1024px → 2 column grid
Desktop: > 1024px → 12 column grid (full experience)
```
