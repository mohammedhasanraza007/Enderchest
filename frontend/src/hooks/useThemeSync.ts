import { useEffect } from "react";
import type { ThemePref } from "../api/endpoints";
import { applyTheme, watchSystemTheme } from "../lib/theme";

/** Keeps <html> in step with the stored preference, and with the system when it is "system". */
export function useThemeSync(pref: ThemePref | undefined): void {
  useEffect(() => {
    if (pref === undefined) return;
    applyTheme(pref, false);
    if (pref !== "system") return;
    return watchSystemTheme(() => applyTheme("system", true));
  }, [pref]);
}
