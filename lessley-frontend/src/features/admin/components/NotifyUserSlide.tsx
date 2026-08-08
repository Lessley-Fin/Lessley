import { useState } from "react"
import type { FormEvent } from "react"
import { Send } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useSendNotificationToUser } from "../hooks"

const TEXTAREA_CLASS =
  "flex min-h-24 w-full resize-none rounded-2xl border border-input bg-transparent px-3 py-2 text-base shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"

export function NotifyUserSlide() {
  const { t } = useTranslation()
  const [email, setEmail] = useState("")
  const [message, setMessage] = useState("")
  const [dealId, setDealId] = useState("")
  const mutation = useSendNotificationToUser()

  function submit(e: FormEvent) {
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
    <form
      onSubmit={submit}
      className="flex min-h-[380px] flex-col gap-4 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]"
    >
      <div className="flex items-center gap-2">
        <span className="flex size-9 items-center justify-center rounded-full bg-secondary">
          <Send className="size-4 text-primary" aria-hidden />
        </span>
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {t("admin.notifyUser.heading")}
        </p>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-notify-email">{t("admin.notifyUser.recipientEmail")}</Label>
        <Input
          id="admin-notify-email"
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="h-12 rounded-2xl"
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-notify-message">{t("admin.common.message")}</Label>
        <textarea
          id="admin-notify-message"
          placeholder={t("admin.common.messagePlaceholder")}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
          rows={3}
          className={TEXTAREA_CLASS}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-notify-deal">
          {t("admin.common.dealId")} <span className="text-muted-foreground">{t("admin.common.optional")}</span>
        </Label>
        <Input
          id="admin-notify-deal"
          placeholder="deal-abc-123"
          value={dealId}
          onChange={(e) => setDealId(e.target.value)}
          className="h-12 rounded-2xl"
        />
      </div>
      <ErrorAlert
        message={
          mutation.error instanceof Error
            ? mutation.error.message
            : mutation.error
              ? t("admin.notifyUser.failed")
              : null
        }
      />
      {mutation.isSuccess ? <p className="text-xs text-success">{t("admin.notifyUser.success")}</p> : null}
      <Button type="submit" variant="hero" size="xl" disabled={mutation.isPending || !email.trim() || !message.trim()}>
        {mutation.isPending ? t("admin.notifyUser.sending") : t("admin.notifyUser.sendNotification")}
      </Button>
    </form>
  )
}
