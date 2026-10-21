// One function per endpoint of docs/API.md that the app calls. Types come from the generated
// schema (scripts/export_openapi.py, then `test.bat types`), so a backend change that breaks a
// call here breaks the type check.

import type { components } from "./schema";
import { request } from "./client";

export type Profile = components["schemas"]["Profile"];
export type ProfileUpdate = components["schemas"]["ProfileUpdate"];
export type SettingsView = components["schemas"]["SettingsView"];
export type SettingsPatch = components["schemas"]["SettingsPatch"];
export type BackupsView = components["schemas"]["BackupsView"];
export type BackupItem = components["schemas"]["BackupItem"];
export type BackupMade = components["schemas"]["BackupMade"];
export type Health = components["schemas"]["Health"];
export type ThemePref = Profile["theme"];

export const api = {
  health: () => request<Health>("GET", "/health"),
  profile: () => request<Profile>("GET", "/api/v1/profile"),
  saveProfile: (body: ProfileUpdate) => request<Profile>("PUT", "/api/v1/profile", body),
  settings: () => request<SettingsView>("GET", "/api/v1/settings"),
  patchSettings: (body: SettingsPatch) => request<SettingsView>("PATCH", "/api/v1/settings", body),
  backups: () => request<BackupsView>("GET", "/api/v1/backups"),
  makeBackup: () => request<BackupMade>("POST", "/api/v1/backups"),
};
