import * as React from "react"
import { Eye, EyeOff } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"

const PasswordInput = React.forwardRef<HTMLInputElement, Omit<React.ComponentProps<"input">, "type">>(
  ({ className, ...props }, ref) => {
    const { t } = useTranslation()
    const [visible, setVisible] = React.useState(false)

    return (
      <div className="relative">
        <Input
          {...props}
          ref={ref}
          type={visible ? "text" : "password"}
          className={cn("pe-10", className)}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          disabled={props.disabled}
          aria-label={visible ? t("common.hidePassword") : t("common.showPassword")}
          className="absolute inset-y-0 end-0 flex items-center px-3 text-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
        >
          {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
    )
  }
)
PasswordInput.displayName = "PasswordInput"

export { PasswordInput }
