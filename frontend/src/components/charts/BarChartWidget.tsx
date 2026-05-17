'use client'

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { QueryResultPoint } from '@/types/api'

interface Props {
  data: QueryResultPoint[]
  title: string
}

function formatBucket(bucket: string): string {
  const d = new Date(bucket)
  if (isNaN(d.getTime())) return bucket
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export function BarChartWidget({ data, title }: Props) {
  if (!data.length) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        No data for this period
      </div>
    )
  }

  const formatted = data.map((p) => ({ ...p, bucket: formatBucket(p.bucket) }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={formatted} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
        <XAxis dataKey="bucket" tick={{ fontSize: 11 }} tickLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 6 }}
          formatter={(val: number) => [val.toLocaleString(), title]}
        />
        <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
