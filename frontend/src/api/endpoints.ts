// One function per endpoint of docs/API.md that the app calls. Types come from the generated
// schema (scripts/export_openapi.py, then `test.bat types`), so a backend change that breaks a
// call here breaks the type check.

import type { components, operations } from "./schema";
import { request, upload } from "./client";

export type Profile = components["schemas"]["Profile"];
export type ProfileUpdate = components["schemas"]["ProfileUpdate"];
export type SettingsView = components["schemas"]["SettingsView"];
export type SettingsPatch = components["schemas"]["SettingsPatch"];
export type BackupsView = components["schemas"]["BackupsView"];
export type BackupItem = components["schemas"]["BackupItem"];
export type BackupMade = components["schemas"]["BackupMade"];
export type Health = components["schemas"]["Health"];
export type ThemePref = Profile["theme"];
export type Category = components["schemas"]["Category"];
export type CategoryCreate = components["schemas"]["CategoryCreate"];
export type CategoryPatch = components["schemas"]["CategoryPatch"];
export type Location = components["schemas"]["Location"];
export type LocationCreate = components["schemas"]["LocationCreate"];
export type LocationPatch = components["schemas"]["LocationPatch"];
export type ItemSummary = components["schemas"]["ItemSummary"];
export type ItemDetail = components["schemas"]["ItemDetail"];
export type ItemCreate = components["schemas"]["ItemCreate"];
export type ItemPatch = components["schemas"]["ItemPatch"];
export type ItemPage = components["schemas"]["ItemPage"];
export type ExpiryView = components["schemas"]["ExpiryView"];
export type AttrValue = ItemDetail["attributes"][string];
export type EventView = components["schemas"]["EventView"];
export type EventPage = components["schemas"]["EventPage"];
export type PhotoView = components["schemas"]["PhotoView"];
export type Draft = components["schemas"]["Draft"];
export type DraftFields = components["schemas"]["DraftFields"];
export type DraftBatch = components["schemas"]["DraftBatch"];
export type DraftList = components["schemas"]["DraftList"];
export type Proposal = components["schemas"]["Proposal"];
export type ExtractQueued = components["schemas"]["ExtractQueued"];
export type GeminiStatus = components["schemas"]["GeminiStatus"];
export type GeminiTest = components["schemas"]["TestResult"];
export type DeletedItem = components["schemas"]["DeletedItem"];
export type LabelPrintedDone = components["schemas"]["LabelPrintedDone"];
export type UndoDone = components["schemas"]["UndoDone"];
type ListQuery = NonNullable<operations["list_items_api_v1_items_get"]["parameters"]["query"]>;
/** The Inventory filters (PAGES.md P-03); `limit` and `cursor` are added by the list hook. */
export type ItemFilters = Partial<Omit<ListQuery, "limit" | "cursor">>;

/** A query string from defined values only, so a filter left at "any" is not sent. */
function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

const item = (publicId: string) => `/api/v1/items/${encodeURIComponent(publicId)}`;

/** URLs the browser loads directly: images and the QR download. */
export const fileUrl = {
  photo: (id: string) => `/api/v1/photos/${encodeURIComponent(id)}/file`,
  thumb: (id: string) => `/api/v1/photos/${encodeURIComponent(id)}/thumb`,
  qr: (publicId: string) => `${item(publicId)}/qr.svg`,
};

export const api = {
  health: () => request<Health>("GET", "/health"),
  profile: () => request<Profile>("GET", "/api/v1/profile"),
  saveProfile: (body: ProfileUpdate) => request<Profile>("PUT", "/api/v1/profile", body),
  settings: () => request<SettingsView>("GET", "/api/v1/settings"),
  patchSettings: (body: SettingsPatch) => request<SettingsView>("PATCH", "/api/v1/settings", body),
  backups: () => request<BackupsView>("GET", "/api/v1/backups"),
  makeBackup: () => request<BackupMade>("POST", "/api/v1/backups"),

  categories: () => request<Category[]>("GET", "/api/v1/categories"),
  /** A category made by name only starts with no expiry, no maintenance, and a label. */
  createCategory: (body: Pick<CategoryCreate, "name"> & Partial<CategoryCreate>) =>
    request<Category>("POST", "/api/v1/categories", {
      expires_default: false,
      maintenance_default: false,
      label_default: true,
      ...body,
    }),
  changeCategory: (id: number, body: CategoryPatch) =>
    request<Category>("PATCH", `/api/v1/categories/${id}`, body),
  deleteCategory: (id: number, reassignTo?: number | "none") =>
    request<null>("DELETE", `/api/v1/categories/${id}${query({ reassign_to: reassignTo })}`),
  locations: () => request<Location[]>("GET", "/api/v1/locations"),
  createLocation: (body: LocationCreate) => request<Location>("POST", "/api/v1/locations", body),
  changeLocation: (id: number, body: LocationPatch) =>
    request<Location>("PATCH", `/api/v1/locations/${id}`, body),
  deleteLocation: (id: number, reassignTo?: number | "none") =>
    request<null>("DELETE", `/api/v1/locations/${id}${query({ reassign_to: reassignTo })}`),

  items: (filters: ItemFilters & { deleted?: "exclude" | "only" }, cursor?: string) =>
    request<ItemPage>("GET", `/api/v1/items${query({ ...filters, limit: 100, cursor })}`),
  item: (publicId: string) => request<ItemDetail>("GET", item(publicId)),
  createItem: (body: ItemCreate, headers: Record<string, string>) =>
    request<ItemDetail>("POST", "/api/v1/items", body, headers),
  changeItem: (publicId: string, body: ItemPatch) =>
    request<ItemDetail>("PATCH", item(publicId), body),
  deleteItem: (publicId: string) => request<DeletedItem>("DELETE", item(publicId)),
  restoreItem: (publicId: string) => request<ItemDetail>("POST", `${item(publicId)}/restore`),
  purgeItem: (publicId: string) =>
    request<null>("DELETE", `${item(publicId)}/permanent`, { confirm: "DELETE" }),
  itemEvents: (publicId: string, cursor?: string) =>
    request<EventPage>("GET", `${item(publicId)}/events${query({ cursor })}`),
  undo: (eventId: number) => request<UndoDone>("POST", `/api/v1/events/${eventId}/undo`),

  addPhoto: (publicId: string, file: Blob) =>
    upload<PhotoView>(`${item(publicId)}/photos`, form("image", [file])),
  hidePhoto: (photoId: string) =>
    request<null>("DELETE", `/api/v1/photos/${encodeURIComponent(photoId)}`),
  setPrimaryPhoto: (publicId: string, photoId: string) =>
    request<ItemDetail>("PUT", `${item(publicId)}/primary-photo`, { photo_id: photoId }),

  labelPrinted: (publicIds: string[]) =>
    request<LabelPrintedDone>("POST", "/api/v1/items/label-printed", { public_ids: publicIds }),
  lookup: (code: string) =>
    request<ItemSummary>("GET", `/api/v1/lookup/${encodeURIComponent(code)}`),

  createDrafts: (files: Blob[]) => upload<DraftBatch>("/api/v1/drafts", form("images[]", files)),
  drafts: () => request<DraftList>("GET", "/api/v1/drafts"),
  draft: (id: string) => request<Draft>("GET", `/api/v1/drafts/${encodeURIComponent(id)}`),
  changeDraft: (id: string, fields: DraftFields) =>
    request<Draft>("PATCH", `/api/v1/drafts/${encodeURIComponent(id)}`, { fields }),
  addDraftPhoto: (id: string, file: Blob) =>
    upload<Draft>(`/api/v1/drafts/${encodeURIComponent(id)}/photos`, form("image", [file])),
  commitDraft: (id: string, headers: Record<string, string>) =>
    request<ItemDetail>(
      "POST",
      `/api/v1/drafts/${encodeURIComponent(id)}/commit`,
      undefined,
      headers,
    ),
  discardDraft: (id: string) => request<null>("DELETE", `/api/v1/drafts/${encodeURIComponent(id)}`),
  /** Re-read (`local`) or Improve with Gemini (`gemini`); poll the draft for the result. */
  extract: (id: string, engine: "local" | "gemini") =>
    request<ExtractQueued>("POST", `/api/v1/drafts/${encodeURIComponent(id)}/extract`, { engine }),

  gemini: () => request<GeminiStatus>("GET", "/api/v1/gemini"),
  setGeminiKey: (key: string) =>
    request<{ key_set: boolean }>("PUT", "/api/v1/gemini/key", { key }),
  removeGeminiKey: () => request<null>("DELETE", "/api/v1/gemini/key"),
  testGemini: () => request<GeminiTest>("POST", "/api/v1/gemini/test"),
};

function form(field: string, files: Blob[]): FormData {
  const data = new FormData();
  files.forEach((file, index) => {
    const name = file instanceof File ? file.name : `photo-${index + 1}.jpg`;
    data.append(field, file, name);
  });
  return data;
}
