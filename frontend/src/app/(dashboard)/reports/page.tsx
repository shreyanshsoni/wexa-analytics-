export default function ReportsPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center space-y-3 text-center">
      <div className="rounded-full bg-muted p-4">
        <svg className="h-8 w-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <h1 className="text-xl font-semibold">Scheduled Reports</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Schedule recurring PDF or PNG snapshots of any dashboard — daily, weekly, or monthly — and deliver them to your team by email.
      </p>
    </div>
  )
}
