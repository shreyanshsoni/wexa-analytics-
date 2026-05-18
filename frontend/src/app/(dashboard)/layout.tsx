'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'

const NAV_ITEMS = [
  { href: '/dashboards', label: 'Dashboards' },
  { href: '/ingestion', label: 'Ingestion' },
  { href: '/alerts', label: 'Alerts' },
  { href: '/reports', label: 'Reports' },
  { href: '/settings', label: 'Settings' },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, _hasHydrated, user, organization, role, clearAuth } = useAuthStore()

  useEffect(() => {
    if (_hasHydrated && !isAuthenticated) {
      router.replace('/login')
    }
  }, [isAuthenticated, _hasHydrated, router])

  if (!_hasHydrated) return null
  if (!isAuthenticated) return null

  function handleLogout() {
    clearAuth()
    router.push('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="flex w-64 shrink-0 flex-col border-r bg-card">
        <div className="p-4">
          <span className="text-xl font-bold">Wexa Analytics</span>
          {organization && (
            <p className="mt-1 truncate text-xs text-muted-foreground">{organization.name}</p>
          )}
          {role && (
            <span className="mt-1 inline-block rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground">
              {role}
            </span>
          )}
        </div>
        <nav className="flex flex-col gap-1 px-2 text-sm">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded px-3 py-1.5 transition-colors hover:bg-accent hover:text-accent-foreground ${
                pathname.startsWith(item.href)
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t p-4">
          {user && (
            <p className="mb-2 truncate text-xs text-muted-foreground">{user.email}</p>
          )}
          <button
            onClick={handleLogout}
            className="w-full rounded px-3 py-1.5 text-left text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
