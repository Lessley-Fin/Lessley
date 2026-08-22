import { describe, expect, it } from "vitest"

import { passwordSchema } from "./schemas"

// These mirror ASP.NET Identity's default PasswordOptions, which the Gateway relies on
// rather than overriding — if the client rules drift, registration starts failing with a
// generic server error instead of a message on the field.
describe("passwordSchema", () => {
  it("accepts a password with all four character classes", () => {
    expect(passwordSchema.safeParse("Str0ng!pass").success).toBe(true)
  })

  it.each([
    ["too short", "Ab1!xy"],
    ["no uppercase", "str0ng!pass"],
    ["no lowercase", "STR0NG!PASS"],
    ["no digit", "Strong!pass"],
    ["no special character", "Str0ngpass1"],
  ])("rejects a password with %s", (_case, value) => {
    expect(passwordSchema.safeParse(value).success).toBe(false)
  })

  // Hebrew letters are letters to char.IsLetterOrDigit, so Identity does not count them as
  // uppercase, lowercase or non-alphanumeric — the client must not be more permissive.
  it("does not treat Hebrew letters as satisfying the character classes", () => {
    expect(passwordSchema.safeParse("סיסמה123456").success).toBe(false)
  })
})
