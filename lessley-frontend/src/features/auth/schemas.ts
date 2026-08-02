import { z } from "zod"

export const loginSchema = z.object({
  userName: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
})

export const registerSchema = z.object({
  userName: z
    .string()
    .min(3, "Must be at least 3 characters")
    .max(50, "Must be at most 50 characters")
    .regex(/^[a-zA-Z0-9\-._@+]+$/, "Only letters, digits, and - . _ @ + are allowed"),
  email: z.string().email("Please enter a valid email address"),
  password: z
    .string()
    .min(6, "Must be at least 6 characters")
    .regex(/[A-Z]/, "Must include an uppercase letter")
    .regex(/[a-z]/, "Must include a lowercase letter")
    .regex(/[0-9]/, "Must include a digit")
    .regex(/[^a-zA-Z0-9]/, "Must include a special character"),
  clubs: z.array(z.string()).optional(),
  matchLevel: z.enum(["Low", "Medium", "High"]).optional(),
  mutedCategories: z.array(z.string()).optional(),
})

export type LoginValues = z.infer<typeof loginSchema>
export type RegisterValues = z.infer<typeof registerSchema>
