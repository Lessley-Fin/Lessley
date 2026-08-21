import { apiFetch } from "@/lib/api-client"

export type UserRole = "None" | "Viewer" | "Operator" | "Admin"

export interface MccCategory {
  category: string
}

export async function fetchMccCategories(): Promise<MccCategory[]> {
  return apiFetch<MccCategory[]>("/api/v1/mcc/categories")
}

export interface SendNotificationPayload {
  message: string
  dealId?: string
}

export async function changeUserRole(email: string, role: UserRole): Promise<string> {
  return apiFetch<string>(`/api/v1/admin/role/${encodeURIComponent(email)}/${role}`, {
    method: "PUT",
  })
}

export async function updateUserTags(email: string, tags: string[]): Promise<unknown> {
  return apiFetch(`/api/v1/admin/users/${encodeURIComponent(email)}/tags`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tags),
  })
}

export async function sendNotificationToUser(
  email: string,
  payload: SendNotificationPayload,
): Promise<unknown> {
  return apiFetch(`/api/v1/admin/notifications/user/${encodeURIComponent(email)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export async function sendNotificationToGroup(
  tag: string,
  payload: SendNotificationPayload,
): Promise<unknown> {
  return apiFetch(`/api/v1/admin/notifications/group/${encodeURIComponent(tag)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export async function sendNotificationToAll(payload: { message: string }): Promise<unknown> {
  return apiFetch("/api/v1/admin/notifications/broadcast", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}
