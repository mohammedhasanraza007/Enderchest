import type { Profile, ThemePref } from "../../api/endpoints";
import { useChooseTheme } from "../../hooks/useChooseTheme";
import { Chip } from "../../primitives/Chip";
import { GlassCard } from "../../primitives/Glass";

// Settings, Appearance: System, Light or Dark. The choice is applied at once and saved on the
// server, so it follows the owner across reloads without a flash.

const THEMES: Array<{ value: ThemePref; label: string }> = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

export function AppearanceSection({ profile }: { profile: Profile & { name: string } }) {
  const chooseTheme = useChooseTheme(profile);
  return (
    <GlassCard title="Appearance">
      <p className="stack-gap section-note">
        System follows your computer's light or dark setting.
      </p>
      <div className="chip-row" role="radiogroup" aria-label="Theme">
        {THEMES.map((theme) => (
          <Chip
            key={theme.value}
            role="radio"
            selected={profile.theme === theme.value}
            onSelect={() => chooseTheme(theme.value)}
          >
            {theme.label}
          </Chip>
        ))}
      </div>
    </GlassCard>
  );
}
