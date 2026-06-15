import { type FormEvent, useState } from "react"
import { Loader2, Eye, EyeOff, Lock, ShieldCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getMyProfile, loginWithGateway, registerWithGateway } from "@/lib/api"
import { cn } from "@/lib/utils"

interface LoginPageProps {
  onSuccess: () => void
}

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/")
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4)
  return atob(padded)
}

function getEmailFromAccessToken(accessToken: string) {
  try {
    const parts = accessToken.split(".")
    if (parts.length < 2) return ""
    const payload = JSON.parse(decodeBase64Url(parts[1])) as Record<string, unknown>
    const claimCandidates = [
      payload.email,
      payload.upn,
      payload.preferred_username,
      payload["http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"],
    ]
    const match = claimCandidates.find((item) => typeof item === "string" && item.includes("@"))
    return typeof match === "string" ? match.trim().toLowerCase() : ""
  } catch {
    return ""
  }
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login")
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessages, setErrorMessages] = useState<string[]>([])
  const [successMessage, setSuccessMessage] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsLoading(true)
    setErrorMessages([])
    setSuccessMessage("")

    try {
      if (mode === "register") {
        const normalizedEmail = email.trim().toLowerCase()
        const normalizedUsername = username.trim()
        await registerWithGateway({
          userName: normalizedUsername,
          email: normalizedEmail,
          password,
        })

        localStorage.setItem("lessley_user_email", normalizedEmail)

        setSuccessMessage("Registration successful. You can sign in now.")
        setMode("login")
      } else {
        const normalizedUsername = username.trim()
        const data = await loginWithGateway({
          userName: normalizedUsername,
          password,
        })

        localStorage.setItem("lessley_poc_session", "active")
        localStorage.setItem("lessley_access_token", data.accessToken)
        localStorage.setItem("lessley_refresh_token", data.refreshToken)
        const profile = await getMyProfile(data.accessToken).catch(() => null)
        localStorage.setItem("lessley_username", profile?.userName ?? normalizedUsername ?? "User")
        const resolvedEmail = profile?.email?.trim().toLowerCase() || getEmailFromAccessToken(data.accessToken)
        if (resolvedEmail) {
          localStorage.setItem("lessley_user_email", resolvedEmail)
        }
        if (profile?.userId) {
          localStorage.setItem("lessley_user_id", profile.userId)
        }
        onSuccess()
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Request failed."
      const parsed = message
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean)
      setErrorMessages(parsed.length ? parsed : [message])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="flex min-h-svh flex-col items-center justify-center px-5 py-12">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <span className="fintech-logo-mark size-12 text-lg" aria-hidden>
          L
        </span>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Lessley</h1>
          <p className="mt-1 text-sm text-slate-500">Personal finance, optimized for you</p>
        </div>
        <p className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700">
          <ShieldCheck className="size-3.5" aria-hidden />
          Bank-grade security
        </p>
      </div>

      <Card className="fintech-card w-full max-w-sm border-0 shadow-fintech-lg">
        <CardHeader className="px-6 pb-2 pt-6">
          <CardTitle className="text-center text-lg font-semibold text-slate-900">
            {mode === "login" ? "Sign in to your account" : "Create your account"}
          </CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-7">
          <div className="mb-6 grid grid-cols-2 gap-1 rounded-2xl border border-slate-200/80 bg-slate-100/80 p-1">
            <Button
              type="button"
              variant="ghost"
              className={cn(
                "min-h-11 rounded-xl border-0 text-sm font-semibold transition-all",
                mode === "login"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "bg-transparent text-slate-500 hover:text-slate-700"
              )}
              disabled={isLoading}
              onClick={() => setMode("login")}
            >
              Sign in
            </Button>
            <Button
              type="button"
              variant="ghost"
              className={cn(
                "min-h-11 rounded-xl border-0 text-sm font-semibold transition-all",
                mode === "register"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "bg-transparent text-slate-500 hover:text-slate-700"
              )}
              disabled={isLoading}
              onClick={() => setMode("register")}
            >
              Register
            </Button>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                required
                className="fintech-input"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                disabled={isLoading}
              />
            </div>
            {mode === "register" ? (
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  className="fintech-input"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  disabled={isLoading}
                />
              </div>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                  required
                  className="fintech-input pl-11 pr-12"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus:outline-none"
                  onClick={() => setShowPassword((s) => !s)}
                  disabled={isLoading}
                >
                  {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                </button>
              </div>
            </div>
            {errorMessages.length ? (
              <ul className="space-y-1 rounded-xl border border-red-200/80 bg-red-50/90 px-3 py-2 text-sm text-red-700">
                {errorMessages.map((item, index) => (
                  <li key={`${index}-${item}`}>{item}</li>
                ))}
              </ul>
            ) : null}
            {successMessage ? (
              <p className="rounded-xl border border-emerald-200/80 bg-emerald-50/90 px-3 py-2 text-sm text-emerald-800">
                {successMessage}
              </p>
            ) : null}
            <Button type="submit" className="min-h-12 w-full" disabled={isLoading}>
              {isLoading ? <Loader2 className="size-4 animate-spin" /> : null}
              {isLoading
                ? mode === "register"
                  ? "Creating account..."
                  : "Signing in..."
                : mode === "register"
                  ? "Create account"
                  : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <p className="mt-8 max-w-xs text-center text-xs leading-relaxed text-slate-400">
        Your credentials are encrypted in transit. We never store your banking passwords.
      </p>
    </main>
  )
}
