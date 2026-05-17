'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import api from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { ApiResponse, AuthData } from '@/types/api'

interface InviteInfo {
  email: string
  org_name: string
  role: string
  inviter_name: string
  is_existing_user: boolean
  expires_at: string
}

export default function InvitePage() {
  const { token } = useParams<{ token: string }>()
  const router = useRouter()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [inviteInfo, setInviteInfo] = useState<InviteInfo | null>(null)
  const [loadingInfo, setLoadingInfo] = useState(true)
  const [infoError, setInfoError] = useState<string | null>(null)

  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    async function fetchInfo() {
      try {
        const { data: res } = await api.get<ApiResponse<InviteInfo>>(`/auth/invite/${token}`)
        setInviteInfo(res.data)
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { error?: { message?: string } } } })
            ?.response?.data?.error?.message ?? 'This invite link is invalid or has expired.'
        setInfoError(msg)
      } finally {
        setLoadingInfo(false)
      }
    }
    fetchInfo()
  }, [token])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteInfo) return
    setSubmitting(true)
    try {
      const body: Record<string, string> = { password }
      if (!inviteInfo.is_existing_user) {
        body.full_name = fullName
      }
      const { data: res } = await api.post<ApiResponse<AuthData>>(
        `/auth/invite/${token}/accept`,
        body,
      )
      setAuth(res.data.user, res.data.org, res.data.role, res.data.access_token)
      toast.success(`Welcome to ${res.data.org.name}!`)
      router.push('/overview')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error
          ?.message ?? 'Failed to accept invite'
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  // Loading invite info
  if (loadingInfo) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Invalid / expired invite
  if (infoError || !inviteInfo) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl font-bold">Invite not found</CardTitle>
            <CardDescription>{infoError}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              The link may have expired or already been used. Ask the organization owner to send a new invite.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const isExisting = inviteInfo.is_existing_user

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">
            {isExisting ? 'Rejoin organization' : 'Accept your invite'}
          </CardTitle>
          <CardDescription>
            {isExisting
              ? `You've been re-invited to ${inviteInfo.org_name} as ${inviteInfo.role}. Enter your existing password to confirm.`
              : `${inviteInfo.inviter_name} invited you to join ${inviteInfo.org_name} as ${inviteInfo.role}. Create your account below.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email — read-only, always shown for clarity */}
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={inviteInfo.email} disabled className="bg-muted" />
            </div>

            {/* Full name — only for new users */}
            {!isExisting && (
              <div className="space-y-2">
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  placeholder="Jane Smith"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="password">
                {isExisting ? 'Your existing password' : 'Choose a password'}
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder={isExisting ? 'Enter your password' : 'Min 8 chars, 1 uppercase, 1 digit'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete={isExisting ? 'current-password' : 'new-password'}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={submitting || !password || (!isExisting && !fullName)}
            >
              {submitting
                ? (isExisting ? 'Rejoining…' : 'Creating account…')
                : (isExisting ? 'Confirm & rejoin' : 'Join organization')}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
