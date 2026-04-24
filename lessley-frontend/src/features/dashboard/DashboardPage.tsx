import { useEffect, useState } from "react"
import { ArrowRight, CheckCircle2, LogOut } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FeedbackDrawerForm } from "@/features/feedback/FeedbackDrawerForm"
import { getOpenFinanceConnectionUrl, hasOpenFinanceConnection } from "@/lib/api"
import type { FeedbackItem } from "@/lib/types"

interface DashboardPageProps {
  username: string
  userId: string
  feedbackItems: FeedbackItem[]
  onCreateFeedback: (item: FeedbackItem) => void
  onLogout: () => void
}

export function DashboardPage({
  username,
  userId,
  feedbackItems,
  onCreateFeedback,
  onLogout,
}: DashboardPageProps) {
  const [checkingConnection, setCheckingConnection] = useState(true)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionHint, setConnectionHint] = useState("")

  useEffect(() => {
    let isMounted = true

    const runCheck = async () => {
      if (!userId) {
        if (isMounted) {
          setIsConnected(false)
          setCheckingConnection(false)
        }
        return
      }

      const accessToken = localStorage.getItem("lessley_access_token") ?? undefined
      const connected = await hasOpenFinanceConnection(userId, accessToken)
      if (isMounted) {
        setIsConnected(connected)
        setCheckingConnection(false)
        if (connected) {
          setConnectionHint("")
        }
      }
    }

    void runCheck()

    const handleFocus = () => {
      void runCheck()
    }

    window.addEventListener("focus", handleFocus)
    return () => {
      isMounted = false
      window.removeEventListener("focus", handleFocus)
    }
  }, [userId])

  const handleConnectOpenBanking = () => {
    if (!userId) {
      setConnectionHint("We are still loading your account. Please try again in a second.")
      return
    }
    const returnUrl = window.location.href
    window.location.assign(getOpenFinanceConnectionUrl(userId, returnUrl))
  }

  return (
    <main className="mx-auto min-h-svh w-full max-w-md bg-slate-50 pb-28">
      <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between bg-slate-50/95 px-6 pt-3 backdrop-blur">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Lessley</h1>
          <p className="text-sm text-slate-500">Hi {username}</p>
        </div>
        <Button
          className="min-h-11 min-w-11 rounded-xl border-0 bg-white px-3 text-slate-700 shadow-sm hover:bg-slate-100"
          variant="ghost"
          onClick={onLogout}
          aria-label="Logout"
        >
          <LogOut className="size-4" />
          Logout
        </Button>
      </header>

      <section className="space-y-4 px-6 pb-6 pt-4">
        {checkingConnection ? (
          <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
            <CardContent className="pt-5 text-sm text-slate-500">Checking bank connection...</CardContent>
          </Card>
        ) : isConnected ? (
          <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
            <CardContent className="flex items-center gap-2 pt-5 text-sm text-emerald-700">
              <CheckCircle2 className="size-4" />
              Open Banking connected
            </CardContent>
          </Card>
        ) : (
          <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
            <CardHeader className="pb-2 pt-5">
              <CardTitle className="text-base">Connect your bank</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              <p className="text-sm text-slate-500">
                You are not connected to Open Banking yet. Connect now to sync transactions.
              </p>
              {connectionHint ? <p className="text-xs text-slate-500">{connectionHint}</p> : null}
              <Button className="min-h-11 rounded-xl" onClick={handleConnectOpenBanking}>
                Connect Open Banking
                <ArrowRight className="size-4" />
              </Button>
            </CardContent>
          </Card>
        )}

        {feedbackItems.map((item) => (
          <Card
            key={item.id}
            className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]"
          >
            <CardHeader className="pb-2 pt-5">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="line-clamp-2 text-base">{item.summary}</CardTitle>
                <Badge className="border-0 bg-slate-100 text-slate-700">{item.category}</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-0 text-xs text-slate-500">{item.createdAt}</CardContent>
          </Card>
        ))}
      </section>

      <FeedbackDrawerForm onSubmitted={onCreateFeedback} />
    </main>
  )
}
