import { Loader2 } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface LoadingCardProps {
  message?: string
  variant?: "spinner" | "pulse"
  className?: string
}

export function LoadingCard({ message, variant = "spinner", className }: LoadingCardProps) {
  return (
    <Card className={cn("fintech-card border-0", className)}>
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        {variant === "spinner" ? (
          <Loader2 className="size-7 animate-spin text-violet-400" />
        ) : (
          <span className="size-6 animate-pulse rounded-full bg-violet-400/50" aria-hidden />
        )}
        {message ? <p className="text-sm text-slate-500">{message}</p> : null}
      </CardContent>
    </Card>
  )
}
