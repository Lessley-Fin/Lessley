import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"

const ITEM_KEYS = ["q1", "q2", "q3", "q4", "q5", "q6"] as const

export function QAView() {
  const { t } = useTranslation()
  const [openItem, setOpenItem] = useState<(typeof ITEM_KEYS)[number] | null>(null)

  return (
    <div className="space-y-2 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{t("settings.qa.title")}</p>
      <div className="divide-y divide-border">
        {ITEM_KEYS.map((key) => {
          const isOpen = openItem === key
          const answerKey = `a${key.slice(1)}`
          return (
            <div key={key}>
              <button
                type="button"
                onClick={() => setOpenItem(isOpen ? null : key)}
                aria-expanded={isOpen}
                className="flex w-full items-center justify-between gap-3 py-3 text-start text-sm font-medium"
              >
                {t(`settings.qa.${key}`)}
                <ChevronDown className={cn("size-4 shrink-0 text-muted-foreground transition-transform", isOpen && "rotate-180")} aria-hidden />
              </button>
              {isOpen ? (
                <p className="pb-3 text-sm text-muted-foreground">{t(`settings.qa.${answerKey}`)}</p>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
