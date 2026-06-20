import { cn } from "@/lib/utils"

interface ErrorAlertProps {
  message: string | undefined | null
  className?: string
}

export function ErrorAlert({ message, className }: ErrorAlertProps) {
  if (!message) return null

  return (
    <p className={cn("rounded-xl border border-red-200/80 bg-red-50/90 px-3 py-2 text-sm text-red-700", className)}>
      {message}
    </p>
  )
}
