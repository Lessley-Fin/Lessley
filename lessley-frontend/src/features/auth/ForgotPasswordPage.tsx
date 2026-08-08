import { useState } from "react"
import { ArrowLeft, Loader2, MailCheck, ShieldCheck } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ROUTES } from "@/lib/routes"
import { passwordSchema } from "./schemas"

const CODE_LENGTH = 6

// No backend endpoint exists for password reset yet (no email-sending infrastructure in the
// Gateway), so this whole flow is a client-only stub: it walks the same 3 steps a real flow
// would, but never calls the network or changes any real password.
export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const SUBTITLES = [
    t("auth.forgotPassword.subtitleSendCode"),
    t("auth.forgotPassword.subtitleEnterCode"),
    t("auth.forgotPassword.subtitleChoosePassword"),
  ]
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [isWorking, setIsWorking] = useState(false)
  const [email, setEmail] = useState("")
  const [code, setCode] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  async function handleSendCode() {
    setIsWorking(true)
    await new Promise((resolve) => setTimeout(resolve, 500))
    setIsWorking(false)
    setStep(1)
  }

  async function handleVerifyCode() {
    setIsWorking(true)
    await new Promise((resolve) => setTimeout(resolve, 500))
    setIsWorking(false)
    setStep(2)
  }

  async function handleSavePassword() {
    setIsWorking(true)
    await new Promise((resolve) => setTimeout(resolve, 500))
    setIsWorking(false)
    toast.success(t("auth.forgotPassword.passwordUpdated"))
    navigate(ROUTES.LOGIN)
  }

  const passwordsMismatch = confirmPassword.length > 0 && password !== confirmPassword
  const canSavePassword = passwordSchema.safeParse(password).success && password === confirmPassword

  return (
    <div className="flex min-h-screen flex-col px-6 py-8">
      <Link to={ROUTES.LOGIN} className="mb-6 flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden /> {t("auth.forgotPassword.backToSignIn")}
      </Link>
      <div className="mx-auto w-full max-w-sm">
        <h1 className="text-2xl font-bold tracking-tight">{t("auth.forgotPassword.resetPassword")}</h1>
        <p className="mt-1 mb-6 text-sm text-muted-foreground">
          {step === 1
            ? t("auth.forgotPassword.enterCodeSentTo", {
                length: CODE_LENGTH,
                email: email || t("auth.forgotPassword.yourEmail"),
              })
            : SUBTITLES[step]}
        </p>

        <div className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]">
          {step === 0 ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="email">{t("auth.forgotPassword.email")}</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  className="h-12 rounded-2xl"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isWorking}
                />
              </div>
              <Button type="button" variant="hero" size="xl" disabled={!email || isWorking} onClick={handleSendCode}>
                {isWorking ? <Loader2 className="size-4 animate-spin" /> : <MailCheck />}
                {t("auth.forgotPassword.sendCode")}
              </Button>
            </>
          ) : null}

          {step === 1 ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="code">{t("auth.forgotPassword.verificationCode")}</Label>
                <Input
                  id="code"
                  inputMode="numeric"
                  placeholder="000000"
                  className="h-12 rounded-2xl tracking-[0.4em]"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  disabled={isWorking}
                />
              </div>
              <Button
                type="button"
                variant="hero"
                size="xl"
                disabled={code.length < CODE_LENGTH || isWorking}
                onClick={handleVerifyCode}
              >
                {isWorking ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck />}
                {t("auth.forgotPassword.verify")}
              </Button>
            </>
          ) : null}

          {step === 2 ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="pw">{t("auth.forgotPassword.newPassword")}</Label>
                <Input
                  id="pw"
                  type="password"
                  className="h-12 rounded-2xl"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isWorking}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pw2">{t("auth.forgotPassword.confirmNewPassword")}</Label>
                <Input
                  id="pw2"
                  type="password"
                  className="h-12 rounded-2xl"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isWorking}
                />
              </div>
              {passwordsMismatch ? (
                <p className="text-xs font-medium text-destructive">{t("auth.forgotPassword.passwordsMismatch")}</p>
              ) : null}
              <Button
                type="button"
                variant="hero"
                size="xl"
                disabled={!canSavePassword || isWorking}
                onClick={handleSavePassword}
              >
                {isWorking ? <Loader2 className="size-4 animate-spin" /> : null}
                {t("auth.forgotPassword.savePassword")}
              </Button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
