import { Gem, Layers, Target } from "lucide-react"
import { useTranslation } from "react-i18next"

import { InfoDialog } from "@/components/shared/InfoDialog"

export function MatchLevelInfoDialog() {
  const { t } = useTranslation()
  const HIGHLIGHTS = [
    {
      icon: Layers,
      title: t("matchLevels.Low"),
      description: t("auth.register.matchLevel.explain.lowDesc"),
    },
    {
      icon: Target,
      title: t("matchLevels.Medium"),
      description: t("auth.register.matchLevel.explain.mediumDesc"),
    },
    {
      icon: Gem,
      title: t("matchLevels.High"),
      description: t("auth.register.matchLevel.explain.highDesc"),
    },
  ]

  return (
    <InfoDialog
      ariaLabel={t("auth.register.matchLevel.explain.ariaLabel")}
      title={t("auth.register.matchLevel.explain.title")}
      subtitle={t("auth.register.matchLevel.explain.subtitle")}
      highlights={HIGHLIGHTS}
    />
  )
}
