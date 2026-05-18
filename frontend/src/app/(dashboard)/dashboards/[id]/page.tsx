'use client'

import { use, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import {
  DndContext,
  DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  ArrowLeft,
  Copy,
  Edit2,
  Maximize2,
  Minimize2,
  Plus,
  RefreshCw,
  Share2,
  Trash2,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { WidgetCard } from '@/components/dashboard/WidgetCard'
import api from '@/lib/api'
import type {
  AggregationType,
  ApiResponse,
  Dashboard,
  GroupByType,
  SavedQuery,
  ShareResponse,
  TimeRange,
  Widget,
  WidgetType,
} from '@/types/api'

// ── API ───────────────────────────────────────────────────────────────────────

async function fetchDashboard(id: string): Promise<Dashboard> {
  const { data: res } = await api.get<ApiResponse<Dashboard>>(`/dashboards/${id}`)
  return res.data
}

async function fetchSavedQueries(): Promise<SavedQuery[]> {
  const { data: res } = await api.get<ApiResponse<SavedQuery[]>>('/saved-queries')
  return res.data
}

async function shareDashboard(id: string, enabled: boolean): Promise<ShareResponse> {
  const { data: res } = await api.post<ApiResponse<ShareResponse>>(`/dashboards/${id}/share`, { enabled })
  return res.data
}

async function deleteWidget(widgetId: string): Promise<void> {
  await api.delete(`/widgets/${widgetId}`)
}

async function updateWidgetPosition(widgetId: string, position: { x: number; y: number; w: number; h: number }): Promise<void> {
  await api.put(`/widgets/${widgetId}`, { position })
}

async function createWidget(payload: {
  dashboard_id: string
  title: string
  widget_type: WidgetType
  saved_query_id: string
  time_range: TimeRange
  position: { x: number; y: number; w: number; h: number }
}): Promise<Widget> {
  const { data: res } = await api.post<ApiResponse<Widget>>('/widgets', payload)
  return res.data
}

async function updateWidget(widgetId: string, payload: {
  title?: string
  widget_type?: WidgetType
  saved_query_id?: string
  time_range?: TimeRange
}): Promise<Widget> {
  const { data: res } = await api.put<ApiResponse<Widget>>(`/widgets/${widgetId}`, payload)
  return res.data
}

async function createSavedQuery(payload: {
  name: string
  event_name: string
  aggregation: AggregationType
  group_by: GroupByType
  time_range: TimeRange
}): Promise<SavedQuery> {
  const { data: res } = await api.post<ApiResponse<SavedQuery>>('/saved-queries', { ...payload, filters: [] })
  return res.data
}

// ── Sortable Widget Wrapper ────────────────────────────────────────────────────

function SortableWidget({
  widget,
  isEditMode,
  onEdit,
  onDelete,
}: {
  widget: Widget
  isEditMode: boolean
  onEdit: (w: Widget) => void
  onDelete: (id: string) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: widget.id,
    disabled: !isEditMode,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    gridColumn: `span ${widget.width}`,
    gridRow: `span ${widget.height}`,
    minHeight: `${widget.height * 50}px`,
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <div className="h-full">
        <WidgetCard
          widget={widget}
          isEditMode={isEditMode}
          onEdit={onEdit}
          onDelete={onDelete}
          dragListeners={isEditMode ? listeners : undefined}
        />
      </div>
    </div>
  )
}

// ── Widget Editor Dialog ───────────────────────────────────────────────────────

function WidgetEditorDialog({
  dashboardId,
  editingWidget,
  open,
  onClose,
  onSaved,
}: {
  dashboardId: string
  editingWidget: Widget | null
  open: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const [title, setTitle] = useState('')
  const [widgetType, setWidgetType] = useState<WidgetType>('line_chart')
  const [timeRange, setTimeRange] = useState<TimeRange>('24h')
  const [savedQueryId, setSavedQueryId] = useState<string>('')
  const [tab, setTab] = useState<'existing' | 'new'>('existing')
  // New query fields
  const [qName, setQName] = useState('')
  const [qEvent, setQEvent] = useState('')
  const [qAgg, setQAgg] = useState<AggregationType>('count')
  const [qGroupBy, setQGroupBy] = useState<GroupByType>('hour')

  const queryClient = useQueryClient()

  const { data: savedQueries = [] } = useQuery({
    queryKey: ['saved-queries'],
    queryFn: fetchSavedQueries,
  })

  useEffect(() => {
    if (editingWidget) {
      setTitle(editingWidget.title)
      setWidgetType(editingWidget.widget_type)
      setTimeRange(editingWidget.time_range as TimeRange)
      setSavedQueryId(editingWidget.saved_query_id ?? '')
    } else {
      setTitle('')
      setWidgetType('line_chart')
      setTimeRange('24h')
      setSavedQueryId(savedQueries[0]?.id ?? '')
    }
  }, [editingWidget, open, savedQueries])

  const saveMutation = useMutation({
    mutationFn: async () => {
      let queryId = savedQueryId

      if (tab === 'new') {
        const sq = await createSavedQuery({
          name: qName || `${qEvent} ${qAgg}`,
          event_name: qEvent,
          aggregation: qAgg,
          group_by: qGroupBy,
          time_range: timeRange,
        })
        queryId = sq.id
      }

      if (editingWidget) {
        await updateWidget(editingWidget.id, {
          title,
          widget_type: widgetType,
          saved_query_id: queryId || undefined,
          time_range: timeRange,
        })
      } else {
        const nextPos = { x: 0, y: 999, w: 6, h: 4 }
        await createWidget({
          dashboard_id: dashboardId,
          title,
          widget_type: widgetType,
          saved_query_id: queryId,
          time_range: timeRange,
          position: nextPos,
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] })
      queryClient.invalidateQueries({ queryKey: ['saved-queries'] })
      toast.success(editingWidget ? 'Widget updated' : 'Widget added')
      onSaved()
      onClose()
    },
    onError: () => toast.error('Failed to save widget'),
  })

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{editingWidget ? 'Edit Widget' : 'Add Widget'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Widget title" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Chart type</Label>
              <Select value={widgetType} onValueChange={(v) => setWidgetType(v as WidgetType)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="line_chart">Line chart</SelectItem>
                  <SelectItem value="bar_chart">Bar chart</SelectItem>
                  <SelectItem value="pie_chart">Pie chart</SelectItem>
                  <SelectItem value="kpi_card">KPI card</SelectItem>
                  <SelectItem value="table">Table</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Time range</Label>
              <Select value={timeRange} onValueChange={(v) => setTimeRange(v as TimeRange)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="1h">Last 1 hour</SelectItem>
                  <SelectItem value="6h">Last 6 hours</SelectItem>
                  <SelectItem value="24h">Last 24 hours</SelectItem>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Query selector */}
          <div className="space-y-2">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setTab('existing')}
                className={`text-sm px-3 py-1 rounded-md ${tab === 'existing' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Existing query
              </button>
              <button
                type="button"
                onClick={() => setTab('new')}
                className={`text-sm px-3 py-1 rounded-md ${tab === 'new' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              >
                New query
              </button>
            </div>

            {tab === 'existing' ? (
              <Select value={savedQueryId} onValueChange={(v) => { if (v) setSavedQueryId(v) }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a saved query" />
                </SelectTrigger>
                <SelectContent>
                  {savedQueries.map((q) => (
                    <SelectItem key={q.id} value={q.id}>
                      {q.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="space-y-2 rounded-lg border p-3">
                <div className="space-y-1">
                  <Label className="text-xs">Event name</Label>
                  <Input
                    value={qEvent}
                    onChange={(e) => setQEvent(e.target.value)}
                    placeholder="e.g. page_view"
                    className="h-8 text-sm"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Aggregation</Label>
                    <Select value={qAgg} onValueChange={(v) => setQAgg(v as AggregationType)}>
                      <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="count">Count</SelectItem>
                        <SelectItem value="sum">Sum</SelectItem>
                        <SelectItem value="avg">Average</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Group by</Label>
                    <Select value={qGroupBy} onValueChange={(v) => setQGroupBy(v as GroupByType)}>
                      <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="minute">Minute</SelectItem>
                        <SelectItem value="hour">Hour</SelectItem>
                        <SelectItem value="day">Day</SelectItem>
                        <SelectItem value="week">Week</SelectItem>
                        <SelectItem value="month">Month</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || !title.trim() || (tab === 'existing' && !savedQueryId) || (tab === 'new' && !qEvent.trim())}
          >
            {saveMutation.isPending ? 'Saving…' : editingWidget ? 'Update' : 'Add Widget'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const REFRESH_MS: Record<string, number> = { '30s': 30000, '1m': 60000, '5m': 300000 }

export default function DashboardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const queryClient = useQueryClient()

  const [isEditMode, setIsEditMode] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [widgetOrder, setWidgetOrder] = useState<string[]>([])
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingWidget, setEditingWidget] = useState<Widget | null>(null)
  const fullscreenRef = useRef<HTMLDivElement>(null)

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const { data: dashboard, isLoading } = useQuery<Dashboard>({
    queryKey: ['dashboard', id],
    queryFn: () => fetchDashboard(id),
    refetchInterval: (query) => {
      const d = query.state.data
      if (d?.auto_refresh_interval) return REFRESH_MS[d.auto_refresh_interval] ?? false
      return false
    },
  })

  useEffect(() => {
    if (dashboard?.widgets) {
      setWidgetOrder(
        [...dashboard.widgets]
          .sort((a, b) => a.position_y - b.position_y || a.position_x - b.position_x)
          .map((w) => w.id)
      )
    }
  }, [dashboard?.widgets])

  const shareMutation = useMutation({
    mutationFn: (enabled: boolean) => shareDashboard(id, enabled),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', id] })
      if (data.share_url) {
        navigator.clipboard.writeText(data.share_url)
        toast.success('Share link copied to clipboard')
      } else {
        toast.success('Dashboard is now private')
      }
    },
    onError: () => toast.error('Failed to update sharing'),
  })

  const deleteWidgetMutation = useMutation({
    mutationFn: deleteWidget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', id] })
      toast.success('Widget deleted')
    },
    onError: () => toast.error('Failed to delete widget'),
  })

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = widgetOrder.indexOf(String(active.id))
    const newIndex = widgetOrder.indexOf(String(over.id))
    const newOrder = arrayMove(widgetOrder, oldIndex, newIndex)
    setWidgetOrder(newOrder)

    // Persist positions
    const updates = newOrder.map((wid, idx) => {
      const col = (idx % 2) * 6
      const row = Math.floor(idx / 2) * 4
      return updateWidgetPosition(wid, { x: col, y: row, w: 6, h: 4 })
    })
    await Promise.all(updates)
    queryClient.invalidateQueries({ queryKey: ['dashboard', id] })
  }

  function toggleFullscreen() {
    if (!isFullscreen) {
      fullscreenRef.current?.requestFullscreen().catch(() => {})
      setIsFullscreen(true)
    } else {
      document.exitFullscreen().catch(() => {})
      setIsFullscreen(false)
    }
  }

  const sortedWidgets = dashboard
    ? widgetOrder
        .map((wid) => dashboard.widgets.find((w) => w.id === wid))
        .filter((w): w is Widget => !!w)
    : []

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-12 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="col-span-6 h-48 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (!dashboard) return null

  return (
    <div ref={fullscreenRef} className={`space-y-4 ${isFullscreen ? 'bg-background p-6' : ''}`}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="ghost" size="icon" onClick={() => router.push('/dashboards')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold truncate">{dashboard.name}</h1>
          {dashboard.description && (
            <p className="text-xs text-muted-foreground">{dashboard.description}</p>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {dashboard.auto_refresh_interval && (
            <Badge variant="secondary" className="text-xs">
              <RefreshCw className="mr-1 h-3 w-3" />
              {dashboard.auto_refresh_interval}
            </Badge>
          )}

          {/* Share */}
          <Button
            variant="outline"
            size="sm"
            disabled={shareMutation.isPending}
            onClick={() => shareMutation.mutate(!dashboard.is_public)}
          >
            {dashboard.is_public ? (
              <>
                <Copy className="mr-1.5 h-3.5 w-3.5" /> Copy link
              </>
            ) : (
              <>
                <Share2 className="mr-1.5 h-3.5 w-3.5" /> Share
              </>
            )}
          </Button>

          {/* Fullscreen */}
          <Button variant="outline" size="icon" onClick={toggleFullscreen}>
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>

          {/* Edit mode */}
          <Button
            variant={isEditMode ? 'default' : 'outline'}
            size="sm"
            onClick={() => setIsEditMode((v) => !v)}
          >
            <Edit2 className="mr-1.5 h-3.5 w-3.5" />
            {isEditMode ? 'Done' : 'Edit'}
          </Button>

          {/* Add widget */}
          {isEditMode && (
            <Button size="sm" onClick={() => { setEditingWidget(null); setEditorOpen(true) }}>
              <Plus className="mr-1.5 h-3.5 w-3.5" /> Add widget
            </Button>
          )}
        </div>
      </div>

      {/* Widget grid */}
      {sortedWidgets.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <p className="text-sm font-medium">No widgets yet</p>
          <p className="text-xs text-muted-foreground mt-1 mb-4">
            Click <strong>Edit</strong> then <strong>Add widget</strong> to get started
          </p>
        </div>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={widgetOrder} strategy={rectSortingStrategy}>
            <div className="grid grid-cols-12 gap-4" style={{ gridAutoRows: '50px' }}>
              {sortedWidgets.map((widget) => (
                <SortableWidget
                  key={widget.id}
                  widget={widget}
                  isEditMode={isEditMode}
                  onEdit={(w) => { setEditingWidget(w); setEditorOpen(true) }}
                  onDelete={(wid) => deleteWidgetMutation.mutate(wid)}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      {/* Widget editor */}
      <WidgetEditorDialog
        dashboardId={id}
        editingWidget={editingWidget}
        open={editorOpen}
        onClose={() => { setEditorOpen(false); setEditingWidget(null) }}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ['dashboard', id] })}
      />
    </div>
  )
}
