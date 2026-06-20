import { CalendarRange } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { Card, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TIME_RANGE_OPTIONS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"

interface AnalysisPeriodCardProps {
  value: number
  onChange: (days: number) => void
}

export function AnalysisPeriodCard({ value, onChange }: AnalysisPeriodCardProps) {
  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon icon={CalendarRange} iconColor="blue" title="Analysis period" />
      <CardContent className="px-5 pb-5 pt-0">
        <Label htmlFor="insights-time-range" className="sr-only">
          Time range
        </Label>
        <Select
          value={String(value)}
          onValueChange={(v) => onChange(Number(v))}
        >
          <SelectTrigger id="insights-time-range" className={fintech.select}>
            <SelectValue placeholder="Choose period" />
          </SelectTrigger>
          <SelectContent className="z-[100]">
            {TIME_RANGE_OPTIONS.map((opt) => (
              <SelectItem key={opt.days} value={String(opt.days)}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardContent>
    </Card>
  )
}
