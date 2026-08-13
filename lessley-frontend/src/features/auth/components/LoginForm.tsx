import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { KeyRound, Loader2, Mail, Sparkles } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ROUTES } from "@/lib/routes"
import { loginWithGateway, requestLoginCode, verifyLoginCode } from "../api"
import { loginSchema, type LoginValues } from "../schemas"
import { usePostAuth } from "../usePostAuth"
import { CodeEntryForm } from "./CodeEntryForm"

// Password is the default; the emailed-code path is offered alongside it rather than replacing it.
type Mode = "password" | "email-request" | "email-code"

export function LoginForm() {
  const postAuth = usePostAuth()
  const [mode, setMode] = useState<Mode>("password")

  if (mode === "password") {
    return <PasswordLoginForm onUseEmailCode={() => setMode("email-request")} />
  }

  return (
    <EmailCodeLoginForm
      awaitingCode={mode === "email-code"}
      onCodeSent={() => setMode("email-code")}
      onUsePassword={() => setMode("password")}
      onAuthenticated={postAuth}
    />
  )
}

function PasswordLoginForm({ onUseEmailCode }: { onUseEmailCode: () => void }) {
  const { t } = useTranslation()
  const postAuth = usePostAuth()

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { userName: "", password: "" },
  })

  const isLoading = form.formState.isSubmitting
  const serverError = form.formState.errors.root?.message

  const handleSubmit = form.handleSubmit(async (values) => {
    try {
      const data = await loginWithGateway({ userName: values.userName, password: values.password })
      await postAuth({ userName: data.userName ?? values.userName, email: data.email })
    } catch (error) {
      form.setError("root", {
        message: error instanceof Error ? error.message : t("auth.login.signInFailed"),
      })
    }
  })

  return (
    <Form {...form}>
      <form className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]" onSubmit={handleSubmit}>
        <FormField
          control={form.control}
          name="userName"
          render={({ field }) => (
            <FormItem className="space-y-1.5">
              <FormLabel>{t("auth.login.username")}</FormLabel>
              <FormControl>
                <Input {...field} autoComplete="username" className="h-12 rounded-2xl" disabled={isLoading} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem className="space-y-1.5">
              <FormLabel>{t("auth.login.password")}</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  type="password"
                  autoComplete="current-password"
                  className="h-12 rounded-2xl"
                  disabled={isLoading}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <Link to={ROUTES.FORGOT_PASSWORD} className="text-xs font-medium text-primary hover:underline">
            {t("auth.login.forgotPassword")}
          </Link>
        </div>
        <ErrorAlert message={serverError} />
        <Button type="submit" variant="hero" size="xl" disabled={isLoading}>
          {isLoading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles />}
          {isLoading ? t("auth.login.signingIn") : t("auth.login.signIn")}
        </Button>
        <Button type="button" variant="pill" size="xl" disabled={isLoading} onClick={onUseEmailCode}>
          <Mail />
          {t("auth.login.useEmailCode")}
        </Button>
        <Button asChild variant="pill" size="xl">
          <Link to={ROUTES.REGISTER}>{t("auth.login.createAccount")}</Link>
        </Button>
      </form>
    </Form>
  )
}

interface EmailCodeLoginFormProps {
  awaitingCode: boolean
  onCodeSent: () => void
  onUsePassword: () => void
  onAuthenticated: (profile: { userName: string; email: string }) => Promise<void>
}

function EmailCodeLoginForm({
  awaitingCode,
  onCodeSent,
  onUsePassword,
  onAuthenticated,
}: EmailCodeLoginFormProps) {
  const { t } = useTranslation()
  const [email, setEmail] = useState("")
  const [isWorking, setIsWorking] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [error, setError] = useState<string | undefined>()

  async function sendCode(resending: boolean) {
    const setBusy = resending ? setIsResending : setIsWorking
    setBusy(true)
    setError(undefined)
    try {
      await requestLoginCode({ email })
      // The answer is the same for unknown addresses, so the UI always advances — it never
      // becomes a way to check who has an account.
      if (!resending) onCodeSent()
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.login.codeSendFailed"))
    } finally {
      setBusy(false)
    }
  }

  async function handleVerify(code: string) {
    setIsWorking(true)
    setError(undefined)
    try {
      const profile = await verifyLoginCode({ email, code })
      await onAuthenticated({ userName: profile.userName, email: profile.email ?? email })
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.code.verifyFailed"))
    } finally {
      setIsWorking(false)
    }
  }

  if (awaitingCode) {
    return (
      <div className="space-y-3">
        <CodeEntryForm
          email={email}
          isWorking={isWorking}
          isResending={isResending}
          error={error}
          onSubmit={handleVerify}
          onResend={() => void sendCode(true)}
        />
        <Button type="button" variant="pill" size="xl" onClick={onUsePassword}>
          <KeyRound />
          {t("auth.login.usePassword")}
        </Button>
      </div>
    )
  }

  return (
    <form
      className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]"
      onSubmit={(e) => {
        e.preventDefault()
        void sendCode(false)
      }}
    >
      <p className="text-sm text-muted-foreground">{t("auth.login.emailCodeIntro")}</p>
      <div className="space-y-1.5">
        <Label htmlFor="otp-email">{t("auth.forgotPassword.email")}</Label>
        <Input
          id="otp-email"
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
        {isWorking ? <Loader2 className="size-4 animate-spin" /> : <Mail />}
        {t("auth.login.sendSignInCode")}
      </Button>
      <Button type="button" variant="pill" size="xl" disabled={isWorking} onClick={onUsePassword}>
        <KeyRound />
        {t("auth.login.usePassword")}
      </Button>
    </form>
  )
}
