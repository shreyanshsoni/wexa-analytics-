'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'

export default function Home() {
  const router = useRouter()
  const { isAuthenticated, _hasHydrated } = useAuthStore()

  useEffect(() => {
    if (!_hasHydrated) return
    router.replace(isAuthenticated ? '/overview' : '/login')
  }, [isAuthenticated, _hasHydrated, router])

  return null
}
