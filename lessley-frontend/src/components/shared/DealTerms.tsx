import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"

export interface DealTermsProps {
  minimumPurchase?: number | null
  minSpend?: number | null
  maxDiscountAmount?: number | null
  maxUsesPerTransaction?: number | null
  maxUsesPerMonth?: number | null
  /** true / "yes" / null — the optimizer and the Gateway disagree on the wire type. */
  membershipRequired?: boolean | string | null
  /** Which programme the membership is in, when the deal names one. */
  membershipSource?: string | null
  redeemChannels?: string[]
  /** The source's own legal text, shown verbatim. */
  fineprint?: string | null
}

function isRequired(value?: boolean | string | null) {
  return value === true || value === "yes"
}

/**
 * The conditions attached to a benefit — caps, minimums and eligibility —
 * followed by the source's own small print. Rows only appear when the deal
 * actually states them, so a sparsely-described deal renders nothing rather
 * than a wall of "unknown".
 */
export function DealTerms(props: DealTermsProps) {
  const { t } = useTranslation()

  const rows: { label: string; value: string }[] = []

  const minimum = props.minimumPurchase ?? props.minSpend
  if (typeof minimum === "number" && minimum > 0) {
    rows.push({ label: t("shared.dealTerms.minimumPurchase"), value: formatAmount(minimum) })
  }
  if (typeof props.maxDiscountAmount === "number" && props.maxDiscountAmount > 0) {
    rows.push({ label: t("shared.dealTerms.maxDiscount"), value: formatAmount(props.maxDiscountAmount) })
  }
  if (typeof props.maxUsesPerTransaction === "number") {
    rows.push({
      label: t("shared.dealTerms.usesPerTransaction"),
      value: String(props.maxUsesPerTransaction),
    })
  }
  if (typeof props.maxUsesPerMonth === "number") {
    rows.push({ label: t("shared.dealTerms.usesPerMonth"), value: String(props.maxUsesPerMonth) })
  }
  if (isRequired(props.membershipRequired)) {
    rows.push({
      label: t("shared.dealTerms.membershipRequired"),
      value: props.membershipSource ?? t("shared.dealTerms.membershipRequiredValue"),
    })
  }
  if (props.redeemChannels && props.redeemChannels.length > 0) {
    rows.push({
      label: t("shared.dealTerms.redeemAt"),
      value: props.redeemChannels
        .map((channel) =>
          t(`shared.dealTerms.channels.${channel}`, { defaultValue: channel.replace(/_/g, " ") }),
        )
        .join(", "),
    })
  }

  if (rows.length === 0 && !props.fineprint) return null

  return (
    <div className="space-y-3">
      {rows.length > 0 ? (
        <div>
          <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {t("shared.dealTerms.title")}
          </p>
          <div className="space-y-1 text-sm">
            {rows.map((row) => (
              <div key={row.label} className="flex items-baseline justify-between gap-3">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="font-semibold capitalize">{row.value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {props.fineprint ? (
        <div>
          <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {t("shared.dealTerms.fineprintTitle")}
          </p>
          <p className="whitespace-pre-line text-xs leading-relaxed text-muted-foreground">
            {props.fineprint}
          </p>
        </div>
      ) : null}
    </div>
  )
}
