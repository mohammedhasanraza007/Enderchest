// Theme handling (DESIGN.md 5.3, ARCHITECTURE 7). The choice is stored on the server (the
// profile); the page gets it before first paint from data-theme-pref, written by the server.
// <html data-theme> is always "light" or "dark"; data-theme-pref is "system", "light" or "dark".

import type { ThemePref } from "../api/endpoints";

export type ResolvedTheme = "light" | "dark";

export function resolveTheme(pref: ThemePref, systemPrefersDark: boolean): ResolvedTheme {
  if (pref === "system") return systemPrefersDark ? "dark" : "light";
  return pref;
}

const DARK_QUERY = "(prefers-color-scheme: dark)";
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function systemPrefersDark(): boolean {
  return window.matchMedia(DARK_QUERY).matches;
}

/** Apply a preference to the page. The colours crossfade briefly unless motion is reduced. */
export function applyTheme(pref: ThemePref, animate = true): void {
  const root = document.documentElement;
  const resolved = resolveTheme(pref, systemPrefersDark());
  if (
    root.getAttribute("data-theme") === resolved &&
    root.getAttribute("data-theme-pref") === pref
  ) {
    return;
  }
  const reduced = window.matchMedia(REDUCED_MOTION_QUERY).matches;
  if (animate && !reduced) {
    root.classList.add("theme-fade");
    window.setTimeout(() => root.classList.remove("theme-fade"), 220);
  }
  root.setAttribute("data-theme-pref", pref);
  root.setAttribute("data-theme", resolved);
}

/** While the preference is "system", follow the operating system when it changes. */
export function watchSystemTheme(onChange: () => void): () => void {
  const query = window.matchMedia(DARK_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}
