import * as React from "react"
import useEmblaCarousel, { type UseEmblaCarouselType } from "embla-carousel-react"
import { ArrowLeft, ArrowRight } from "lucide-react"

import { Button, type ButtonProps } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type CarouselApi = UseEmblaCarouselType[1]
type UseCarouselParameters = Parameters<typeof useEmblaCarousel>
type CarouselOptions = UseCarouselParameters[0]
type CarouselPlugin = UseCarouselParameters[1]

interface CarouselProps {
  opts?: CarouselOptions
  plugins?: CarouselPlugin
  setApi?: (api: CarouselApi) => void
}

interface CarouselContextProps extends CarouselProps {
  carouselRef: ReturnType<typeof useEmblaCarousel>[0]
  api: ReturnType<typeof useEmblaCarousel>[1]
  canScrollPrev: boolean
  canScrollNext: boolean
  scrollPrev: () => void
  scrollNext: () => void
}

const CarouselContext = React.createContext<CarouselContextProps | null>(null)

function useCarousel() {
  const context = React.useContext(CarouselContext)
  if (!context) {
    throw new Error("useCarousel must be used within a <Carousel />")
  }
  return context
}

// Embla's api is an external system (it mutates and emits its own events), so we read its
// scroll-bounds via useSyncExternalStore instead of mirroring them into local state —
// avoids the "setState synchronously in an effect" footgun on the initial subscribe.
function subscribeToApi(api: CarouselApi, callback: () => void) {
  if (!api) return () => {}
  api.on("select", callback)
  api.on("reInit", callback)
  return () => {
    api.off("select", callback)
    api.off("reInit", callback)
  }
}

const Carousel = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & CarouselProps
>(({ opts, plugins, setApi, className, children, ...props }, ref) => {
  const [carouselRef, api] = useEmblaCarousel(opts, plugins)

  const canScrollPrev = React.useSyncExternalStore(
    React.useCallback((callback) => subscribeToApi(api, callback), [api]),
    React.useCallback(() => api?.canScrollPrev() ?? false, [api])
  )
  const canScrollNext = React.useSyncExternalStore(
    React.useCallback((callback) => subscribeToApi(api, callback), [api]),
    React.useCallback(() => api?.canScrollNext() ?? false, [api])
  )

  React.useEffect(() => {
    if (!api || !setApi) return
    setApi(api)
  }, [api, setApi])

  return (
    <CarouselContext.Provider
      value={{
        carouselRef,
        api,
        opts,
        plugins,
        setApi,
        canScrollPrev,
        canScrollNext,
        scrollPrev: () => api?.scrollPrev(),
        scrollNext: () => api?.scrollNext(),
      }}
    >
      <div ref={ref} className={cn("relative", className)} role="region" aria-roledescription="carousel" {...props}>
        {children}
      </div>
    </CarouselContext.Provider>
  )
})
Carousel.displayName = "Carousel"

const CarouselContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    const { carouselRef } = useCarousel()
    return (
      <div ref={carouselRef} className="overflow-hidden">
        <div ref={ref} className={cn("flex -ms-4", className)} {...props} />
      </div>
    )
  }
)
CarouselContent.displayName = "CarouselContent"

const CarouselItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      role="group"
      aria-roledescription="slide"
      className={cn("min-w-0 shrink-0 grow-0 basis-full ps-4", className)}
      {...props}
    />
  )
)
CarouselItem.displayName = "CarouselItem"

const CarouselPrevious = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "pill", size = "icon", "aria-label": ariaLabel = "Previous slide", ...props }, ref) => {
    const { opts, canScrollPrev, scrollPrev } = useCarousel()
    const isRtl = opts?.direction === "rtl"
    return (
      <Button
        ref={ref}
        type="button"
        variant={variant}
        size={size}
        className={cn("size-9 shrink-0", className)}
        disabled={!canScrollPrev}
        onClick={scrollPrev}
        aria-label={ariaLabel}
        {...props}
      >
        {isRtl ? <ArrowRight aria-hidden /> : <ArrowLeft aria-hidden />}
      </Button>
    )
  }
)
CarouselPrevious.displayName = "CarouselPrevious"

const CarouselNext = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "pill", size = "icon", "aria-label": ariaLabel = "Next slide", ...props }, ref) => {
    const { opts, canScrollNext, scrollNext } = useCarousel()
    const isRtl = opts?.direction === "rtl"
    return (
      <Button
        ref={ref}
        type="button"
        variant={variant}
        size={size}
        className={cn("size-9 shrink-0", className)}
        disabled={!canScrollNext}
        onClick={scrollNext}
        aria-label={ariaLabel}
        {...props}
      >
        {isRtl ? <ArrowLeft aria-hidden /> : <ArrowRight aria-hidden />}
      </Button>
    )
  }
)
CarouselNext.displayName = "CarouselNext"

export {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselPrevious,
  CarouselNext,
  useCarousel,
  type CarouselApi,
}
