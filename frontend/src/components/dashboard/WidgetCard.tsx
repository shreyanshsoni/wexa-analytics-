'use client'

import { MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { BarChartWidget } from '@/components/charts/BarChartWidget'
import { KpiCardWidget } from '@/components/charts/KpiCardWidget'
import { LineChartWidget } from '@/components/charts/LineChartWidget'
import { PieChartWidget } from '@/components/charts/PieChartWidget'
import { TableWidget } from '@/components/charts/TableWidget'
import type { QueryResultPoint, Widget } from '@/types/api'

interface Props {
  widget: Widget
  isEditMode: boolean
  onEdit: (widget: Widget) => void
  onDelete: (widgetId: string) => void
}

function ChartContent({ widget }: { widget: Widget }) {
  const data: QueryResultPoint[] = widget.query_result?.data ?? []
  const title = widget.title

  switch (widget.widget_type) {
    case 'line_chart':
      return <LineChartWidget data={data} title={title} />
    case 'bar_chart':
      return <BarChartWidget data={data} title={title} />
    case 'pie_chart':
      return <PieChartWidget data={data} title={title} />
    case 'kpi_card':
      return <KpiCardWidget data={data} title={title} />
    case 'table':
      return <TableWidget data={data} title={title} />
    default:
      return <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Unknown widget type</div>
  }
}

export function WidgetCard({ widget, isEditMode, onEdit, onDelete }: Props) {
  const isCached = widget.query_result?.cached

  return (
    <div className="flex h-full flex-col rounded-lg border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <p className="truncate text-sm font-medium">{widget.title}</p>
          {isCached && (
            <span className="shrink-0 text-xs text-muted-foreground">(cached)</span>
          )}
        </div>
        {isEditMode && (
          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground">
              <MoreHorizontal className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(widget)}>
                <Pencil className="mr-2 h-4 w-4" /> Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => onDelete(widget.id)}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Chart */}
      <div className="flex-1 min-h-0 p-2">
        <ChartContent widget={widget} />
      </div>
    </div>
  )
}
