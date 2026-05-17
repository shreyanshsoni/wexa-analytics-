'use client'

import type { QueryResultPoint } from '@/types/api'

interface Props {
  data: QueryResultPoint[]
  title: string
}

export function KpiCardWidget({ data, title }: Props) {
  const total = data.reduce((s, p) => s + p.value, 0)
  const latest = data[data.length - 1]?.value ?? 0
  const prev = data[data.length - 2]?.value ?? 0
  const change = prev > 0 ? ((latest - prev) / prev) * 100 : null

  return (
    <div className="flex h-full flex-col justify-center p-2">
      <p className="text-xs font-medium text-muted-foreground truncate">{title}</p>
      <p className="mt-1 text-3xl font-bold tabular-nums">
        {total.toLocaleString()}
      </p>
      {change !== null && (
        <p className={`mt-1 text-xs font-medium ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
          {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}% vs prev period
        </p>
      )}
      {data.length === 0 && (
        <p className="mt-1 text-xs text-muted-foreground">No data</p>
      )}
    </div>
  )
}
