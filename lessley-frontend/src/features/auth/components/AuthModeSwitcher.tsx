import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface AuthModeSwitcherProps {
  mode: "login" | "register"
  disabled: boolean
  onModeChange: (mode: "login" | "register") => void
}

export function AuthModeSwitcher({ mode, disabled, onModeChange }: AuthModeSwitcherProps) {
  return (
    <div className="mb-6 grid grid-cols-2 gap-1 rounded-2xl border border-slate-200/80 bg-slate-100/80 p-1">
      <Button
        type="button"
        variant="ghost"
        className={cn(
          "min-h-11 rounded-xl border-0 text-sm font-semibold transition-all",
          mode === "login"
            ? "bg-white text-slate-900 shadow-sm"
            : "bg-transparent text-slate-500 hover:text-slate-700"
        )}
        disabled={disabled}
        onClick={() => onModeChange("login")}
      >
        Sign in
      </Button>
      <Button
        type="button"
        variant="ghost"
        className={cn(
          "min-h-11 rounded-xl border-0 text-sm font-semibold transition-all",
          mode === "register"
            ? "bg-white text-slate-900 shadow-sm"
            : "bg-transparent text-slate-500 hover:text-slate-700"
        )}
        disabled={disabled}
        onClick={() => onModeChange("register")}
      >
        Register
      </Button>
    </div>
  )
}
