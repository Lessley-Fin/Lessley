import { useState } from "react"
import type { FormEvent } from "react"
import { Radio } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { useSendNotificationToAll } from "../hooks"

const TEXTAREA_CLASS =
  "flex min-h-24 w-full resize-none rounded-2xl border border-input bg-transparent px-3 py-2 text-base shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"

export function NotifyAllSlide() {
  const { t } = useTranslation()
  const [message, setMessage] = useState("")
  const mutation = useSendNotificationToAll()

  function submit(e: FormEvent) {
    e.preventDefault()
    mutation.mutate(
      { message: message.trim() },
      {
        onSuccess: () => {
          setMessage("")
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
          <Radio className="size-4 text-primary" aria-hidden />
        </span>
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {t("admin.notifyAll.heading")}
        </p>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-broadcast-all-message">{t("admin.common.message")}</Label>
        <textarea
          id="admin-broadcast-all-message"
          placeholder={t("admin.common.messagePlaceholder")}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
          rows={3}
          className={TEXTAREA_CLASS}
        />
      </div>
      <ErrorAlert
        message={
          mutation.error instanceof Error
            ? mutation.error.message
            : mutation.error
              ? t("admin.notifyAll.failed")
              : null
        }
      />
      {mutation.isSuccess ? <p className="text-xs text-success">{t("admin.notifyAll.success")}</p> : null}
      <Button type="submit" variant="hero" size="xl" disabled={mutation.isPending || !message.trim()}>
        {mutation.isPending ? t("admin.notifyAll.broadcasting") : t("admin.notifyAll.broadcastToAll")}
      </Button>
    </form>
  )
}
