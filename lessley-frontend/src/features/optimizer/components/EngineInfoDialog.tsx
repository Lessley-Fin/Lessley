import { Box, Globe, Sparkles, Zap } from "lucide-react"
import { useTranslation } from "react-i18next"

import { InfoDialog } from "@/components/shared/InfoDialog"

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
    <InfoDialog
      ariaLabel={t("optimizer.engineInfoDialog.ariaLabel")}
      title={t("optimizer.engineInfoDialog.title")}
      subtitle={t("optimizer.engineInfoDialog.subtitle")}
      titleIcon={Zap}
      highlights={HIGHLIGHTS}
    />
  )
}
