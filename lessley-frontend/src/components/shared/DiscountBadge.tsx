import { useTranslation } from "react-i18next"

import { discountLabel } from "@/lib/deal-discount"
import { cn } from "@/lib/utils"
import type { DealDiscount } from "@/lib/types"

interface DiscountBadgeProps {
  discount: DealDiscount | null | undefined
  className?: string
}

/** The deal's headline discount, or nothing when the deal doesn't state one. */
export function DiscountBadge({ discount, className }: DiscountBadgeProps) {
  const { t } = useTranslation()
  const label = discountLabel(discount, t)

  if (!label) return null

  return (
    <span
      className={cn(
        "rounded-full bg-primary px-2.5 py-1 text-xs font-bold text-primary-foreground shadow-sm",
        className,
      )}
    >
      {label}
    </span>
  )
}
