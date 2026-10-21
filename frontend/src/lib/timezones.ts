// Time zone choices for the welcome screen and Settings. The browser knows the owner's zone; the
// list is the browser's own, so every entry can be saved (the server checks it against tzdata).

import type { SelectOption } from "../primitives/Input";

// Browsers still report some zones under an old name (Chrome says Asia/Calcutta for India). The
// current names exist in tzdata too, and are the ones a person expects to see.
const CURRENT_NAME: Record<string, string> = {
  "Asia/Calcutta": "Asia/Kolkata",
  "Asia/Katmandu": "Asia/Kathmandu",
  "Asia/Saigon": "Asia/Ho_Chi_Minh",
  "Asia/Rangoon": "Asia/Yangon",
  "Asia/Thimbu": "Asia/Thimphu",
  "Europe/Kiev": "Europe/Kyiv",
  "Atlantic/Faeroe": "Atlantic/Faroe",
  "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
};

export function currentZoneName(zone: string): string {
  return CURRENT_NAME[zone] ?? zone;
}

export function browserTimeZone(): string {
  return currentZoneName(Intl.DateTimeFormat().resolvedOptions().timeZone);
}

export function timeZoneOptions(current: string): SelectOption[] {
  const known =
    typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [];
  const all = new Set<string>(
    ["UTC", current, browserTimeZone(), ...known].map((zone) => currentZoneName(zone)),
  );
  return [...all]
    .sort((a, b) => a.localeCompare(b))
    .map((zone) => ({ value: zone, label: zone.replace(/_/g, " ") }));
}
