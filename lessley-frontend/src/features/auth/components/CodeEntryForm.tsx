import { useEffect, useState } from "react"
import { Loader2, ShieldCheck } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export const CODE_LENGTH = 6

interface CodeEntryFormProps {
  /** Address the code went to — shown so the user can spot a typo before waiting on an email. */
  email: string
  isWorking: boolean
  error?: string
  onSubmit: (code: string) => void
  /** Omit to hide the resend affordance (e.g. where re-requesting means restarting the flow). */
  onResend?: () => void
  isResending?: boolean
  /** Seconds the server makes callers wait between codes. */
  resendCooldownSeconds?: number
}

export function CodeEntryForm({
  email,
  isWorking,
  error,
  onSubmit,
  onResend,
  isResending = false,
  resendCooldownSeconds = 60,
}: CodeEntryFormProps) {
  const { t } = useTranslation()
  const [code, setCode] = useState("")
  const [secondsLeft, setSecondsLeft] = useState(resendCooldownSeconds)

  // Mirror the server's cooldown locally so the button is simply unavailable rather than
  // handing the user a 429 they can do nothing about.
  useEffect(() => {
    if (secondsLeft <= 0) return
    const timer = setTimeout(() => setSecondsLeft((s) => s - 1), 1000)
    return () => clearTimeout(timer)
  }, [secondsLeft])

  function handleResend() {
    setSecondsLeft(resendCooldownSeconds)
    setCode("")
    onResend?.()
  }

  return (
    <form
      className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit(code)
      }}
    >
      <p className="text-sm text-muted-foreground">
        {t("auth.code.sentTo", { length: CODE_LENGTH, email })}
      </p>
      <div className="space-y-1.5">
        <Label htmlFor="code">{t("auth.code.label")}</Label>
        <Input
          id="code"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={CODE_LENGTH}
          placeholder="000000"
          className="h-12 rounded-2xl text-center tracking-[0.4em]"
          value={code}
          // Digits only: pasting from a mail client often drags spaces along.
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          disabled={isWorking}
        />
      </div>
      <ErrorAlert message={error} />
      <Button type="submit" variant="hero" size="xl" disabled={code.length < CODE_LENGTH || isWorking}>
        {isWorking ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck />}
        {t("auth.code.verify")}
      </Button>
      {onResend ? (
        <Button
          type="button"
          variant="pill"
          size="xl"
          disabled={secondsLeft > 0 || isResending || isWorking}
          onClick={handleResend}
        >
          {isResending ? <Loader2 className="size-4 animate-spin" /> : null}
          {secondsLeft > 0
            ? t("auth.code.resendIn", { seconds: secondsLeft })
            : t("auth.code.resend")}
        </Button>
      ) : null}
    </form>
  )
}
