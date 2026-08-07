import type { ReactNode } from "react"
import { ShieldCheck } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface AuthShellProps {
  title: string
  children: ReactNode
}

export function AuthShell({ title, children }: AuthShellProps) {
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
        <p className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
          <ShieldCheck className="size-3.5" aria-hidden />
          Bank-grade security
        </p>
      </div>

      <Card className="fintech-card w-full max-w-sm border-0 shadow-fintech-lg">
        <CardHeader className="px-6 pb-2 pt-6">
          <CardTitle className="text-center text-lg font-semibold text-slate-900">{title}</CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-7">{children}</CardContent>
      </Card>

      <p className="mt-8 max-w-xs text-center text-xs leading-relaxed text-slate-400">
        Your credentials are encrypted in transit. We never store your banking passwords.
      </p>
    </main>
  )
}
