'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart2 } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { WidgetCard } from '@/components/dashboard/WidgetCard'
import api from '@/lib/api'
import type { ApiResponse, Dashboard, Widget } from '@/types/api'

async function fetchSharedDashboard(token: string): Promise<Dashboard> {
  const { data: res } = await api.get<ApiResponse<Dashboard>>(`/dashboards/shared/${token}`)
  return res.data
}

export default function SharedDashboardPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params)

  const { data: dashboard, isLoading, isError } = useQuery({
    queryKey: ['shared-dashboard', token],
    queryFn: () => fetchSharedDashboard(token),
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-12 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="col-span-6 h-48 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (isError || !dashboard) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
        <BarChart2 className="h-12 w-12 text-muted-foreground" />
        <h1 className="text-xl font-semibold">Dashboard not found</h1>
        <p className="text-sm text-muted-foreground">
          This link may be invalid or the dashboard is no longer public.
        </p>
      </div>
    )
  }

  const sortedWidgets = [...dashboard.widgets].sort(
    (a, b) => a.position_y - b.position_y || a.position_x - b.position_x
  )

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <BarChart2 className="h-5 w-5 text-primary" />
          <div>
            <h1 className="text-lg font-semibold">{dashboard.name}</h1>
            {dashboard.description && (
              <p className="text-xs text-muted-foreground">{dashboard.description}</p>
            )}
          </div>
          <span className="ml-auto text-xs text-muted-foreground">Read-only · Wexa Analytics</span>
        </div>
      </header>

      {/* Widgets */}
      <main className="p-6">
        {sortedWidgets.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
            <p className="text-sm text-muted-foreground">This dashboard has no widgets.</p>
          </div>
        ) : (
          <div className="grid grid-cols-12 gap-4" style={{ gridAutoRows: '80px' }}>
            {sortedWidgets.map((widget: Widget) => (
              <div
                key={widget.id}
                style={{
                  gridColumn: `span ${widget.width}`,
                  gridRow: `span ${Math.ceil(widget.height / 2)}`,
                  minHeight: `${widget.height * 40}px`,
                }}
              >
                <WidgetCard
                  widget={widget}
                  isEditMode={false}
                  onEdit={() => {}}
                  onDelete={() => {}}
                />
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
