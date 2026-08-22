import { z } from "zod"

export const loginSchema = z.object({
  // The Gateway resolves this as a username first and then as an email address, so the field
  // accepts either — a user who just reset their password by email will try that email here.
  userName: z.string().min(1, "Username or email is required"),
  password: z.string().min(1, "Password is required"),
})

// Length comes from the Gateway's RegisterDto ([StringLength(128, MinimumLength = 8)]);
// the character classes come from ASP.NET Identity's default PasswordOptions, which the
// Gateway never overrides — so UserManager.CreateAsync rejects a password missing any of
// them. Checking them here turns a generic server-side "registration failed" into a
// specific message on the field. The Unicode classes mirror Identity's own char.IsUpper /
// IsLower / IsDigit / !IsLetterOrDigit tests, so a Hebrew-only password fails in the same
// way on both sides.
export const passwordSchema = z
  .string()
  .min(8, "Must be at least 8 characters")
  .regex(/\p{Lu}/u, "Must include an uppercase letter")
  .regex(/\p{Ll}/u, "Must include a lowercase letter")
  .regex(/\p{Nd}/u, "Must include a number")
  .regex(/[^\p{L}\p{N}]/u, "Must include a special character (for example !, ? or #)")

export const registerSchema = z
  .object({
    userName: z
      .string()
      .min(3, "Must be at least 3 characters")
      .max(50, "Must be at most 50 characters")
      .regex(/^[a-zA-Z0-9\-._@+]+$/, "Only letters, digits, and - . _ @ + are allowed"),
    email: z.string().email("Please enter a valid email address"),
    password: passwordSchema,
    verifyPassword: z.string().min(1, "Please confirm your password"),
    clubs: z.array(z.string()).optional(),
    matchLevel: z.enum(["Low", "Medium", "High"]).optional(),
    mutedCategories: z.array(z.string()).optional(),
  })
  .refine((values) => values.password === values.verifyPassword, {
    message: "Passwords don't match",
    path: ["verifyPassword"],
  })

export type LoginValues = z.infer<typeof loginSchema>
export type RegisterValues = z.infer<typeof registerSchema>
