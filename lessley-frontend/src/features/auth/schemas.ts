import { z } from "zod"

export const loginSchema = z.object({
  userName: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
})

// Matches the Gateway's actual RegisterDto constraint (MinimumLength = 8) — no extra
// complexity rule is enforced server-side, so the client shouldn't invent one either.
export const passwordSchema = z.string().min(8, "Must be at least 8 characters")

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
