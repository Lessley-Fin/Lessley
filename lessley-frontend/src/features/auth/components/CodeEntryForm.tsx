import { useEffect, useState } from "react"
import { Loader2, ShieldCheck } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

import type { VerificationPolicy } from "../api"

export const CODE_LENGTH = 6

// Used only until the server's own policy arrives with the first response. These mirror
// VerificationConfig's defaults; the server value always wins once it is known.
const FALLBACK_POLICY: VerificationPolicy = {
  codeLength: CODE_LENGTH,
  codeTtlMinutes: 10,
  resendCooldownSeconds: 60,
}

interface CodeEntryFormProps {
  /** Address the code went to — shown so the user can spot a typo before waiting on an email. */
  email: string
  isWorking: boolean
  error?: string
  onSubmit: (code: string) => void
  /** Omit to hide the resend affordance (e.g. where re-requesting means restarting the flow). */
  onResend?: () => void
  isResending?: boolean
  /**
   * Code rules as reported by the server. Two separate timings live in here and they are not
   * the same thing: the code stays usable for codeTtlMinutes (10 by default), while
   * resendCooldownSeconds (60) only gates how soon a *replacement* may be requested.
   */
  policy?: VerificationPolicy
}

export function CodeEntryForm({
  email,
  isWorking,
  error,
  onSubmit,
  onResend,
  isResending = false,
  policy = FALLBACK_POLICY,
}: CodeEntryFormProps) {
  const resendCooldownSeconds = policy.resendCooldownSeconds
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
        {t("auth.code.sentTo", { length: policy.codeLength, email })}
      </p>
      <div className="space-y-1.5">
        <Label htmlFor="code">{t("auth.code.label")}</Label>
        <Input
          id="code"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={policy.codeLength}
          placeholder="000000"
          className="h-12 rounded-2xl text-center tracking-[0.4em]"
          value={code}
          // Digits only: pasting from a mail client often drags spaces along.
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          disabled={isWorking}
        />
      </div>
      {/* States the code's real lifetime. Without it the only number moving on this screen is
          the resend cooldown, which reads as if the code itself were about to expire. */}
      <p className="text-xs text-muted-foreground">
        {t("auth.code.validFor", { minutes: policy.codeTtlMinutes })}
      </p>
      <ErrorAlert message={error} />
      <Button
        type="submit"
        variant="hero"
        size="xl"
        disabled={code.length < policy.codeLength || isWorking}
      >
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
