import { formatAmount } from "@/lib/formatters"
import type { DealDiscount } from "@/lib/types"

type Translate = (key: string, options?: Record<string, unknown>) => string

/**
 * The headline number of a deal. Which field is set decides what the number
 * *means*, so each reward type gets its own wording — "30% off" and "₪30 off"
 * come from the same `value: 30` upstream and must not be conflated.
 * Returns null when the deal states no usable discount.
 */
export function discountLabel(discount: DealDiscount | null | undefined, t: Translate): string | null {
  if (!discount) return null

  if (typeof discount.percentOff === "number" && discount.percentOff > 0) {
    const percent = discount.percentOff * 100
    return t("shared.discount.percentOff", {
      percent: `${percent.toFixed(percent < 10 ? 1 : 0).replace(/\.0$/, "")}%`,
    })
  }
  if (typeof discount.amountOff === "number" && discount.amountOff > 0) {
    return t("shared.discount.amountOff", { amount: formatAmount(discount.amountOff) })
  }
  if (typeof discount.fixedPrice === "number" && discount.fixedPrice > 0) {
    return t("shared.discount.fixedPrice", { amount: formatAmount(discount.fixedPrice) })
  }
  return null
}
