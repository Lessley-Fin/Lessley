import * as React from "react"
import { Eye, EyeOff } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"

/**
 * iOS Safari and Android Chrome echo the last character typed into an `input[type=password]`
 * for a second or two. That is keyboard/OS behaviour attached to the password input type
 * itself — no CSS or JS switch turns it off — so the only way to stop the echo is to not be
 * a password input, and to mask a plain text field with `-webkit-text-security` instead.
 *
 * The cost is real: Chrome's built-in password manager keys off `type="password"` and will
 * no longer offer to save or fill these fields. Extension-based managers (1Password,
 * Bitwarden) mostly still match on the `autocomplete` attribute, which we keep passing through.
 * Flip this constant to `false` to go back to a native password field and accept the echo.
 */
const MASK_WITH_TEXT_SECURITY = true

/**
 * Firefox only shipped `-webkit-text-security` in 141. On anything older the declaration is
 * dropped and a plain text input would render the password in the clear, so we feature-detect
 * and fall back to a real password field rather than risk that.
 */
const canMaskTextInput =
  typeof CSS !== "undefined" &&
  typeof CSS.supports === "function" &&
  CSS.supports("-webkit-text-security", "disc")

const PasswordInput = React.forwardRef<HTMLInputElement, Omit<React.ComponentProps<"input">, "type">>(
  ({ className, onBlur, ...props }, ref) => {
    const { t } = useTranslation()
    const [visible, setVisible] = React.useState(false)

    const usesTextSecurity = MASK_WITH_TEXT_SECURITY && canMaskTextInput

    return (
      <div className="relative">
        <Input
          {...props}
          ref={ref}
          // When masking via CSS the field is always a text input and `.password-masked`
          // does the hiding; otherwise fall back to toggling the native input type.
          type={usesTextSecurity || visible ? "text" : "password"}
          /* The field spends its life as a text input now, so the mobile keyboard would
             otherwise autocorrect the password, offer it in the suggestion strip, and learn
             it into the personal dictionary. spellCheck also keeps it off remote checkers. */
          autoCorrect="off"
          autoCapitalize="none"
          spellCheck={false}
          /* Never leave a password unmasked on screen once the user has moved on. */
          onBlur={(e) => {
            setVisible(false)
            onBlur?.(e)
          }}
          className={cn("pe-10", usesTextSecurity && !visible && "password-masked", className)}
        />
        <button
          type="button"
          /* Take the toggle on mousedown-prevention so clicking the eye doesn't blur the
             input first — otherwise the blur handler above would fight the toggle. */
          onMouseDown={(e) => e.preventDefault()}
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
