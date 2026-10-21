import { useEffect, useId, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import type { Profile, ThemePref } from "../api/endpoints";
import { useBackups } from "../api/queries";
import { useChooseTheme } from "../hooks/useChooseTheme";
import { statusLine } from "../lib/backupText";
import { Chip } from "../primitives/Chip";

// The name pill and its menu (PAGES.md 1): Settings, the theme in three small pills, and the
// backup status line. It is a disclosure (a button that shows a panel), so Tab walks through it
// in order; Escape closes it and puts focus back on the pill.

const THEMES: Array<{ value: ThemePref; label: string }> = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

export function NameMenu({ profile }: { profile: Profile & { name: string } }) {
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const pill = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const location = useLocation();
  const backups = useBackups();
  const chooseTheme = useChooseTheme(profile);

  // Going to another page closes the menu.
  useEffect(() => setOpen(false), [location.pathname]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        pill.current?.focus();
      }
    }
    function onPointer(event: PointerEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  return (
    <div className="name-menu" ref={container}>
      <button
        ref={pill}
        type="button"
        className="name-pill"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        title={profile.name}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="name-pill__text">{profile.name}</span>
      </button>
      {open ? (
        <div id={panelId} className="name-menu__panel">
          <Link to="/settings" className="name-menu__link" onClick={() => setOpen(false)}>
            Settings
          </Link>
          <div className="name-menu__group" role="radiogroup" aria-label="Theme">
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
          <p className="name-menu__status">{statusLine(backups.data, profile.timezone)}</p>
        </div>
      ) : null}
    </div>
  );
}
