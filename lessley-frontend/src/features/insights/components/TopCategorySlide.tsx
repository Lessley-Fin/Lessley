import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { INSIGHTS_DEFAULTS, emojiForCategoryLabel, formatCategoryLabel } from "@/lib/constants"
import { formatAmount } from "@/lib/formatters"
import type { SpendingCategoryInsight } from "@/lib/types"

interface TopCategorySlideProps {
  categories: SpendingCategoryInsight[]
}

export function TopCategorySlide({ categories }: TopCategorySlideProps) {
  const topCategories = categories.slice(0, INSIGHTS_DEFAULTS.CAROUSEL_CATEGORY_LIMIT)

  if (topCategories.length === 0) {
    return (
      <CarouselSlideCard title="Top category" subtitle="Where the money goes">
        <p className="text-sm text-muted-foreground">No category data yet for this period.</p>
      </CarouselSlideCard>
    )
  }

  return (
    <CarouselSlideCard title="Top category" subtitle="Where the money goes">
      <div className="flex items-center gap-3">
        <ResponsiveContainer width="45%" height={140}>
          <PieChart>
            <Pie data={topCategories} dataKey="total_amount" innerRadius={34} outerRadius={58} paddingAngle={3}>
              {topCategories.map((c, i) => (
                <Cell key={c.category} fill={`hsl(var(--chart-${(i % 5) + 1}))`} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <ul className="no-scrollbar max-h-36 flex-1 space-y-1.5 overflow-y-auto text-sm">
          {topCategories.map((c, i) => (
            <li key={c.category} className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 truncate">
                <span className="size-2.5 shrink-0 rounded-full" style={{ background: `hsl(var(--chart-${(i % 5) + 1}))` }} />
                {emojiForCategoryLabel(c.category)} {formatCategoryLabel(c.category)}
              </span>
              <span className="font-semibold">{formatAmount(c.total_amount)}</span>
            </li>
          ))}
        </ul>
      </div>
    </CarouselSlideCard>
  )
}
