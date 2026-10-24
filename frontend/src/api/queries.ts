// Server state through TanStack Query (ARCHITECTURE 7): cached, revalidated, invalidated after
// every change. Screens use these hooks and never call `api` directly for reading.

import {
  useInfiniteQuery,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCallback } from "react";
import { api } from "./endpoints";
import type { Draft, ItemFilters, NotificationStatus, ProfileUpdate, TaskScope } from "./endpoints";

export const keys = {
  health: ["health"] as const,
  profile: ["profile"] as const,
  settings: ["settings"] as const,
  backups: ["backups"] as const,
  categories: ["categories"] as const,
  locations: ["locations"] as const,
  items: ["items"] as const,
  item: (publicId: string) => ["item", publicId] as const,
  itemEvents: (publicId: string) => ["item-events", publicId] as const,
  drafts: ["drafts"] as const,
  draft: (id: string) => ["draft", id] as const,
  gemini: ["gemini"] as const,
  tasks: (scope: TaskScope) => ["tasks", scope] as const,
  inspections: (publicId: string) => ["inspections", publicId] as const,
  notifications: (status: NotificationStatus) => ["notifications", status] as const,
  notificationCount: ["notification-count"] as const,
};

// The bell is read every minute and whenever the window gets focus (PAGES.md P-11).
const NOTIFICATION_POLL_MS = 60_000;

// A reading runs in the background (D-100); while one is pending the draft is read again every
// second, and polling stops by itself once nothing is pending.
const READING_POLL_MS = 1000;

function isReading(draft: Draft): boolean {
  return draft.ocr_status === "pending" || draft.gemini_status === "pending";
}

export function useProfile() {
  return useQuery({ queryKey: keys.profile, queryFn: api.profile, staleTime: 60_000 });
}

export function useHealth() {
  return useQuery({ queryKey: keys.health, queryFn: api.health, staleTime: 60_000 });
}

/** The backup status drives the global banner, so it is re-read every minute and on focus. */
export function useBackups() {
  return useQuery({
    queryKey: keys.backups,
    queryFn: api.backups,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

export function useSaveProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileUpdate) => api.saveProfile(body),
    onSuccess: (profile) => client.setQueryData(keys.profile, profile),
  });
}

export function useMakeBackup() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.makeBackup,
    onSettled: () => client.invalidateQueries({ queryKey: keys.backups }),
  });
}

export function useCategories() {
  return useQuery({ queryKey: keys.categories, queryFn: api.categories });
}

export function useLocations() {
  return useQuery({ queryKey: keys.locations, queryFn: api.locations });
}

/** One list of items, page by page (`cursor`), for Inventory and Trash. */
export function useItemList(filters: ItemFilters & { deleted?: "exclude" | "only" }) {
  return useInfiniteQuery({
    queryKey: [...keys.items, filters],
    queryFn: ({ pageParam }) => api.items(filters, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useItem(publicId: string) {
  return useQuery({ queryKey: keys.item(publicId), queryFn: () => api.item(publicId) });
}

/** Several items at once, for the label sheet (PAGES.md P-08). */
export function useItemsById(publicIds: string[]) {
  return useQueries({
    queries: publicIds.map((publicId) => ({
      queryKey: keys.item(publicId),
      queryFn: () => api.item(publicId),
    })),
  });
}

export function useItemEvents(publicId: string) {
  return useInfiniteQuery({
    queryKey: keys.itemEvents(publicId),
    queryFn: ({ pageParam }) => api.itemEvents(publicId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useDrafts() {
  return useQuery({
    queryKey: keys.drafts,
    queryFn: api.drafts,
    refetchInterval: (query) => (query.state.data?.items.some(isReading) ? READING_POLL_MS : false),
  });
}

export function useDraft(id: string) {
  return useQuery({
    queryKey: keys.draft(id),
    queryFn: () => api.draft(id),
    refetchInterval: (query) =>
      query.state.data && isReading(query.state.data) ? READING_POLL_MS : false,
  });
}

export function useSettings() {
  return useQuery({ queryKey: keys.settings, queryFn: api.settings });
}

export function useTasks(scope: TaskScope) {
  return useQuery({ queryKey: keys.tasks(scope), queryFn: () => api.tasks(scope) });
}

export function useInspections(publicId: string) {
  return useQuery({
    queryKey: keys.inspections(publicId),
    queryFn: () => api.inspections(publicId),
  });
}

export function useNotifications(status: NotificationStatus) {
  return useQuery({
    queryKey: keys.notifications(status),
    queryFn: () => api.notifications(status),
    refetchOnWindowFocus: true,
  });
}

/** Open and unread counts, and the rows never shown as a browser notification. */
export function useNotificationCount() {
  return useQuery({
    queryKey: keys.notificationCount,
    queryFn: api.notificationCount,
    refetchInterval: NOTIFICATION_POLL_MS,
    refetchOnWindowFocus: true,
  });
}

/** Gemini key state, model, mode and photo sharing (P-02, P-07). */
export function useGemini() {
  return useQuery({ queryKey: keys.gemini, queryFn: api.gemini });
}

/**
 * After any inventory change: every list, item, history, count, draft, task and reminder is read
 * again, so no screen shows a stale number (DESIGN.md 13, counts match lists). An item change can
 * change what is due, so the reminders are part of it (D-107).
 */
export function useRefreshInventory(): () => Promise<void> {
  const client = useQueryClient();
  return useCallback(async () => {
    await Promise.all(
      [
        keys.items,
        ["item"],
        ["item-events"],
        keys.categories,
        keys.locations,
        keys.drafts,
        ["tasks"],
        ["inspections"],
        ["notifications"],
        keys.notificationCount,
      ].map((queryKey) => client.invalidateQueries({ queryKey })),
    );
  }, [client]);
}
