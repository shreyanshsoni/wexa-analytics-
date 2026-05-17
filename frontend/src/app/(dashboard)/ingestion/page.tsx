'use client'

import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Copy, Eye, EyeOff, KeyRound, Plus, RefreshCw, Trash2, Upload } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import api from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { ApiKey, ApiKeyCreated, ApiResponse, CsvUploadResult, IngestionStats } from '@/types/api'

// ── API calls ─────────────────────────────────────────────────────────────────

async function fetchApiKeys(): Promise<ApiKey[]> {
  const { data: res } = await api.get<ApiResponse<ApiKey[]>>('/api-keys')
  return res.data
}

async function createApiKey(name: string): Promise<ApiKeyCreated> {
  const { data: res } = await api.post<ApiResponse<ApiKeyCreated>>('/api-keys', { name })
  return res.data
}

async function revokeApiKey(id: string): Promise<void> {
  await api.post(`/api-keys/${id}/revoke`)
}

async function rotateApiKey(id: string): Promise<ApiKeyCreated> {
  const { data: res } = await api.post<ApiResponse<ApiKeyCreated>>(`/api-keys/${id}/rotate`)
  return res.data
}

async function fetchStats(): Promise<IngestionStats> {
  const { data: res } = await api.get<ApiResponse<IngestionStats>>('/ingest/stats')
  return res.data
}

async function uploadCsv(file: File): Promise<CsvUploadResult> {
  const form = new FormData()
  form.append('file', file)
  const { data: res } = await api.post<ApiResponse<CsvUploadResult>>('/ingest/csv', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, loading }: { label: string; value: number; loading: boolean }) {
  return (
    <Card>
      <CardContent className="pt-6">
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <p className="text-3xl font-bold">{value.toLocaleString()}</p>
        )}
        <p className="mt-1 text-sm text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function IngestionPage() {
  const { role } = useAuthStore()
  const queryClient = useQueryClient()

  // API Keys
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeySecret, setNewKeySecret] = useState<string | null>(null)
  const [showSecret, setShowSecret] = useState(false)
  const [revealedKeys, setRevealedKeys] = useState<Record<string, string>>({})

  // CSV upload
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const canManageKeys = role === 'owner' || role === 'admin'
  const canUploadCsv = role === 'owner' || role === 'admin' || role === 'analyst'

  // ── queries ──────────────────────────────────────────────────────────────

  const { data: apiKeys = [], isLoading: keysLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: fetchApiKeys,
  })

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['ingestion-stats'],
    queryFn: fetchStats,
    refetchInterval: 30_000,
  })

  // ── mutations ─────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: createApiKey,
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setNewKeyName('')
      setNewKeySecret(created.key)
      setShowSecret(true)
      toast.success('API key created — copy it now, it won\'t be shown again')
    },
    onError: () => toast.error('Failed to create API key'),
  })

  const revokeMutation = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      toast.success('API key revoked')
    },
    onError: () => toast.error('Failed to revoke API key'),
  })

  const rotateMutation = useMutation({
    mutationFn: rotateApiKey,
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setNewKeySecret(created.key)
      setShowSecret(true)
      toast.success('API key rotated — copy the new key now')
    },
    onError: () => toast.error('Failed to rotate API key'),
  })

  const csvMutation = useMutation({
    mutationFn: uploadCsv,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['ingestion-stats'] })
      toast.success(result.message)
    },
    onError: () => toast.error('CSV upload failed'),
  })

  // ── handlers ──────────────────────────────────────────────────────────────

  function handleCreateKey(e: React.FormEvent) {
    e.preventDefault()
    if (!newKeyName.trim()) return
    createMutation.mutate(newKeyName.trim())
  }

  function handleFileSelect(file: File | null) {
    if (!file) return
    if (!file.name.endsWith('.csv')) {
      toast.error('Only .csv files are supported')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File exceeds 10 MB limit')
      return
    }
    csvMutation.mutate(file)
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Data Ingestion</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Send events via API key or upload a CSV file
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Events today" value={stats?.total_today ?? 0} loading={statsLoading} />
        <StatCard label="Last 7 days" value={stats?.total_week ?? 0} loading={statsLoading} />
        <StatCard label="Last 30 days" value={stats?.total_month ?? 0} loading={statsLoading} />
        <StatCard label="All time" value={stats?.total_all_time ?? 0} loading={statsLoading} />
      </div>

      {/* Revealed new key banner */}
      {newKeySecret && (
        <Card className="border-amber-400 bg-amber-50 dark:bg-amber-950/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-amber-800 dark:text-amber-300">
              Copy your API key — it will not be shown again
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-white px-3 py-2 font-mono text-sm dark:bg-black/30 overflow-x-auto">
                {showSecret ? newKeySecret : '•'.repeat(32)}
              </code>
              <Button size="icon" variant="ghost" onClick={() => setShowSecret((v) => !v)}>
                {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button size="icon" variant="ghost" onClick={() => copyToClipboard(newKeySecret)}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <Button
              size="sm"
              variant="ghost"
              className="text-xs"
              onClick={() => setNewKeySecret(null)}
            >
              Dismiss
            </Button>
          </CardContent>
        </Card>
      )}

      {/* API Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" /> API Keys
          </CardTitle>
          <CardDescription>
            Use these keys in the <code className="text-xs">X-API-Key</code> header to send events
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {canManageKeys && (
            <form onSubmit={handleCreateKey} className="flex gap-2">
              <Input
                placeholder="Key name (e.g. production-server)"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="max-w-sm"
              />
              <Button type="submit" disabled={createMutation.isPending || !newKeyName.trim()}>
                <Plus className="mr-2 h-4 w-4" />
                {createMutation.isPending ? 'Creating…' : 'Create key'}
              </Button>
            </form>
          )}

          {keysLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : apiKeys.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No API keys yet. Create one to start ingesting events.
            </p>
          ) : (
            <div className="divide-y rounded-md border">
              {apiKeys.map((key) => (
                <div key={key.id} className="flex items-center justify-between p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{key.name}</p>
                    <p className="font-mono text-xs text-muted-foreground">
                      {key.key_prefix}••••••••
                    </p>
                    {key.last_used_at && (
                      <p className="text-xs text-muted-foreground">
                        Last used {new Date(key.last_used_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <Badge variant={key.is_active ? 'default' : 'secondary'}>
                      {key.is_active ? 'Active' : 'Revoked'}
                    </Badge>
                    {canManageKeys && key.is_active && (
                      <>
                        <Button
                          size="icon"
                          variant="ghost"
                          title="Rotate key"
                          disabled={rotateMutation.isPending}
                          onClick={() => rotateMutation.mutate(key.id)}
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          title="Revoke key"
                          disabled={revokeMutation.isPending}
                          onClick={() => revokeMutation.mutate(key.id)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* CSV Upload */}
      {canUploadCsv && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" /> CSV Upload
            </CardTitle>
            <CardDescription>
              Upload a .csv file (max 10 MB). Required column: <code className="text-xs">event_name</code>.
              Optional: <code className="text-xs">timestamp</code>. All other columns become event properties.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 transition-colors ${
                dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
              } ${csvMutation.isPending ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragOver(false)
                handleFileSelect(e.dataTransfer.files[0] ?? null)
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="mb-3 h-8 w-8 text-muted-foreground" />
              <p className="text-sm font-medium">
                {csvMutation.isPending ? 'Uploading…' : 'Drop CSV here or click to browse'}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Max 10 MB · .csv only</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
              />
            </div>

            {/* Quick reference */}
            <details className="mt-4">
              <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                CSV format example
              </summary>
              <pre className="mt-2 rounded bg-muted p-3 text-xs overflow-x-auto">{`event_name,timestamp,url,user_id
page_view,2024-01-01T10:00:00Z,/home,user_123
button_click,,/pricing,user_456
signup,2024-01-01T11:30:00Z,/signup,user_789`}</pre>
            </details>
          </CardContent>
        </Card>
      )}

      {/* Quick-start code snippet */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick Start</CardTitle>
          <CardDescription>Send your first event with curl</CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="rounded bg-muted p-4 text-xs overflow-x-auto">{`curl -X POST ${process.env.NEXT_PUBLIC_API_URL}/api/v1/ingest/events \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"event": "page_view", "properties": {"url": "/home", "user_id": "123"}}'`}</pre>
        </CardContent>
      </Card>
    </div>
  )
}
