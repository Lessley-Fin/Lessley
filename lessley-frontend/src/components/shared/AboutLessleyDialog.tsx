import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Gift, Layers, ShieldCheck, Sparkles, type LucideIcon } from "lucide-react"

import { CarouselDots } from "@/components/shared/CarouselDots"
import { Button } from "@/components/ui/button"
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel"
import { Dialog, DialogBody, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { getDirection } from "@/lib/i18n/config"

interface SlidePoint {
  title: string
  description: string
}

interface Slide {
  key: "what" | "gain" | "how" | "safety"
  icon: LucideIcon
  title: string
  subtitle: string
  points: SlidePoint[]
}

export function AboutLessleyDialog() {
  const { t, i18n } = useTranslation()
  const direction = getDirection(i18n.language)
  const [api, setApi] = useState<CarouselApi>()

  const SLIDES: Slide[] = [
    {
      key: "what",
      icon: Sparkles,
      title: t("common.aboutLessley.slides.what.title"),
      subtitle: t("common.aboutLessley.slides.what.subtitle"),
      points: [
        {
          title: t("common.aboutLessley.slides.what.point1Title"),
          description: t("common.aboutLessley.slides.what.point1Desc"),
        },
        {
          title: t("common.aboutLessley.slides.what.point2Title"),
          description: t("common.aboutLessley.slides.what.point2Desc"),
        },
      ],
    },
    {
      key: "gain",
      icon: Gift,
      title: t("common.aboutLessley.slides.gain.title"),
      subtitle: t("common.aboutLessley.slides.gain.subtitle"),
      points: [
        {
          title: t("common.aboutLessley.slides.gain.point1Title"),
          description: t("common.aboutLessley.slides.gain.point1Desc"),
        },
        {
          title: t("common.aboutLessley.slides.gain.point2Title"),
          description: t("common.aboutLessley.slides.gain.point2Desc"),
        },
        {
          title: t("common.aboutLessley.slides.gain.point3Title"),
          description: t("common.aboutLessley.slides.gain.point3Desc"),
        },
      ],
    },
    {
      key: "how",
      icon: Layers,
      title: t("common.aboutLessley.slides.how.title"),
      subtitle: t("common.aboutLessley.slides.how.subtitle"),
      points: [
        {
          title: t("common.aboutLessley.slides.how.point1Title"),
          description: t("common.aboutLessley.slides.how.point1Desc"),
        },
        {
          title: t("common.aboutLessley.slides.how.point2Title"),
          description: t("common.aboutLessley.slides.how.point2Desc"),
        },
        {
          title: t("common.aboutLessley.slides.how.point3Title"),
          description: t("common.aboutLessley.slides.how.point3Desc"),
        },
      ],
    },
    {
      key: "safety",
      icon: ShieldCheck,
      title: t("common.aboutLessley.slides.safety.title"),
      subtitle: t("common.aboutLessley.slides.safety.subtitle"),
      points: [
        {
          title: t("common.aboutLessley.slides.safety.point1Title"),
          description: t("common.aboutLessley.slides.safety.point1Desc"),
        },
        {
          title: t("common.aboutLessley.slides.safety.point2Title"),
          description: t("common.aboutLessley.slides.safety.point2Desc"),
        },
        {
          title: t("common.aboutLessley.slides.safety.point3Title"),
          description: t("common.aboutLessley.slides.safety.point3Desc"),
        },
      ],
    },
  ]

  const DOT_LABELS = SLIDES.map((slide) => t(`common.aboutLessley.carousel.${slide.key}`))

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="pill" size="sm">
          <Sparkles /> {t("common.aboutLessley.trigger")}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-sm rounded-3xl sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{t("common.aboutLessley.dialogTitle")}</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <Carousel setApi={setApi} opts={{ align: "start", direction }}>
            <CarouselContent>
              {SLIDES.map(({ key, icon: Icon, title, subtitle, points }) => (
                <CarouselItem key={key}>
                  <div className="flex min-h-[360px] flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
                    <div className="flex items-center gap-2 text-primary">
                      <Icon className="size-5" aria-hidden />
                    </div>
                    <div>
                      <p className="font-bold">{title}</p>
                      <p className="text-xs text-muted-foreground">{subtitle}</p>
                    </div>
                    <div className="space-y-2">
                      {points.map((point) => (
                        <div key={point.title} className="rounded-2xl bg-secondary p-3">
                          <p className="text-sm font-semibold">{point.title}</p>
                          <p className="text-xs text-muted-foreground">{point.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </CarouselItem>
              ))}
            </CarouselContent>
            <div className="mt-4 flex items-center justify-center gap-3">
              <CarouselPrevious aria-label={t("common.previousSlide")} />
              <CarouselDots api={api} labels={DOT_LABELS} />
              <CarouselNext aria-label={t("common.nextSlide")} />
            </div>
          </Carousel>
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}
