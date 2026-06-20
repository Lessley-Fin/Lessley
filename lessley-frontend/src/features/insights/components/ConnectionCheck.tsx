import { Card, CardContent } from "@/components/ui/card"

export function ConnectionCheck() {
  return (
    <Card className="fintech-card border-0">
      <CardContent className="flex items-center gap-3 py-5">
        <span className="size-4 animate-pulse rounded-full bg-blue-400/50" aria-hidden />
        <p className="text-sm text-slate-500">Verifying bank connection...</p>
      </CardContent>
    </Card>
  )
}
