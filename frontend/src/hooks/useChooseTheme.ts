import type { Profile, ThemePref } from "../api/endpoints";
import { useSaveProfile } from "../api/queries";
import { applyTheme } from "../lib/theme";
import { useToast } from "../primitives/Toast";

/**
 * Choose a theme: it is applied at once, then saved on the server (the profile). If saving
 * fails, the old theme comes back and a toast says so. Only used once a name is saved.
 */
export function useChooseTheme(profile: Profile & { name: string }) {
  const save = useSaveProfile();
  const toast = useToast();
  return (theme: ThemePref) => {
    if (theme === profile.theme) return;
    const previous = profile.theme;
    applyTheme(theme);
    save.mutate(
      { name: profile.name, timezone: profile.timezone, theme },
      {
        onError: (error) => {
          applyTheme(previous);
          toast({ message: `The theme was not saved. ${error.message}` });
        },
      },
    );
  };
}
