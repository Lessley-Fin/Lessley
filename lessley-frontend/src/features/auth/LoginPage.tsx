import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Loader2, Eye, EyeOff, Lock, ShieldCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getMyProfile, loginWithGateway, registerWithGateway } from "@/lib/api"
import { getEmailFromToken, storeSession } from "@/lib/auth"
import { CLUBS, MATCH_LEVELS, MCC_CATEGORIES, formatCategoryLabel } from "@/lib/constants"
import { cn } from "@/lib/utils"

// ── Schemas ────────────────────────────────────────────────────────────────────

const loginSchema = z.object({
  userName: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
})

// Mirrors ASP.NET Identity defaults + RegisterDto optional fields.
const registerSchema = z.object({
  userName: z
    .string()
    .min(3, "Must be at least 3 characters")
    .max(50, "Must be at most 50 characters")
    .regex(/^[a-zA-Z0-9\-._@+]+$/, "Only letters, digits, and - . _ @ + are allowed"),
  email: z.string().email("Please enter a valid email address"),
  password: z
    .string()
    .min(6, "Must be at least 6 characters")
    .regex(/[A-Z]/, "Must include an uppercase letter")
    .regex(/[a-z]/, "Must include a lowercase letter")
    .regex(/[0-9]/, "Must include a digit")
    .regex(/[^a-zA-Z0-9]/, "Must include a special character"),
  clubs: z.array(z.string()).optional(),
  matchLevel: z.enum(["Low", "Medium", "High"]).optional(),
  mutedCategories: z.array(z.string()).optional(),
})

type LoginValues = z.infer<typeof loginSchema>
type RegisterValues = z.infer<typeof registerSchema>

// ── Component ──────────────────────────────────────────────────────────────────

interface LoginPageProps {
  onSuccess: () => void
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login")
  const [showPassword, setShowPassword] = useState(false)

  const loginForm = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { userName: "", password: "" },
  })

  const registerForm = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { userName: "", email: "", password: "", clubs: [], matchLevel: undefined, mutedCategories: [] },
  })

  const switchMode = (next: "login" | "register") => {
    setMode(next)
    setShowPassword(false)
    if (next === "login") registerForm.reset()
    else loginForm.reset()
  }

  const isLoading =
    mode === "login" ? loginForm.formState.isSubmitting : registerForm.formState.isSubmitting

  // ── Submit handlers ──────────────────────────────────────────────────────────

  const handleLogin = loginForm.handleSubmit(async (values) => {
    try {
      const data = await loginWithGateway({ userName: values.userName, password: values.password })
      const profile = await getMyProfile(data.accessToken).catch(() => null)
      const resolvedEmail = profile?.email?.trim().toLowerCase() ?? getEmailFromToken(data.accessToken)
      storeSession({
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
        username: profile?.userName ?? values.userName,
        userId: resolvedEmail,
        email: resolvedEmail,
      })
      onSuccess()
    } catch (error) {
      loginForm.setError("root", {
        message: error instanceof Error ? error.message : "Sign-in failed. Please try again.",
      })
    }
  })

  const handleRegister = registerForm.handleSubmit(async (values) => {
    try {
      await registerWithGateway({
        userName: values.userName,
        email: values.email,
        password: values.password,
        clubs: values.clubs?.length ? values.clubs : undefined,
        matchLevel: values.matchLevel,
        mutedCategories: values.mutedCategories?.length ? values.mutedCategories : undefined,
      })
      const data = await loginWithGateway({ userName: values.userName, password: values.password })
      const profile = await getMyProfile(data.accessToken).catch(() => null)
      const resolvedEmail = profile?.email?.trim().toLowerCase() ?? values.email
      storeSession({
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
        username: profile?.userName ?? values.userName,
        userId: resolvedEmail,
        email: resolvedEmail,
      })
      onSuccess()
    } catch (error) {
      registerForm.setError("root", {
        message: error instanceof Error ? error.message : "Registration failed. Please try again.",
      })
    }
  })

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function toggleArrayValue(current: string[], value: string): string[] {
    return current.includes(value) ? current.filter((v) => v !== value) : [...current, value]
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  const serverError =
    mode === "login"
      ? loginForm.formState.errors.root?.message
      : registerForm.formState.errors.root?.message

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
          {/* Mode toggle */}
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
              onClick={() => switchMode("login")}
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
              onClick={() => switchMode("register")}
            >
              Register
            </Button>
          </div>

          {/* ── Login form ──────────────────────────────────────────────────── */}
          {mode === "login" ? (
            <Form key="login" {...loginForm}>
              <form className="space-y-5" onSubmit={handleLogin}>
                <FormField
                  control={loginForm.control}
                  name="userName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Username</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          autoComplete="username"
                          className="fintech-input"
                          disabled={isLoading}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={loginForm.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Password</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Lock className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                          <Input
                            {...field}
                            type={showPassword ? "text" : "password"}
                            autoComplete="current-password"
                            className="fintech-input pl-11 pr-12"
                            disabled={isLoading}
                          />
                          <button
                            type="button"
                            tabIndex={-1}
                            aria-label={showPassword ? "Hide password" : "Show password"}
                            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus:outline-none"
                            onClick={() => setShowPassword((s) => !s)}
                          >
                            {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                          </button>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                {serverError ? (
                  <p className="rounded-xl border border-red-200/80 bg-red-50/90 px-3 py-2 text-sm text-red-700">
                    {serverError}
                  </p>
                ) : null}
                <Button type="submit" className="min-h-12 w-full" disabled={isLoading}>
                  {isLoading ? <Loader2 className="size-4 animate-spin" /> : null}
                  {isLoading ? "Signing in..." : "Sign in"}
                </Button>
              </form>
            </Form>
          ) : (
            /* ── Register form ──────────────────────────────────────────────── */
            <Form key="register" {...registerForm}>
              <form className="space-y-5" onSubmit={handleRegister}>
                {/* Required fields */}
                <FormField
                  control={registerForm.control}
                  name="userName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Username</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          autoComplete="username"
                          className="fintech-input"
                          disabled={isLoading}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={registerForm.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          type="email"
                          autoComplete="email"
                          className="fintech-input"
                          disabled={isLoading}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={registerForm.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Password</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Lock className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                          <Input
                            {...field}
                            type={showPassword ? "text" : "password"}
                            autoComplete="new-password"
                            className="fintech-input pl-11 pr-12"
                            disabled={isLoading}
                          />
                          <button
                            type="button"
                            tabIndex={-1}
                            aria-label={showPassword ? "Hide password" : "Show password"}
                            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus:outline-none"
                            onClick={() => setShowPassword((s) => !s)}
                          >
                            {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                          </button>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Personalization — all optional */}
                <div className="space-y-4 rounded-2xl border border-slate-200/60 bg-slate-50/60 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Personalize (optional)
                  </p>

                  {/* Clubs */}
                  <FormField
                    control={registerForm.control}
                    name="clubs"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm">Loyalty clubs</FormLabel>
                        <div className="grid grid-cols-2 gap-1.5">
                          {CLUBS.map((club) => (
                            <label
                              key={club.id}
                              className={cn(
                                "flex cursor-pointer select-none items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors",
                                field.value?.includes(club.id)
                                  ? "bg-violet-50 text-violet-800"
                                  : "text-slate-600 hover:bg-slate-100"
                              )}
                            >
                              <input
                                type="checkbox"
                                className="size-3.5 rounded accent-violet-600"
                                checked={field.value?.includes(club.id) ?? false}
                                disabled={isLoading}
                                onChange={() => field.onChange(toggleArrayValue(field.value ?? [], club.id))}
                              />
                              {club.name}
                            </label>
                          ))}
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Match Level */}
                  <FormField
                    control={registerForm.control}
                    name="matchLevel"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm">Match level</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value ?? ""}>
                          <FormControl>
                            <SelectTrigger className="fintech-input">
                              <SelectValue placeholder="Select match level" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {MATCH_LEVELS.map((level) => (
                              <SelectItem key={level} value={level}>
                                {level === "High" ? "High (top 25%)" : level === "Medium" ? "Medium (top 50%)" : "Low (top 75%)"}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Muted Categories */}
                  <FormField
                    control={registerForm.control}
                    name="mutedCategories"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm">
                          Muted categories
                          {field.value && field.value.length > 0 ? (
                            <span className="ml-1.5 font-normal text-slate-400">
                              ({field.value.length} selected)
                            </span>
                          ) : null}
                        </FormLabel>
                        <div className="max-h-40 space-y-0.5 overflow-y-auto rounded-xl border border-slate-200/80 bg-white p-2">
                          {MCC_CATEGORIES.map((cat) => (
                            <label
                              key={cat}
                              className={cn(
                                "flex cursor-pointer select-none items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                                field.value?.includes(cat)
                                  ? "bg-red-50 text-red-700"
                                  : "text-slate-600 hover:bg-slate-50"
                              )}
                            >
                              <input
                                type="checkbox"
                                className="size-3.5 rounded accent-red-500"
                                checked={field.value?.includes(cat) ?? false}
                                disabled={isLoading}
                                onChange={() => field.onChange(toggleArrayValue(field.value ?? [], cat))}
                              />
                              {formatCategoryLabel(cat)}
                            </label>
                          ))}
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {serverError ? (
                  <p className="rounded-xl border border-red-200/80 bg-red-50/90 px-3 py-2 text-sm text-red-700">
                    {serverError}
                  </p>
                ) : null}
                <Button type="submit" className="min-h-12 w-full" disabled={isLoading}>
                  {isLoading ? <Loader2 className="size-4 animate-spin" /> : null}
                  {isLoading ? "Creating account..." : "Create account"}
                </Button>
              </form>
            </Form>
          )}
        </CardContent>
      </Card>

      <p className="mt-8 max-w-xs text-center text-xs leading-relaxed text-slate-400">
        Your credentials are encrypted in transit. We never store your banking passwords.
      </p>
    </main>
  )
}
