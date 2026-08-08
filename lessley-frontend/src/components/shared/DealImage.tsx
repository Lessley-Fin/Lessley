import { useState } from "react"

import { cn } from "@/lib/utils"

interface DealImageProps {
  /** Candidate images, best first — the first one that loads is shown. */
  urls: string[]
  alt: string
  /** Rendered when there is no image, or every candidate fails to load. */
  fallback: React.ReactNode
  className?: string
  imageClassName?: string
}

/**
 * Deal imagery is scraped off third-party sites, so a dead URL is routine
 * rather than exceptional: each failure advances to the next candidate and the
 * fallback only appears once they are all exhausted.
 */
export function DealImage({ urls, alt, fallback, className, imageClassName }: DealImageProps) {
  const [index, setIndex] = useState(0)
  const url = urls[index]

  if (!url) {
    return <div className={cn("flex items-center justify-center", className)}>{fallback}</div>
  }

  return (
    <div className={cn("overflow-hidden", className)}>
      <img
        src={url}
        alt={alt}
        loading="lazy"
        onError={() => setIndex((i) => i + 1)}
        className={cn("size-full object-cover", imageClassName)}
      />
    </div>
  )
}
