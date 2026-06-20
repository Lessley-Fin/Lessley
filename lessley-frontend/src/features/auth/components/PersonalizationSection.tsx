import type { UseFormReturn } from "react-hook-form"

import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { CLUBS, MATCH_LEVELS, MCC_CATEGORIES, formatCategoryLabel } from "@/lib/constants"
import { cn, toggleArrayValue } from "@/lib/utils"
import type { RegisterValues } from "../schemas"

interface PersonalizationSectionProps {
  form: UseFormReturn<RegisterValues>
  isLoading: boolean
}

export function PersonalizationSection({ form, isLoading }: PersonalizationSectionProps) {
  return (
    <div className="space-y-4 rounded-2xl border border-slate-200/60 bg-slate-50/60 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Personalize (optional)
      </p>

      <FormField
        control={form.control}
        name="clubs"
        render={({ field }) => (
          <FormItem>
            <FormLabel className="text-sm">Loyalty clubs</FormLabel>
            <div className="grid grid-cols-2 gap-1.5">
              {CLUBS.map((club) => (
                <label
                  key={club.id}
                  className={cn(
                    "flex cursor-pointer select-none items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors",
                    field.value?.includes(club.id)
                      ? "bg-violet-50 text-violet-800"
                      : "text-slate-600 hover:bg-slate-100"
                  )}
                >
                  <input
                    type="checkbox"
                    className="size-3.5 rounded accent-violet-600"
                    checked={field.value?.includes(club.id) ?? false}
                    disabled={isLoading}
                    onChange={() => field.onChange(toggleArrayValue(field.value ?? [], club.id))}
                  />
                  {club.name}
                </label>
              ))}
            </div>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name="matchLevel"
        render={({ field }) => (
          <FormItem>
            <FormLabel className="text-sm">Match level</FormLabel>
            <Select onValueChange={field.onChange} value={field.value ?? ""}>
              <FormControl>
                <SelectTrigger className="fintech-input">
                  <SelectValue placeholder="Select match level" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {MATCH_LEVELS.map((level) => (
                  <SelectItem key={level} value={level}>
                    {level === "High" ? "High (top 25%)" : level === "Medium" ? "Medium (top 50%)" : "Low (top 75%)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name="mutedCategories"
        render={({ field }) => (
          <FormItem>
            <FormLabel className="text-sm">
              Muted categories
              {field.value && field.value.length > 0 ? (
                <span className="ml-1.5 font-normal text-slate-400">
                  ({field.value.length} selected)
                </span>
              ) : null}
            </FormLabel>
            <div className="max-h-40 space-y-0.5 overflow-y-auto rounded-xl border border-slate-200/80 bg-white p-2">
              {MCC_CATEGORIES.map((cat) => (
                <label
                  key={cat}
                  className={cn(
                    "flex cursor-pointer select-none items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                    field.value?.includes(cat)
                      ? "bg-red-50 text-red-700"
                      : "text-slate-600 hover:bg-slate-50"
                  )}
                >
                  <input
                    type="checkbox"
                    className="size-3.5 rounded accent-red-500"
                    checked={field.value?.includes(cat) ?? false}
                    disabled={isLoading}
                    onChange={() => field.onChange(toggleArrayValue(field.value ?? [], cat))}
                  />
                  {formatCategoryLabel(cat)}
                </label>
              ))}
            </div>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  )
}
