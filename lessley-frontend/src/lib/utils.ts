import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function toggleArrayValue(current: string[], value: string): string[] {
  return current.includes(value) ? current.filter((v) => v !== value) : [...current, value]
}

export function getClubName(clubs: { id: string; name: string }[], clubId: string): string {
  return clubs.find((c) => c.id === clubId)?.name ?? clubId
}
