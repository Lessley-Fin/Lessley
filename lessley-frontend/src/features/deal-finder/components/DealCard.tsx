import { useState } from "react"
import { Calendar, ChevronDown, ChevronUp, ExternalLink } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { CLUBS } from "@/lib/constants"
import { cn } from "@/lib/utils"
import type { DealSearchResultItem } from "@/lib/types"

function getClubName(clubId: string): string {
  return CLUBS.find((c) => c.id === clubId)?.name ?? clubId
}

function ClubBadge({ clubId }: { clubId: string }) {
  return (
    <span className="shrink-0 rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
      {getClubName(clubId)}
    </span>
  )
}

export function DealCard({ item }: { item: DealSearchResultItem }) {
  const [expanded, setExpanded] = useState(false)
  const { deal, store } = item

  return (
    <Card className="fintech-card border-0">
      <CardContent className="p-0">
        <button
          type="button"
          className="w-full px-4 py-3.5 text-left"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-label={expanded ? "Collapse deal" : "Expand deal"}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex flex-wrap items-center gap-1.5">
                <ClubBadge clubId={deal.clubId} />
                <span className="truncate text-sm font-semibold text-slate-800">{store.name}</span>
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

        {expanded ? (
          <div className="border-t border-slate-100 px-4 pb-4 pt-3">
            {deal.description ? (
              <p className="mb-3 text-sm leading-relaxed text-slate-600">{deal.description}</p>
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
                  Visit store
                </a>
              ) : null}
              <p className="flex items-center gap-1">
                <Calendar className="size-3" aria-hidden />
                Scraped: {new Date(deal.scrapedAt).toLocaleDateString()}
              </p>
              {deal.resolvedAt ? (
                <p className="flex items-center gap-1">
                  <Calendar className="size-3" aria-hidden />
                  Resolved: {new Date(deal.resolvedAt).toLocaleDateString()}
                </p>
              ) : null}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
