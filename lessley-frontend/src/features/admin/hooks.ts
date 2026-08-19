import { useMutation, useQuery } from "@tanstack/react-query"
import { queryKeys } from "@/lib/query-keys"
import {
  changeUserRole,
  fetchMccCategories,
  sendNotificationToAll,
  sendNotificationToGroup,
  sendNotificationToUser,
  updateUserTags,
} from "./api"

export function useMccCategories() {
  return useQuery({
    queryKey: queryKeys.mcc.categories(),
    queryFn: fetchMccCategories,
  })
}

export function useChangeUserRole() {
  return useMutation({
    mutationFn: ({ email, role }: { email: string; role: Parameters<typeof changeUserRole>[1] }) =>
      changeUserRole(email, role),
  })
}

export function useUpdateUserTags() {
  return useMutation({
    mutationFn: ({ email, tags }: { email: string; tags: string[] }) =>
      updateUserTags(email, tags),
  })
}

export function useSendNotificationToUser() {
  return useMutation({
    mutationFn: ({
      email,
      message,
      dealId,
    }: {
      email: string
      message: string
      dealId?: string
    }) => sendNotificationToUser(email, { message, dealId: dealId || undefined }),
  })
}

export function useSendNotificationToGroup() {
  return useMutation({
    mutationFn: ({
      tag,
      message,
      dealId,
    }: {
      tag: string
      message: string
      dealId?: string
    }) => sendNotificationToGroup(tag, { message, dealId: dealId || undefined }),
  })
}

export function useSendNotificationToAll() {
  return useMutation({
    mutationFn: ({ message, dealId }: { message: string; dealId?: string }) =>
      sendNotificationToAll({ message, dealId: dealId || undefined }),
  })
}
