import { type FormEvent, useState } from "react"
import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getMyProfile, loginWithGateway, registerWithGateway } from "@/lib/api"

interface LoginPageProps {
  onSuccess: () => void
}

const USERNAME_BY_EMAIL_KEY = "lessley_username_by_email"

function readUsernameMap() {
  const raw = localStorage.getItem(USERNAME_BY_EMAIL_KEY)
  if (!raw) return {} as Record<string, string>
  try {
    return JSON.parse(raw) as Record<string, string>
  } catch {
    return {} as Record<string, string>
  }
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login")
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState("")
  const [successMessage, setSuccessMessage] = useState("")

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsLoading(true)
    setErrorMessage("")
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

        const usernameMap = readUsernameMap()
        usernameMap[normalizedEmail] = normalizedUsername
        localStorage.setItem(USERNAME_BY_EMAIL_KEY, JSON.stringify(usernameMap))

        setSuccessMessage("Registration successful. You can sign in now.")
        setMode("login")
      } else {
        const normalizedEmail = email.trim().toLowerCase()
        const usernameMap = readUsernameMap()
        const mappedUsername = usernameMap[normalizedEmail]

        const candidates = [mappedUsername, normalizedEmail].filter(Boolean) as string[]
        if (normalizedEmail.includes("@")) {
          const localPart = normalizedEmail.split("@")[0]
          if (localPart && !candidates.includes(localPart)) {
            candidates.push(localPart)
          }
        }

        let data: Awaited<ReturnType<typeof loginWithGateway>> | null = null
        let lastError: Error | null = null
        for (const candidate of candidates) {
          try {
            data = await loginWithGateway({
              userName: candidate,
              password,
            })
            break
          } catch (error) {
            lastError = error instanceof Error ? error : new Error("Request failed.")
            if (!lastError.message.includes("Unable to sign in with provided credentials.")) {
              throw lastError
            }
          }
        }

        if (!data) {
          throw lastError ?? new Error("Unable to sign in with provided credentials.")
        }

        localStorage.setItem("lessley_poc_session", "active")
        localStorage.setItem("lessley_access_token", data.accessToken)
        localStorage.setItem("lessley_refresh_token", data.refreshToken)
        const profile = await getMyProfile(data.accessToken).catch(() => null)
        localStorage.setItem(
          "lessley_username",
          profile?.userName ?? mappedUsername ?? candidates[0] ?? "User"
        )
        if (profile?.userId) {
          localStorage.setItem("lessley_user_id", profile.userId)
        }
        onSuccess()
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Request failed."
      setErrorMessage(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-slate-50 px-6 py-12">
      <Card className="w-full max-w-sm rounded-3xl border-0 bg-white shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
        <CardHeader className="px-7 pt-8">
          <CardTitle className="text-center text-3xl font-semibold tracking-tight">Lessley</CardTitle>
        </CardHeader>
        <CardContent className="px-7 pb-8">
          <div className="mb-7 grid grid-cols-2 gap-2 rounded-2xl bg-slate-100 p-1.5">
            <Button
              type="button"
              variant="ghost"
              className={
                mode === "login"
                  ? "min-h-11 rounded-xl border-0 bg-white text-slate-900 shadow-[0_2px_10px_rgba(15,23,42,0.10)] hover:bg-white focus-visible:ring-2 focus-visible:ring-slate-300"
                  : "min-h-11 rounded-xl border-0 bg-transparent text-slate-500 shadow-none hover:bg-slate-200/70 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-slate-300"
              }
              disabled={isLoading}
              onClick={() => setMode("login")}
            >
              Sign in
            </Button>
            <Button
              type="button"
              variant="ghost"
              className={
                mode === "register"
                  ? "min-h-11 rounded-xl border-0 bg-white text-slate-900 shadow-[0_2px_10px_rgba(15,23,42,0.10)] hover:bg-white focus-visible:ring-2 focus-visible:ring-slate-300"
                  : "min-h-11 rounded-xl border-0 bg-transparent text-slate-500 shadow-none hover:bg-slate-200/70 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-slate-300"
              }
              disabled={isLoading}
              onClick={() => setMode("register")}
            >
              Register
            </Button>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            {mode === "register" ? (
              <div className="space-y-2.5">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  type="text"
                  autoComplete="username"
                  required
                  className="min-h-12 border-0 bg-slate-100 px-4 shadow-none focus-visible:ring-slate-300"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  disabled={isLoading}
                />
              </div>
            ) : null}
            <div className="space-y-2.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                className="min-h-12 border-0 bg-slate-100 px-4 shadow-none focus-visible:ring-slate-300"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                className="min-h-12 border-0 bg-slate-100 px-4 shadow-none focus-visible:ring-slate-300"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={isLoading}
              />
            </div>
            {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}
            {successMessage ? <p className="text-sm text-emerald-600">{successMessage}</p> : null}
            <Button type="submit" className="min-h-12 w-full rounded-xl shadow-sm" disabled={isLoading}>
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
    </main>
  )
}
