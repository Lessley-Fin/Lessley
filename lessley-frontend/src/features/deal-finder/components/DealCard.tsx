import { useState } from "react"
import { Calendar, ChevronDown, ChevronUp, ExternalLink } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ClubLogoTile } from "@/components/shared/ClubLogoTile"
import { Card, CardContent } from "@/components/ui/card"
import { resolveClubName } from "@/lib/clubs"
import { cn } from "@/lib/utils"
import type { ClubDto, DealSearchResultItem } from "@/lib/types"

function ClubBadge({ clubs, clubId }: { clubs: ClubDto[]; clubId: string }) {
  const name = resolveClubName(clubs, clubId)
  if (!name) return null

  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-violet-100 py-0.5 pe-2 ps-0.5 text-[10px] font-semibold text-violet-700">
      <ClubLogoTile clubId={clubId} clubName={name} variant="inline" />
      {name}
    </span>
  )
}

export function DealCard({ item, clubs = [] }: { item: DealSearchResultItem; clubs?: ClubDto[] }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const { deal, store } = item

  return (
    <Card className="fintech-card border-0">
      <CardContent className="p-0">
        <button
          type="button"
          className="w-full px-4 py-3.5 text-start"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-label={expanded ? t("dealFinder.card.collapseDeal") : t("dealFinder.card.expandDeal")}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex flex-wrap items-center gap-1.5">
                <span className="truncate text-sm font-semibold text-slate-800">{store.name}</span>
                <ClubBadge clubs={clubs} clubId={deal.clubId} />
                {deal.redeemChannels.map((ch) => (
                  <span
                    key={ch}
                    className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium capitalize text-slate-500"
                  >
                    {ch.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
              <p className={cn("text-sm text-slate-600", !expanded && "line-clamp-2")}>
                {deal.title}
              </p>
              {!expanded ? (
                <p className="mt-1.5 flex items-center gap-1 text-xs text-slate-400">
                  <Calendar className="size-3" aria-hidden />
                  {new Date(deal.scrapedAt).toLocaleDateString()}
                </p>
              ) : null}
            </div>
            {expanded ? (
              <ChevronUp className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
            ) : (
              <ChevronDown className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
            )}
          </div>
        </button>

        {/* Quick CTA — rendered outside the expand button to avoid nested interactive elements */}
        {!expanded && deal.benefitUrl ? (
          <div className="px-4 pb-3">
            <a
              href={deal.benefitUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-600 hover:bg-blue-100"
            >
              {t("dealFinder.card.getDeal")}
              <ExternalLink className="size-3" aria-hidden />
            </a>
          </div>
        ) : null}

        {expanded ? (
          <div className="border-t border-slate-100 px-4 pb-4 pt-3">
            {deal.description && deal.description !== deal.title ? (
              <p className="mb-3 text-sm leading-relaxed text-slate-600">{deal.description}</p>
            ) : null}

            {deal.benefitUrl ? (
              <a
                href={deal.benefitUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="mb-3 flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-500 to-violet-500 py-2.5 text-sm font-semibold text-white shadow-sm hover:opacity-90"
              >
                {t("dealFinder.card.getDeal")}
                <ExternalLink className="size-3.5" aria-hidden />
              </a>
            ) : null}

            {deal.couponCode ? (
              <div className="mb-3 flex items-center gap-2 rounded-xl border border-dashed border-violet-300 bg-violet-50 px-3 py-2">
                <span className="flex-1 font-mono text-sm font-semibold text-violet-700">
                  {deal.couponCode}
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    void navigator.clipboard.writeText(deal.couponCode!)
                  }}
                  className="shrink-0 text-xs text-violet-500 hover:text-violet-700"
                >
                  {t("dealFinder.card.copy")}
                </button>
              </div>
            ) : null}

            {store.metadata.imageUrls.length > 0 ? (
              <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                {store.metadata.imageUrls.map((url, i) => (
                  <img
                    key={url + i}
                    src={url}
                    alt={`${store.name} image ${i + 1}`}
                    className="h-20 w-28 flex-shrink-0 rounded-xl object-cover"
                    onError={(e) => {
                      ;(e.target as HTMLImageElement).style.display = "none"
                    }}
                  />
                ))}
              </div>
            ) : null}

            <div className="space-y-1.5 text-xs text-slate-500">
              {store.metadata.storeUrl ? (
                <a
                  href={store.metadata.storeUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 font-medium text-blue-600 hover:text-blue-700"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink className="size-3" aria-hidden />
                  {t("dealFinder.card.visitStore")}
                </a>
              ) : null}
              <p className="flex items-center gap-1">
                <Calendar className="size-3" aria-hidden />
                {t("dealFinder.card.scraped", { date: new Date(deal.scrapedAt).toLocaleDateString() })}
              </p>
              {deal.resolvedAt ? (
                <p className="flex items-center gap-1">
                  <Calendar className="size-3" aria-hidden />
                  {t("dealFinder.card.resolved", { date: new Date(deal.resolvedAt).toLocaleDateString() })}
                </p>
              ) : null}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
