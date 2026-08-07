import { Check } from "lucide-react"

// No i18n backend exists yet — showing a working multi-language switcher would be dishonest,
// so this is a single selected row rather than the fake language list a pure demo would show.
export function LanguageView() {
  return (
    <div className="space-y-2 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Change language</p>
      <div className="flex w-full items-center justify-between rounded-2xl bg-accent p-3 text-sm font-medium text-accent-foreground">
        English
        <Check className="size-4" aria-hidden />
      </div>
      <p className="text-xs text-muted-foreground">More languages are on the way.</p>
    </div>
  )
}
