import { CalendarDays } from "lucide-react"

import { BarRow } from "@/components/shared/BarRow"
import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { Card, CardContent } from "@/components/ui/card"
import type { SpendingByDayInsight } from "@/lib/types"

interface SpendingByDayCardProps {
  spendingByDay: SpendingByDayInsight[]
}

export function SpendingByDayCard({ spendingByDay }: SpendingByDayCardProps) {
  if (spendingByDay.length === 0) return null

  const maxValue = Math.max(...spendingByDay.map((item) => item.total_amount), 0)

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={CalendarDays}
        iconColor="blue"
        title="Spending by day of week"
      />
      <CardContent className="space-y-3 px-5 pb-5 pt-0">
        {spendingByDay.map((item) => (
          <BarRow
            key={item.day}
            label={item.day}
            value={item.total_amount}
            maxValue={maxValue}
            colorClassName="bg-blue-500"
          />
        ))}
      </CardContent>
    </Card>
  )
}
