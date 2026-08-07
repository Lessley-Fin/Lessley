import { useState } from "react"
import type { FormEvent } from "react"
import { Tag } from "lucide-react"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useUpdateUserTags } from "../hooks"
import { TagChipInput } from "./TagChipInput"

export function UpdateTagsSlide() {
  const [email, setEmail] = useState("")
  const [tags, setTags] = useState<string[]>([])
  const mutation = useUpdateUserTags()

  function submit(e: FormEvent) {
    e.preventDefault()
    mutation.mutate({ email: email.trim(), tags })
  }

  return (
    <form
      onSubmit={submit}
      className="flex min-h-[380px] flex-col gap-4 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]"
    >
      <div className="flex items-center gap-2">
        <span className="flex size-9 items-center justify-center rounded-full bg-secondary">
          <Tag className="size-4 text-primary" aria-hidden />
        </span>
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Assign user tags</p>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="admin-tags-email">User email</Label>
        <Input
          id="admin-tags-email"
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="h-12 rounded-2xl"
        />
      </div>
      <div className="space-y-1.5">
        <Label>Tags</Label>
        <TagChipInput value={tags} onChange={setTags} placeholder="e.g. high-spender" />
      </div>
      <ErrorAlert
        message={
          mutation.error instanceof Error ? mutation.error.message : mutation.error ? "Failed to update tags." : null
        }
      />
      {mutation.isSuccess ? <p className="text-xs text-success">Tags updated</p> : null}
      <Button type="submit" variant="hero" size="xl" disabled={mutation.isPending || !email.trim()}>
        {mutation.isPending ? "Saving..." : "Save tags"}
      </Button>
    </form>
  )
}
