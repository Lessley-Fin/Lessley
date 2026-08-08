import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

interface StepIndicatorProps {
  steps: string[]
  currentIndex: number
}

export function StepIndicator({ steps, currentIndex }: StepIndicatorProps) {
  return (
    <div className="mb-8 flex items-center justify-center gap-2">
      {steps.map((label, index) => {
        const isDone = index < currentIndex
        const isCurrent = index === currentIndex
        return (
          <div key={label} className="flex items-center gap-2">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex size-8 items-center justify-center rounded-full text-xs font-bold transition-colors",
                  isDone && "surface-teal",
                  isCurrent && "surface-navy",
                  !isDone && !isCurrent && "bg-muted text-muted-foreground"
                )}
              >
                {isDone ? <Check className="size-4" aria-hidden /> : index + 1}
              </div>
              <span className="text-[10px] font-medium text-muted-foreground">{label}</span>
            </div>
            {index < steps.length - 1 ? (
              <span className={cn("mb-4 h-0.5 w-8 rounded-full", isDone ? "bg-primary" : "bg-border")} aria-hidden />
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
