'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { BarChart2, Globe, Lock, Plus } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import api from '@/lib/api'
import type { ApiResponse, Dashboard, DashboardListItem, TemplateType } from '@/types/api'

async function fetchDashboards(): Promise<DashboardListItem[]> {
  const { data: res } = await api.get<ApiResponse<DashboardListItem[]>>('/dashboards')
  return res.data
}

async function createDashboard(payload: {
  name: string
  description?: string
  template_type?: TemplateType | null
}): Promise<Dashboard> {
  const { data: res } = await api.post<ApiResponse<Dashboard>>('/dashboards', payload)
  return res.data
}

const TEMPLATES: { value: TemplateType | 'blank'; label: string; description: string }[] = [
  { value: 'blank', label: 'Blank Dashboard', description: 'Start from scratch' },
  { value: 'web_analytics', label: 'Web Analytics', description: 'Page views, visitors, clicks' },
  { value: 'sales', label: 'Sales', description: 'Purchases, revenue, conversions' },
  { value: 'devops', label: 'DevOps', description: 'Errors, requests, latency' },
]

function CreateDashboardDialog({ onCreated }: { onCreated: (id: string) => void }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [template, setTemplate] = useState<TemplateType | 'blank'>('blank')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: createDashboard,
    onSuccess: (d) => {
      queryClient.invalidateQueries({ queryKey: ['dashboards'] })
      setOpen(false)
      setName('')
      setTemplate('blank')
      toast.success('Dashboard created')
      onCreated(d.id)
    },
    onError: () => toast.error('Failed to create dashboard'),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    mutation.mutate({
      name: name.trim(),
      template_type: template === 'blank' ? null : template,
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button onClick={() => setOpen(true)}>
        <Plus className="mr-2 h-4 w-4" /> New Dashboard
      </Button>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Dashboard</DialogTitle>
          <DialogDescription>Give your dashboard a name and optionally start from a template.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="dash-name">Name</Label>
            <Input
              id="dash-name"
              placeholder="My Dashboard"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <Label>Template</Label>
            <div className="grid grid-cols-2 gap-2">
              {TEMPLATES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setTemplate(t.value)}
                  className={`rounded-lg border p-3 text-left transition-colors ${
                    template === t.value
                      ? 'border-primary bg-primary/5'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                >
                  <p className="text-sm font-medium">{t.label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{t.description}</p>
                </button>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending || !name.trim()}>
              {mutation.isPending ? 'Creating…' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function OverviewPage() {
  const router = useRouter()

  const { data: dashboards = [], isLoading } = useQuery({
    queryKey: ['dashboards'],
    queryFn: fetchDashboards,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboards</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create and manage your analytics dashboards
          </p>
        </div>
        <CreateDashboardDialog onCreated={(id) => router.push(`/dashboards/${id}`)} />
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-40 w-full rounded-xl" />)}
        </div>
      ) : dashboards.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <BarChart2 className="h-10 w-10 text-muted-foreground mb-4" />
          <p className="text-sm font-medium">No dashboards yet</p>
          <p className="text-xs text-muted-foreground mt-1 mb-4">
            Create your first dashboard to start visualizing your data
          </p>
          <CreateDashboardDialog onCreated={(id) => router.push(`/dashboards/${id}`)} />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {dashboards.map((d) => (
            <Card
              key={d.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/dashboards/${d.id}`)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base leading-snug">{d.name}</CardTitle>
                  {d.is_public ? (
                    <Globe className="h-4 w-4 shrink-0 text-muted-foreground" aria-label="Public" />
                  ) : (
                    <Lock className="h-4 w-4 shrink-0 text-muted-foreground" aria-label="Private" />
                  )}
                </div>
                {d.description && (
                  <CardDescription className="line-clamp-2">{d.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{d.widget_count} widget{d.widget_count !== 1 ? 's' : ''}</span>
                  {d.auto_refresh_interval && (
                    <Badge variant="secondary" className="text-xs">
                      Auto-refresh {d.auto_refresh_interval}
                    </Badge>
                  )}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Updated {new Date(d.updated_at).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
