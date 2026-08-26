/**
 * Bidi direction on credential fields.
 *
 * The app runs `dir="rtl"` in Hebrew. Anything that inherits that direction has its neutral
 * characters (`@`, `.`, `!`, `-`) reordered by the bidi algorithm: a trailing one takes the
 * paragraph direction and lands at the *visual start*, so a password typed as "MyPass123!"
 * shows up as "!MyPass123". The value posted to the server is right — only the rendering is
 * scrambled, which is worse than a plain bug, because it reads as a typo the user did not
 * make and they retype a correct password over and over.
 *
 * Browsers do this for us on `input[type=password]`, which is always laid out LTR. The
 * moment `PasswordInput` stopped being one — it masks a text input instead, so iOS stops
 * echoing the last character — that protection disappeared silently. These tests are here so
 * it cannot disappear again without something going red.
 */

import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"

import { Input } from "./input"
import { PasswordInput } from "./password-input"

/** The app in Hebrew: everything nested under an RTL root. */
function renderInRtl(ui: React.ReactElement) {
  return render(ui, {
    container: document.body.appendChild(
      Object.assign(document.createElement("div"), { dir: "rtl" })
    ),
  })
}

describe("credential fields inside an RTL page", () => {
  it("lays the password control out LTR", () => {
    renderInRtl(<PasswordInput aria-label="password" />)

    // The whole control, not just the input: the reveal button is positioned with a logical
    // property (`end-0`), so if only the input flipped, text and button would resolve
    // against opposite directions and the text would run underneath the button.
    expect(screen.getByLabelText("password").closest("[dir]")).toHaveAttribute("dir", "ltr")
  })

  it("lays an email field out LTR", () => {
    renderInRtl(<Input type="email" aria-label="email" />)

    expect(screen.getByLabelText("email")).toHaveAttribute("dir", "ltr")
  })

  it.each(["tel", "url"])("lays a %s field out LTR", (type) => {
    renderInRtl(<Input type={type} aria-label="field" />)

    expect(screen.getByLabelText("field")).toHaveAttribute("dir", "ltr")
  })

  it("leaves a plain text field alone, so Hebrew prose still reads correctly", () => {
    // The opposite failure: forcing LTR on every input would left-align genuine Hebrew
    // input and reorder *its* neutrals instead. Only Latin-by-syntax types are pinned.
    renderInRtl(<Input type="text" aria-label="free text" />)

    expect(screen.getByLabelText("free text")).not.toHaveAttribute("dir")
  })

  it("lets a caller pin direction explicitly", () => {
    // How the username fields opt in — a plain text input that happens to be Latin.
    renderInRtl(<Input aria-label="username" dir="ltr" />)

    expect(screen.getByLabelText("username")).toHaveAttribute("dir", "ltr")
  })

  it("does not let the type default override an explicit direction", () => {
    renderInRtl(<Input type="email" aria-label="email" dir="rtl" />)

    expect(screen.getByLabelText("email")).toHaveAttribute("dir", "rtl")
  })
})

/**
 * The other half of "Latin by syntax": a mobile keyboard capitalises the first letter of
 * any ordinary field, so a username typed `dor` is submitted as `Dor` and the sign-in is
 * rejected as the wrong credentials — with nothing on screen explaining why.
 */
describe("autocapitalisation on credential fields", () => {
  it("turns capitalisation, autocorrect and spellcheck off on a username field", () => {
    // Exactly how AccountStep and LoginForm render it.
    render(<Input aria-label="username" dir="ltr" autoComplete="username" />)
    const field = screen.getByLabelText("username")

    expect(field).toHaveAttribute("autocapitalize", "none")
    expect(field).toHaveAttribute("autocorrect", "off")
    expect(field).toHaveAttribute("spellcheck", "false")
  })

  it("turns capitalisation off on an email field", () => {
    render(<Input type="email" aria-label="email" />)

    expect(screen.getByLabelText("email")).toHaveAttribute("autocapitalize", "none")
  })

  it("leaves a prose field capitalising as the user expects", () => {
    // The opposite failure: a store-name or free-text box should still behave like prose.
    render(<Input type="text" aria-label="free text" />)
    const field = screen.getByLabelText("free text")

    expect(field).not.toHaveAttribute("autocapitalize")
    expect(field).not.toHaveAttribute("spellcheck", "false")
  })

  it("lets a caller override the default", () => {
    render(<Input aria-label="name" dir="ltr" autoCapitalize="words" />)

    expect(screen.getByLabelText("name")).toHaveAttribute("autocapitalize", "words")
  })

  it("keeps the password control non-capitalising", () => {
    render(<PasswordInput aria-label="password" />)

    expect(screen.getByLabelText("password")).toHaveAttribute("autocapitalize", "none")
  })
})
