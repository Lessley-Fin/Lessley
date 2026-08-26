import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * Input types whose value is Latin by syntax, never prose: an address, a number, a URL.
 *
 * In Hebrew the page is `dir="rtl"`, and a text-ish input inherits that. The bidi algorithm
 * then reorders neutral characters (`@`, `.`, `!`, `-`) against what was typed — a trailing
 * one takes the paragraph direction and lands at the *visual start*, so an address ending in
 * `.com.` or a password ending in `!` renders with that character at the front. The value in
 * the DOM is correct; only what the user sees is scrambled, which is worse, because it reads
 * as a typo they did not make.
 *
 * Browsers already do exactly this for `type="password"`, which they always lay out LTR
 * whatever the surrounding direction is. This extends the same treatment to the rest.
 *
 * Not a blanket default: a plain `type="text"` holds prose as often as not, and forcing LTR
 * there would left-align genuine Hebrew input. Those fields opt in with `dir="ltr"` at the
 * call site — see the username fields in `features/auth`.
 *
 * The same "Latin by syntax, never prose" test also decides autocapitalisation. A mobile
 * keyboard defaults to `autocapitalize="sentences"`, so it silently upper-cases the first
 * character of a username or an address — and the user then submits `Dor` where they typed
 * `dor`, which the server rejects as the wrong credentials. Autocorrect and the spell
 * checker are wrong on the same fields and for the same reason: none of these values are
 * words. Defaults only, applied before the caller's props, so any field can still override.
 */
const LATIN_ONLY_TYPES = new Set(["email", "password", "tel", "url"])

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, dir, ...props }, ref) => {
    // Latin by syntax either because the type says so, or because the call site pinned the
    // direction — which is how a plain-text username field declares it holds no prose.
    const isLatinBySyntax = dir === "ltr" || (!!type && LATIN_ONLY_TYPES.has(type))

    return (
      <input
        type={type}
        // An explicit `dir` from the caller always wins.
        dir={dir ?? (isLatinBySyntax ? "ltr" : undefined)}
        // Spread before `props` so a caller can still opt back in.
        {...(isLatinBySyntax
          ? { autoCapitalize: "none" as const, autoCorrect: "off", spellCheck: false }
          : null)}
        className={cn(
          "flex h-10 w-full rounded-xl border border-input bg-background px-3 py-2 text-base shadow-sm transition-all file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
