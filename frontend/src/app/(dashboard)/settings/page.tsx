'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Mail, Shield, Trash2, UserPlus } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import api from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { ApiResponse, Member, OrgMe, Role } from '@/types/api'

async function fetchOrgMe(): Promise<OrgMe> {
  const { data: res } = await api.get<ApiResponse<OrgMe>>('/organizations/me')
  return res.data
}

async function updateOrgName(name: string): Promise<{ name: string; slug: string }> {
  const { data: res } = await api.put<ApiResponse<{ id: string; name: string; slug: string }>>('/organizations/me', { name })
  return res.data
}

async function inviteMember(payload: { email: string; role: string }): Promise<void> {
  await api.post('/organizations/invite', payload)
}

async function removeMember(memberId: string): Promise<void> {
  await api.delete(`/organizations/members/${memberId}`)
}

async function changeMemberRole(memberId: string, role: string): Promise<void> {
  await api.put(`/organizations/members/${memberId}/role`, { role })
}

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  admin: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  analyst: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  viewer: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
}

function RoleBadge({ role }: { role: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${ROLE_COLORS[role] ?? ''}`}>
      {role}
    </span>
  )
}

export default function SettingsPage() {
  const { role: myRole, user, updateOrganization } = useAuthStore()
  const queryClient = useQueryClient()

  const [orgName, setOrgName] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<Role>('viewer')

  const canManage = myRole === 'owner' || myRole === 'admin'

  const { data: orgData, isLoading } = useQuery({
    queryKey: ['org-me'],
    queryFn: fetchOrgMe,
    select: (data: OrgMe) => {
      if (!orgName) setOrgName(data.org.name)
      return data
    },
  })

  const renameMutation = useMutation({
    mutationFn: updateOrgName,
    onSuccess: (updated) => {
      updateOrganization({ name: updated.name, slug: updated.slug })
      queryClient.invalidateQueries({ queryKey: ['org-me'] })
      toast.success('Organization name updated')
    },
    onError: () => toast.error('Failed to update organization name'),
  })

  const inviteMutation = useMutation({
    mutationFn: inviteMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-me'] })
      setInviteEmail('')
      toast.success('Invite sent successfully')
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message
      toast.error(msg ?? 'Failed to send invite')
    },
  })

  const removeMutation = useMutation({
    mutationFn: removeMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-me'] })
      toast.success('Member removed')
    },
    onError: () => toast.error('Failed to remove member'),
  })

  const changeRoleMutation = useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: string }) =>
      changeMemberRole(memberId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-me'] })
      toast.success('Role updated')
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message
      toast.error(msg ?? 'Failed to update role')
    },
  })

  function handleRename(e: React.FormEvent) {
    e.preventDefault()
    if (!orgName.trim()) return
    renameMutation.mutate(orgName.trim())
  }

  function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteEmail.trim()) return
    inviteMutation.mutate({ email: inviteEmail.trim(), role: inviteRole })
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your organization and team</p>
      </div>

      {/* Organization name */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" /> Organization
          </CardTitle>
          <CardDescription>Update your organization name</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-10 w-64" />
          ) : (
            <form onSubmit={handleRename} className="flex gap-2 max-w-sm">
              <Input
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="Organization name"
                disabled={!canManage}
              />
              {canManage && (
                <Button type="submit" disabled={renameMutation.isPending || !orgName.trim()}>
                  {renameMutation.isPending ? 'Saving…' : 'Save'}
                </Button>
              )}
            </form>
          )}
          {orgData && (
            <p className="mt-2 text-xs text-muted-foreground">
              Slug: <code className="font-mono">{orgData.org.slug}</code>
            </p>
          )}
        </CardContent>
      </Card>

      {/* Invite member */}
      {canManage && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" /> Invite Member
            </CardTitle>
            <CardDescription>Send an invite email to add someone to your organization</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleInvite} className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1 space-y-1">
                <Label htmlFor="invite-email">Email address</Label>
                <Input
                  id="invite-email"
                  type="email"
                  placeholder="colleague@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="invite-role">Role</Label>
                <Select value={inviteRole} onValueChange={(v) => setInviteRole(v as Role)}>
                  <SelectTrigger id="invite-role" className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="analyst">Analyst</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" disabled={inviteMutation.isPending || !inviteEmail.trim()}>
                <Mail className="mr-2 h-4 w-4" />
                {inviteMutation.isPending ? 'Sending…' : 'Send invite'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Members list */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" /> Team Members
          </CardTitle>
          <CardDescription>
            {orgData ? `${orgData.members.length} member${orgData.members.length !== 1 ? 's' : ''}` : ''}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : (
            <div className="divide-y rounded-md border">
              {orgData?.members.map((member: Member) => {
                const isOwner = member.role === 'owner'
                const isSelf = member.user.id === user?.id
                const canEdit = canManage && !isOwner && !isSelf
                return (
                  <div key={member.id} className="flex items-center justify-between p-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {member.user.full_name}
                        {isSelf && <span className="ml-1.5 text-xs text-muted-foreground">(you)</span>}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">{member.user.email}</p>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      {canEdit ? (
                        <Select
                          key={member.id + member.role}
                          value={member.role}
                          onValueChange={(newRole) =>
                            newRole && changeRoleMutation.mutate({ memberId: member.id, role: newRole })
                          }
                          disabled={changeRoleMutation.isPending}
                        >
                          <SelectTrigger className="h-7 w-28 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">Admin</SelectItem>
                            <SelectItem value="analyst">Analyst</SelectItem>
                            <SelectItem value="viewer">Viewer</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        <RoleBadge role={member.role} />
                      )}
                      {canEdit && (
                        <Button
                          size="icon"
                          variant="ghost"
                          title="Remove member"
                          disabled={removeMutation.isPending}
                          onClick={() => removeMutation.mutate(member.id)}
                          className="h-8 w-8 text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
