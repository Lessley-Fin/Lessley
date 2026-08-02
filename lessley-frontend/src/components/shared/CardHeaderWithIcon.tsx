import type { LucideIcon } from "lucide-react"

import { CardHeader, CardTitle } from "@/components/ui/card"
import { fintech } from "@/lib/fintech-styles"
import { cn } from "@/lib/utils"

const iconColorMap = {
  blue: fintech.iconWrapBlue,
  violet: fintech.iconWrapViolet,
  amber: fintech.iconWrapAmber,
  emerald: fintech.iconWrapEmerald,
} as const

interface CardHeaderWithIconProps {
  icon: LucideIcon
  iconColor?: keyof typeof iconColorMap
  title: string
  subtitle?: string
  className?: string
}

export function CardHeaderWithIcon({
  icon: Icon,
  iconColor = "blue",
  title,
  subtitle,
  className,
}: CardHeaderWithIconProps) {
  return (
    <CardHeader className={cn("flex-row items-center gap-3 space-y-0 px-5 pb-2 pt-5", className)}>
      <div className={iconColorMap[iconColor]}>
        <Icon className="size-4" />
      </div>
      <div>
        <CardTitle className={fintech.sectionTitle}>{title}</CardTitle>
        {subtitle ? <p className="text-xs text-slate-500">{subtitle}</p> : null}
      </div>
    </CardHeader>
  )
}
