import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"

import { Carousel, CarouselContent, CarouselItem, type CarouselApi } from "@/components/ui/carousel"
import { getDirection } from "@/lib/i18n/config"
import { cn } from "@/lib/utils"
import { ChangeRoleSlide } from "./components/ChangeRoleSlide"
import { NotifyAllSlide } from "./components/NotifyAllSlide"
import { NotifyGroupSlide } from "./components/NotifyGroupSlide"
import { NotifyUserSlide } from "./components/NotifyUserSlide"
import { UpdateTagsSlide } from "./components/UpdateTagsSlide"

export function AdminPage() {
  const { t, i18n } = useTranslation()
  const direction = getDirection(i18n.language)
  const TABS = [
    t("admin.page.tabRole"),
    t("admin.page.tabTags"),
    t("admin.page.tabNotifyUser"),
    t("admin.page.tabBroadcast"),
    t("admin.page.tabBroadcastAll"),
  ]
  const [api, setApi] = useState<CarouselApi>()
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
    <div className="space-y-4 pb-2">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("admin.page.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("admin.page.subtitle")}</p>
      </div>

      <div className="no-scrollbar flex gap-1 overflow-x-auto rounded-full border border-border bg-card p-1">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            type="button"
            onClick={() => api?.scrollTo(i)}
            className={cn(
              "flex-1 whitespace-nowrap rounded-full px-3 py-2 text-xs font-semibold transition-colors",
              selected === i ? "surface-teal shadow-[var(--shadow-card)]" : "text-muted-foreground",
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      <Carousel setApi={setApi} opts={{ align: "start", direction }}>
        <CarouselContent>
          <CarouselItem>
            <ChangeRoleSlide />
          </CarouselItem>
          <CarouselItem>
            <UpdateTagsSlide />
          </CarouselItem>
          <CarouselItem>
            <NotifyUserSlide />
          </CarouselItem>
          <CarouselItem>
            <NotifyGroupSlide />
          </CarouselItem>
          <CarouselItem>
            <NotifyAllSlide />
          </CarouselItem>
        </CarouselContent>
      </Carousel>
    </div>
  )
}
