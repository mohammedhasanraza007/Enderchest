import { usePageTitle } from "../hooks/usePageTitle";
import { useProfile } from "../api/queries";
import { AboutSection } from "./settings/AboutSection";
import { AppearanceSection } from "./settings/AppearanceSection";
import { BackupSection } from "./settings/BackupSection";
import { ProfileSection } from "./settings/ProfileSection";

// P-02, Settings (PAGES.md): one column of frosted cards, each a section. A section appears
// only when its feature exists, so later phases add sections here (categories, Gemini, ...).

export function Settings() {
  usePageTitle("Settings");
  const profile = useProfile().data;
  if (profile === undefined || profile.name === null) return null; // the first-run gate has loaded it
  const named = { ...profile, name: profile.name };

  return (
    <div className="settings">
      <h1 className="settings__title">Settings</h1>
      <div className="settings__column">
        <ProfileSection profile={profile} />
        <AppearanceSection profile={named} />
        <BackupSection timeZone={profile.timezone} />
        <AboutSection />
      </div>
    </div>
  );
}
