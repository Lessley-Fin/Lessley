import { cn } from "@/lib/utils"

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded-xl bg-slate-200/60", className)}
      aria-hidden
    />
  )
}

export function CardSkeleton({ className }: SkeletonProps) {
  return (
    <div className={cn("fintech-card space-y-3 rounded-2xl border-0 p-5", className)}>
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  )
}
