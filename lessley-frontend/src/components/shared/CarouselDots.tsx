import { useEffect, useState } from "react"

import type { CarouselApi } from "@/components/ui/carousel"
import { cn } from "@/lib/utils"

interface CarouselDotsProps {
  api: CarouselApi | undefined
  labels: string[]
}

export function CarouselDots({ api, labels }: CarouselDotsProps) {
  const [selected, setSelected] = useState(0)

  useEffect(() => {
    if (!api) return
    const onSelect = () => setSelected(api.selectedScrollSnap())
    onSelect()
    api.on("select", onSelect)
    return () => {
      api.off("select", onSelect)
    }
  }, [api])

  return (
    <div className="flex justify-center gap-1.5">
      {labels.map((label, i) => (
        <button
          key={label}
          type="button"
          aria-label={label}
          onClick={() => api?.scrollTo(i)}
          className={cn("h-1.5 rounded-full transition-all", i === selected ? "w-6 bg-primary" : "w-1.5 bg-border")}
        />
      ))}
    </div>
  )
}
