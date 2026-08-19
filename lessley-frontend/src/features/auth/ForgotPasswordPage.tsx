import { useState } from "react"
import { ArrowLeft, Loader2, MailCheck } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { ROUTES } from "@/lib/routes"
import type { VerificationPolicy } from "./api"
import { requestPasswordReset, resetPassword, verifyPasswordResetCode } from "./api"
import { CodeEntryForm } from "./components/CodeEntryForm"
import { passwordSchema } from "./schemas"

const STEP = { EMAIL: 0, CODE: 1, PASSWORD: 2 } as const

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const SUBTITLES = [
    t("auth.forgotPassword.subtitleSendCode"),
    t("auth.forgotPassword.subtitleEnterCode"),
    t("auth.forgotPassword.subtitleChoosePassword"),
  ]
  const navigate = useNavigate()
  const [step, setStep] = useState<number>(STEP.EMAIL)
  const [isWorking, setIsWorking] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [error, setError] = useState<string | undefined>()
  const [email, setEmail] = useState("")
  // Handed out once the emailed code is verified; the final call carries this instead of the code.
  const [resetTicket, setResetTicket] = useState("")
  const [policy, setPolicy] = useState<VerificationPolicy | undefined>()
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  async function handleSendCode() {
    setIsWorking(true)
    setError(undefined)
    try {
      const { policy: codePolicy } = await requestPasswordReset({ email })
      setPolicy(codePolicy)
      // The response is identical for unknown addresses on purpose, so the UI moves on either
      // way rather than revealing whether the account exists.
      setStep(STEP.CODE)
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.forgotPassword.sendFailed"))
    } finally {
      setIsWorking(false)
    }
  }

  async function handleResendCode() {
    setIsResending(true)
    setError(undefined)
    try {
      const { policy: codePolicy } = await requestPasswordReset({ email })
      setPolicy(codePolicy)
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.code.resendFailed"))
    } finally {
      setIsResending(false)
    }
  }

  async function handleVerifyCode(code: string) {
    setIsWorking(true)
    setError(undefined)
    try {
      const { resetTicket: ticket } = await verifyPasswordResetCode({ email, code })
      setResetTicket(ticket)
      setStep(STEP.PASSWORD)
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.code.verifyFailed"))
    } finally {
      setIsWorking(false)
    }
  }

  async function handleSavePassword() {
    setIsWorking(true)
    setError(undefined)
    try {
      await resetPassword({ email, resetTicket, newPassword: password })
      toast.success(t("auth.forgotPassword.passwordUpdated"))
      navigate(ROUTES.LOGIN)
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.forgotPassword.resetFailed"))
    } finally {
      setIsWorking(false)
    }
  }

  const passwordsMismatch = confirmPassword.length > 0 && password !== confirmPassword
  const canSavePassword = passwordSchema.safeParse(password).success && password === confirmPassword

  return (
    <div className="flex min-h-full flex-col px-6 py-8">
      <Link to={ROUTES.LOGIN} className="mb-6 flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden /> {t("auth.forgotPassword.backToSignIn")}
      </Link>
      <div className="mx-auto w-full max-w-sm">
        <h1 className="text-2xl font-bold tracking-tight">{t("auth.forgotPassword.resetPassword")}</h1>
        <p className="mt-1 mb-6 text-sm text-muted-foreground">{SUBTITLES[step]}</p>

        {step === STEP.EMAIL ? (
          <form
            className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]"
            onSubmit={(e) => {
              e.preventDefault()
              void handleSendCode()
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="email">{t("auth.forgotPassword.email")}</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                className="h-12 rounded-2xl"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isWorking}
              />
            </div>
            <ErrorAlert message={error} />
            <Button type="submit" variant="hero" size="xl" disabled={!email || isWorking}>
              {isWorking ? <Loader2 className="size-4 animate-spin" /> : <MailCheck />}
              {t("auth.forgotPassword.sendCode")}
            </Button>
          </form>
        ) : null}

        {step === STEP.CODE ? (
          <CodeEntryForm
            email={email}
            isWorking={isWorking}
            isResending={isResending}
            error={error}
            policy={policy}
            onSubmit={handleVerifyCode}
            onResend={handleResendCode}
          />
        ) : null}

        {step === STEP.PASSWORD ? (
          <form
            className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]"
            onSubmit={(e) => {
              e.preventDefault()
              void handleSavePassword()
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="pw">{t("auth.forgotPassword.newPassword")}</Label>
              <PasswordInput
                id="pw"
                autoComplete="new-password"
                className="h-12 rounded-2xl"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isWorking}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pw2">{t("auth.forgotPassword.confirmNewPassword")}</Label>
              <PasswordInput
                id="pw2"
                autoComplete="new-password"
                className="h-12 rounded-2xl"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isWorking}
              />
            </div>
            {passwordsMismatch ? (
              <p className="text-xs font-medium text-destructive">{t("auth.forgotPassword.passwordsMismatch")}</p>
            ) : null}
            <ErrorAlert message={error} />
            <Button type="submit" variant="hero" size="xl" disabled={!canSavePassword || isWorking}>
              {isWorking ? <Loader2 className="size-4 animate-spin" /> : null}
              {t("auth.forgotPassword.savePassword")}
            </Button>
          </form>
        ) : null}
      </div>
    </div>
  )
}
