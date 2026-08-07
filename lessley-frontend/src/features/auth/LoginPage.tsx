import { LoginForm } from "./components/LoginForm"

export function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col justify-center px-6 py-10">
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="surface-teal mb-4 flex size-16 items-center justify-center rounded-3xl text-2xl font-bold shadow-[var(--shadow-card)]">
            L
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Welcome back</h1>
          <p className="mt-1 text-sm text-muted-foreground">Financial autopilot for every purchase</p>
        </div>
        <LoginForm />
      </div>
    </div>
  )
}
