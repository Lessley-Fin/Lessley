import { useState } from "react"
import type { FormEvent } from "react"
import { UserCog } from "lucide-react"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useChangeUserRole } from "../hooks"
import type { UserRole } from "../api"

const USER_ROLES: UserRole[] = ["Viewer", "Operator", "Admin"]

export function ChangeRoleSlide() {
  const [email, setEmail] = useState("")
  const [role, setRole] = useState<UserRole>("Viewer")
  const mutation = useChangeUserRole()

  function submit(e: FormEvent) {
    e.preventDefault()
    mutation.mutate({ email: email.trim(), role })
  }

  return (
    <form
      onSubmit={submit}
      className="flex min-h-[380px] flex-col gap-4 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]"
    >
      <div className="flex items-center gap-2">
        <span className="flex size-9 items-center justify-center rounded-full bg-secondary">
          <UserCog className="size-4 text-primary" aria-hidden />
        </span>
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Change user role</p>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-role-email">User email</Label>
        <Input
          id="admin-role-email"
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="h-12 rounded-2xl"
        />
      </div>
      <div className="space-y-1.5">
        <Label>Role</Label>
        <Select value={role} onValueChange={(v) => setRole(v as UserRole)}>
          <SelectTrigger className="h-12 rounded-2xl">
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
      <ErrorAlert
        message={
          mutation.error instanceof Error
            ? mutation.error.message
            : mutation.error
              ? "Failed to change role."
              : null
        }
      />
      {mutation.isSuccess ? <p className="text-xs text-success">Role updated</p> : null}
      <Button type="submit" variant="hero" size="xl" disabled={mutation.isPending || !email.trim()}>
        {mutation.isPending ? "Updating..." : "Update role"}
      </Button>
    </form>
  )
}
