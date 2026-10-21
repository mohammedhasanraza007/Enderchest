// Server state through TanStack Query (ARCHITECTURE 7): cached, revalidated, invalidated after
// every change. Screens use these hooks and never call `api` directly for reading.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./endpoints";
import type { ProfileUpdate } from "./endpoints";

export const keys = {
  health: ["health"] as const,
  profile: ["profile"] as const,
  settings: ["settings"] as const,
  backups: ["backups"] as const,
};

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
