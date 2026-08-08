import { Box, CircleQuestionMark, Globe, Sparkles, Zap } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export function EngineInfoDialog() {
  const { t } = useTranslation()
  const HIGHLIGHTS = [
    {
      icon: Sparkles,
      title: t("optimizer.engineInfoDialog.highlight1Title"),
      description: t("optimizer.engineInfoDialog.highlight1Desc"),
    },
    {
      icon: Box,
      title: t("optimizer.engineInfoDialog.highlight2Title"),
      description: t("optimizer.engineInfoDialog.highlight2Desc"),
    },
    {
      icon: Globe,
      title: t("optimizer.engineInfoDialog.highlight3Title"),
      description: t("optimizer.engineInfoDialog.highlight3Desc"),
    },
  ]

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="pill" size="icon" aria-label={t("optimizer.engineInfoDialog.ariaLabel")}>
          <CircleQuestionMark />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-[340px] rounded-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="size-4 text-primary" aria-hidden />
            {t("optimizer.engineInfoDialog.title")}
          </DialogTitle>
          <DialogDescription>{t("optimizer.engineInfoDialog.subtitle")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          {HIGHLIGHTS.map(({ icon: Icon, title, description }) => (
            <div key={title} className="flex gap-3 rounded-2xl bg-secondary p-3">
              <Icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
              <div>
                <p className="text-sm font-semibold">{title}</p>
                <p className="text-xs text-muted-foreground">{description}</p>
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
