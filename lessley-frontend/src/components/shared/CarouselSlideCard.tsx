import type { ReactNode } from "react"

interface CarouselSlideCardProps {
  title: string
  subtitle: string
  children: ReactNode
}

export function CarouselSlideCard({ title, subtitle, children }: CarouselSlideCardProps) {
  return (
    <div className="flex h-[330px] flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <div>
        <p className="font-bold">{title}</p>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
      <div className="min-h-0 flex-1 space-y-2">{children}</div>
    </div>
  )
}
