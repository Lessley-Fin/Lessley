import { ArrowLeft } from "lucide-react"

import { Button } from "@/components/ui/button"
import { fintech } from "@/lib/fintech-styles"

interface PageHeaderProps {
  title: string
  subtitle?: string
  onBack: () => void
  children?: React.ReactNode
}

export function PageHeader({ title, subtitle, onBack, children }: PageHeaderProps) {
  return (
    <header className={fintech.subheader}>
      <Button
        type="button"
        variant="ghost"
        className="min-h-10 min-w-10 rounded-xl border border-slate-200/80 bg-white px-0 shadow-sm"
        onClick={onBack}
        aria-label="Back"
      >
        <ArrowLeft className="size-4" />
      </Button>
      <div className="min-w-0 flex-1">
        <h2 className="text-lg font-bold tracking-tight text-slate-900">{title}</h2>
        {subtitle ? <p className="text-xs text-slate-500">{subtitle}</p> : null}
      </div>
      {children}
    </header>
  )
}
