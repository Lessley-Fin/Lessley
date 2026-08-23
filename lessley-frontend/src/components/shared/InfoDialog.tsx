import type { ReactNode } from "react"
import { CircleQuestionMark, type LucideIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export interface InfoDialogHighlight {
  icon: LucideIcon
  title: string
  description: string
}

interface InfoDialogProps {
  ariaLabel: string
  title: string
  subtitle?: string
  titleIcon?: LucideIcon
  highlights?: InfoDialogHighlight[]
  children?: ReactNode
  className?: string
}

export function InfoDialog({
  ariaLabel,
  title,
  subtitle,
  titleIcon: TitleIcon,
  highlights,
  children,
  className,
}: InfoDialogProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="pill" size="icon" aria-label={ariaLabel}>
          <CircleQuestionMark />
        </Button>
      </DialogTrigger>
      <DialogContent className={className}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {TitleIcon ? <TitleIcon className="size-4 shrink-0 text-primary" aria-hidden /> : null}
            {title}
          </DialogTitle>
          {subtitle ? <DialogDescription>{subtitle}</DialogDescription> : null}
        </DialogHeader>
        {/* Highlights and children are caller-supplied and unbounded in length —
            they belong in the scrolling body, or a long list gets clipped by the
            dialog's overflow-hidden on a short viewport. */}
        <DialogBody>
          {highlights ? (
            <div className="space-y-2">
              {highlights.map(({ icon: Icon, title: highlightTitle, description }) => (
                <div key={highlightTitle} className="flex gap-3 rounded-2xl bg-secondary p-3">
                  <Icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{highlightTitle}</p>
                    <p className="text-xs text-muted-foreground">{description}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          {children}
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}
