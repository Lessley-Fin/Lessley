import { fintech } from "@/lib/fintech-styles"
import { cn } from "@/lib/utils"

interface ListRowProps {
  variant?: "default" | "accent"
  className?: string
  children: React.ReactNode
}

export function ListRow({ variant = "default", className, children }: ListRowProps) {
  return (
    <div className={cn(variant === "accent" ? fintech.listRowAccent : fintech.listRow, className)}>
      {children}
    </div>
  )
}
