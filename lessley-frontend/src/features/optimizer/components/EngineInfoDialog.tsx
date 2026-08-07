import { Box, CircleQuestionMark, Globe, Sparkles, Zap } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

const HIGHLIGHTS = [
  {
    icon: Sparkles,
    title: "Stacked savings",
    description: "Combine a store coupon with the right card benefit in one step.",
  },
  {
    icon: Box,
    title: "Exact product match",
    description: "We price the item you actually want, not a lookalike.",
  },
  {
    icon: Globe,
    title: "Ephemeral coupons",
    description: "Scraped from retailers and forums minutes after they appear.",
  },
]

export function EngineInfoDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="pill" size="icon" aria-label="How the engine works">
          <CircleQuestionMark />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-[340px] rounded-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="size-4 text-primary" aria-hidden />
            What you'll get
          </DialogTitle>
          <DialogDescription>How the engine works</DialogDescription>
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
