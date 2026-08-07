import { useState } from "react"
import type { FormEvent } from "react"
import { Megaphone } from "lucide-react"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { formatCategoryLabel } from "@/lib/constants"
import { useMccCategories, useSendNotificationToGroup } from "../hooks"

const TEXTAREA_CLASS =
  "flex min-h-24 w-full resize-none rounded-2xl border border-input bg-transparent px-3 py-2 text-base shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"

export function NotifyGroupSlide() {
  const [tag, setTag] = useState("")
  const [message, setMessage] = useState("")
  const [dealId, setDealId] = useState("")
  const mutation = useSendNotificationToGroup()
  const { data: categories, isLoading: categoriesLoading, error: categoriesError } = useMccCategories()

  function submit(e: FormEvent) {
    e.preventDefault()
    mutation.mutate(
      { tag, message: message.trim(), dealId: dealId.trim() },
      {
        onSuccess: () => {
          setMessage("")
          setDealId("")
        },
      },
    )
  }

  return (
    <form
      onSubmit={submit}
      className="flex min-h-[380px] flex-col gap-4 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]"
    >
      <div className="flex items-center gap-2">
        <span className="flex size-9 items-center justify-center rounded-full bg-secondary">
          <Megaphone className="size-4 text-primary" aria-hidden />
        </span>
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          Broadcast notification to group
        </p>
      </div>
      <div className="space-y-1.5">
        <Label>Group category</Label>
        {categoriesError ? (
          <ErrorAlert message="Failed to load categories." />
        ) : (
          <Select value={tag} onValueChange={setTag} disabled={categoriesLoading}>
            <SelectTrigger className="h-12 rounded-2xl">
              <SelectValue placeholder={categoriesLoading ? "Loading..." : "Select a category"} />
            </SelectTrigger>
            <SelectContent>
              {(categories ?? []).map((c) => (
                <SelectItem key={c.category} value={c.category}>
                  {formatCategoryLabel(c.category)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-broadcast-message">Message</Label>
        <textarea
          id="admin-broadcast-message"
          placeholder="Notification message..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
          rows={3}
          className={TEXTAREA_CLASS}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-broadcast-deal">
          Deal ID <span className="text-muted-foreground">optional</span>
        </Label>
        <Input
          id="admin-broadcast-deal"
          placeholder="deal-abc-123"
          value={dealId}
          onChange={(e) => setDealId(e.target.value)}
          className="h-12 rounded-2xl"
        />
      </div>
      <ErrorAlert
        message={
          mutation.error instanceof Error
            ? mutation.error.message
            : mutation.error
              ? "Failed to broadcast notification."
              : null
        }
      />
      {mutation.isSuccess ? <p className="text-xs text-success">Notification broadcast</p> : null}
      <Button type="submit" variant="hero" size="xl" disabled={mutation.isPending || !tag || !message.trim()}>
        {mutation.isPending ? "Broadcasting..." : "Broadcast to group"}
      </Button>
    </form>
  )
}
