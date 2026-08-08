import { useState } from "react"
import type { FormEvent } from "react"
import { UserCog } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useChangeUserRole } from "../hooks"
import type { UserRole } from "../api"

const USER_ROLES: UserRole[] = ["Viewer", "Operator", "Admin"]

export function ChangeRoleSlide() {
  const { t } = useTranslation()
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
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{t("admin.changeRole.heading")}</p>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-role-email">{t("admin.common.userEmail")}</Label>
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
        <Label>{t("admin.changeRole.role")}</Label>
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
              ? t("admin.changeRole.failed")
              : null
        }
      />
      {mutation.isSuccess ? <p className="text-xs text-success">{t("admin.changeRole.success")}</p> : null}
      <Button type="submit" variant="hero" size="xl" disabled={mutation.isPending || !email.trim()}>
        {mutation.isPending ? t("admin.changeRole.updating") : t("admin.changeRole.updateRole")}
      </Button>
    </form>
  )
}
