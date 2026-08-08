import i18n from "@/lib/i18n/config"

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "ILS",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatAmount(value: number | undefined, currency?: string) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-"
  if (currency && currency !== "ILS") {
    return `${value.toFixed(2)} ${currency}`
  }
  return currencyFormatter.format(value)
}

export function formatDate(value: string | undefined) {
  if (!value) return "-"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return "-"
  return parsed.toLocaleDateString()
}

export function formatRelativeTime(isoDate: string) {
  try {
    const date = new Date(isoDate)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60_000)

    if (diffMin < 1) return i18n.t("common.justNow")
    if (diffMin < 60) return i18n.t("common.minutesAgo", { count: diffMin })

    const diffHours = Math.floor(diffMin / 60)
    if (diffHours < 24) return i18n.t("common.hoursAgo", { count: diffHours })

    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return i18n.t("common.daysAgo", { count: diffDays })

    const locale = i18n.language === "he" ? "he-IL" : "en-GB"
    return date.toLocaleDateString(locale, { day: "2-digit", month: "2-digit", year: "2-digit" })
  } catch {
    return isoDate
  }
}

export function formatFitPercent(fitScore: number) {
  return `${Math.round(fitScore * 100)}%`
}

export function maskAccountNumber(value: string) {
  const digits = value.replace(/\s+/g, "")
  if (digits.length <= 8) return `•••• ${digits.slice(-4)}`
  return `${digits.slice(0, 6)}...${digits.slice(-4)}`
}
