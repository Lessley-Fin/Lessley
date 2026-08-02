import type { LucideIcon } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  className?: string
  children?: React.ReactNode
}

export function EmptyState({ icon: Icon, title, description, className, children }: EmptyStateProps) {
  return (
    <Card className={cn("fintech-card border-0", className)}>
      <CardContent className="flex flex-col items-center gap-4 py-14 text-center" role="status">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-slate-100">
          <Icon className="size-7 text-slate-300" />
        </div>
        <div>
          <p className="font-semibold text-slate-800">{title}</p>
          {description ? (
            <p className="mt-1 text-sm text-slate-500">{description}</p>
          ) : null}
        </div>
        {children}
      </CardContent>
    </Card>
  )
}
