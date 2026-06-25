import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { CheckCircle2, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { PageHeader } from "@/components/shared/PageHeader"
import { fintech } from "@/lib/fintech-styles"
import {
  useChangeUserRole,
  useMccCategories,
  useSendNotificationToGroup,
  useSendNotificationToUser,
  useUpdateUserTags,
} from "./hooks"
import type { UserRole } from "./api"

const USER_ROLES: UserRole[] = ["Viewer", "Operator", "Admin"]

function SectionSuccess({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-1.5 text-sm text-emerald-600">
      <CheckCircle2 className="size-4" />
      {message}
    </div>
  )
}

function ChangeRoleSection() {
  const [email, setEmail] = useState("")
  const [role, setRole] = useState<UserRole>("Viewer")
  const mutation = useChangeUserRole()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    mutation.mutate({ email: email.trim(), role })
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <p className={fintech.sectionEyebrow}>Change User Role</p>
      <div className="space-y-1.5">
        <Label className="text-sm">User email</Label>
        <Input
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="fintech-input"
        />
      </div>
      <div className="space-y-1.5">
        <Label className="text-sm">New role</Label>
        <Select value={role} onValueChange={(v) => setRole(v as UserRole)}>
          <SelectTrigger className="fintech-input">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {USER_ROLES.map((r) => (
              <SelectItem key={r} value={r}>
                {r}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {mutation.error ? (
        <ErrorAlert
          message={mutation.error instanceof Error ? mutation.error.message : "Failed to change role."}
        />
      ) : null}
      {mutation.isSuccess ? <SectionSuccess message="Role updated" /> : null}
      <Button type="submit" size="sm" disabled={mutation.isPending || !email.trim()}>
        {mutation.isPending ? "Updating…" : "Change role"}
        {!mutation.isPending ? <ChevronRight className="ml-1 size-3.5" /> : null}
      </Button>
    </form>
  )
}

function UpdateTagsSection() {
  const [email, setEmail] = useState("")
  const [tagsRaw, setTagsRaw] = useState("")
  const mutation = useUpdateUserTags()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const tags = tagsRaw
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
    mutation.mutate({ email: email.trim(), tags })
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="mt-1 h-px bg-slate-100" />
      <p className={fintech.sectionEyebrow}>Assign Tags to User</p>
      <div className="space-y-1.5">
        <Label className="text-sm">User email</Label>
        <Input
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="fintech-input"
        />
      </div>
      <div className="space-y-1.5">
        <Label className="text-sm">
          Tags{" "}
          <span className="font-normal text-slate-400">comma-separated</span>
        </Label>
        <Input
          placeholder="groceries, travel, dining"
          value={tagsRaw}
          onChange={(e) => setTagsRaw(e.target.value)}
          className="fintech-input"
        />
      </div>
      {mutation.error ? (
        <ErrorAlert
          message={mutation.error instanceof Error ? mutation.error.message : "Failed to update tags."}
        />
      ) : null}
      {mutation.isSuccess ? <SectionSuccess message="Tags updated" /> : null}
      <Button type="submit" size="sm" disabled={mutation.isPending || !email.trim()}>
        {mutation.isPending ? "Saving…" : "Update tags"}
        {!mutation.isPending ? <ChevronRight className="ml-1 size-3.5" /> : null}
      </Button>
    </form>
  )
}

function NotifyUserSection() {
  const [email, setEmail] = useState("")
  const [message, setMessage] = useState("")
  const [dealId, setDealId] = useState("")
  const mutation = useSendNotificationToUser()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    mutation.mutate(
      { email: email.trim(), message: message.trim(), dealId: dealId.trim() },
      {
        onSuccess: () => {
          setMessage("")
          setDealId("")
        },
      },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <p className={fintech.sectionEyebrow}>Send Notification to User</p>
      <div className="space-y-1.5">
        <Label className="text-sm">Recipient email</Label>
        <Input
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="fintech-input"
        />
      </div>
      <div className="space-y-1.5">
        <Label className="text-sm">Message</Label>
        <textarea
          placeholder="Notification message…"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
          rows={3}
          className="fintech-input w-full resize-none rounded-xl border border-slate-200/80 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-violet-300"
        />
      </div>
      <div className="space-y-1.5">
        <Label className="text-sm">
          Deal ID <span className="font-normal text-slate-400">optional</span>
        </Label>
        <Input
          placeholder="deal-abc-123"
          value={dealId}
          onChange={(e) => setDealId(e.target.value)}
          className="fintech-input"
        />
      </div>
      {mutation.error ? (
        <ErrorAlert
          message={mutation.error instanceof Error ? mutation.error.message : "Failed to send notification."}
        />
      ) : null}
      {mutation.isSuccess ? <SectionSuccess message="Notification sent" /> : null}
      <Button
        type="submit"
        size="sm"
        disabled={mutation.isPending || !email.trim() || !message.trim()}
      >
        {mutation.isPending ? "Sending…" : "Send to user"}
        {!mutation.isPending ? <ChevronRight className="ml-1 size-3.5" /> : null}
      </Button>
    </form>
  )
}

function NotifyGroupSection() {
  const [tag, setTag] = useState("")
  const [message, setMessage] = useState("")
  const [dealId, setDealId] = useState("")
  const mutation = useSendNotificationToGroup()
  const { data: categories, isLoading: categoriesLoading, error: categoriesError } = useMccCategories()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    mutation.mutate(
      { tag, message: message.trim(), dealId: dealId.trim() },
      {
        onSuccess: () => {
          setMessage("")
          setDealId("")
        },
      },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <p className={fintech.sectionEyebrow}>Broadcast Notification to Group</p>
      <div className="space-y-1.5">
        <Label className="text-sm">Group category</Label>
        {categoriesError ? (
          <ErrorAlert message="Failed to load categories." />
        ) : (
          <Select value={tag} onValueChange={setTag} disabled={categoriesLoading}>
            <SelectTrigger className="fintech-input">
              <SelectValue placeholder={categoriesLoading ? "Loading…" : "Select a category"} />
            </SelectTrigger>
            <SelectContent>
              {(categories ?? []).map((c) => (
                <SelectItem key={c.category} value={c.category}>
                  {c.category}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      <div className="space-y-1.5">
        <Label className="text-sm">Message</Label>
        <textarea
          placeholder="Notification message…"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
          rows={3}
          className="fintech-input w-full resize-none rounded-xl border border-slate-200/80 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-violet-300"
        />
      </div>
      <div className="space-y-1.5">
        <Label className="text-sm">
          Deal ID <span className="font-normal text-slate-400">optional</span>
        </Label>
        <Input
          placeholder="deal-abc-123"
          value={dealId}
          onChange={(e) => setDealId(e.target.value)}
          className="fintech-input"
        />
      </div>
      {mutation.error ? (
        <ErrorAlert
          message={mutation.error instanceof Error ? mutation.error.message : "Failed to broadcast notification."}
        />
      ) : null}
      {mutation.isSuccess ? <SectionSuccess message="Notification broadcast" /> : null}
      <Button
        type="submit"
        size="sm"
        disabled={mutation.isPending || !tag || !message.trim()}
      >
        {mutation.isPending ? "Broadcasting…" : "Broadcast to group"}
        {!mutation.isPending ? <ChevronRight className="ml-1 size-3.5" /> : null}
      </Button>
    </form>
  )
}

export function AdminPage() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader title="Admin" onBack={() => navigate(-1)} />

      <section className={fintech.page}>
        <Card className="fintech-card border-0">
          <CardContent className="space-y-4 px-5 py-4">
            <ChangeRoleSection />
            <UpdateTagsSection />
          </CardContent>
        </Card>

        <Card className="fintech-card border-0">
          <CardContent className="space-y-4 px-5 py-4">
            <NotifyUserSection />
          </CardContent>
        </Card>

        <Card className="fintech-card border-0">
          <CardContent className="space-y-4 px-5 py-4">
            <NotifyGroupSection />
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
