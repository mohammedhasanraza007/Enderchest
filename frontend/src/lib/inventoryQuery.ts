// The Inventory filters live in the URL query (PAGES.md P-03), so Back restores them. This turns
// the query into the API filters and back, dropping defaults so the URL stays short.

import type { ItemFilters } from "../api/endpoints";

export const STATES = ["active", "used", "expired", "discarded", "all"] as const;
export const EXPIRIES = ["any", "soon", "today", "past", "none", "unknown"] as const;
export const SORTS = ["created_desc", "name_asc", "expiry_asc"] as const;

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

function id(value: string | null): number | undefined {
  return value && /^\d+$/.test(value) ? Number(value) : undefined;
}

export function filtersFromQuery(query: URLSearchParams): ItemFilters {
  const photo = query.get("photo");
  return {
    q: query.get("q") ?? "",
    category_id: id(query.get("category")),
    location_id: id(query.get("location")),
    state: pick(query.get("state"), STATES, "active"),
    expiry: pick(query.get("expiry"), EXPIRIES, "any"),
    has_photo: photo === "yes" ? true : photo === "no" ? false : undefined,
    sort: pick(query.get("sort"), SORTS, "created_desc"),
  };
}

export function queryFromFilters(filters: ItemFilters): URLSearchParams {
  const query = new URLSearchParams();
  if (filters.q) query.set("q", filters.q);
  if (filters.category_id !== undefined) query.set("category", String(filters.category_id));
  if (filters.location_id !== undefined) query.set("location", String(filters.location_id));
  if (filters.state && filters.state !== "active") query.set("state", filters.state);
  if (filters.expiry && filters.expiry !== "any") query.set("expiry", filters.expiry);
  if (filters.has_photo !== undefined) query.set("photo", filters.has_photo ? "yes" : "no");
  if (filters.sort && filters.sort !== "created_desc") query.set("sort", filters.sort);
  return query;
}

/** True when anything narrows the list, so an empty result means "no matches", not "no items". */
export function isFiltered(filters: ItemFilters): boolean {
  return queryFromFilters({ ...filters, sort: undefined }).toString() !== "";
}
