'use client'

import type { QueryResultPoint } from '@/types/api'

interface Props {
  data: QueryResultPoint[]
  title: string
}

export function TableWidget({ data, title }: Props) {
  if (!data.length) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        No data for this period
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-muted/50">
          <tr>
            <th className="py-2 px-3 text-left font-medium text-muted-foreground">Time</th>
            <th className="py-2 px-3 text-right font-medium text-muted-foreground">Value</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {data.map((row, i) => (
            <tr key={i} className="hover:bg-muted/30">
              <td className="py-1.5 px-3 text-muted-foreground">
                {new Date(row.bucket).toLocaleString()}
              </td>
              <td className="py-1.5 px-3 text-right font-mono font-medium">
                {row.value.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
