'use client'

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { QueryResultPoint } from '@/types/api'

const COLORS = [
  'hsl(var(--primary))',
  '#22c55e',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#06b6d4',
  '#ec4899',
]

interface Props {
  data: QueryResultPoint[]
  title: string
}

export function PieChartWidget({ data, title }: Props) {
  if (!data.length) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        No data for this period
      </div>
    )
  }

  const total = data.reduce((s, p) => s + p.value, 0)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="bucket"
          cx="50%"
          cy="50%"
          outerRadius="70%"
          label={({ name, percent }: { name: string; percent: number }) =>
            `${name.slice(0, 10)} ${(percent * 100).toFixed(0)}%`
          }
          labelLine={false}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 6 }}
          formatter={(val: number) => [val.toLocaleString(), title]}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
