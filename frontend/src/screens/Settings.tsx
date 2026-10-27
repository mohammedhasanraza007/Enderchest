import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { usePageTitle } from "../hooks/usePageTitle";
import { useProfile } from "../api/queries";
import { AboutSection } from "./settings/AboutSection";
import { AppearanceSection } from "./settings/AppearanceSection";
import { BackupSection } from "./settings/BackupSection";
import { CategoriesSection } from "./settings/CategoriesSection";
import { CoachSection } from "./settings/CoachSection";
import { DataSection } from "./settings/DataSection";
import { GeminiSection } from "./settings/GeminiSection";
import { LocationsSection } from "./settings/LocationsSection";
import { NotificationsSection } from "./settings/NotificationsSection";
import { ProfileSection } from "./settings/ProfileSection";

// P-02, Settings (PAGES.md): one column of frosted cards, each a section. A section appears
// only when its feature exists, so later phases add sections here (categories, Gemini, ...).

export function Settings() {
  usePageTitle("Settings");
  const profile = useProfile().data;
  const { hash } = useLocation();
  // The Assistant page links to its switch (/settings#assistant-switch); the router does not
  // scroll to a hash by itself, and the Gemini section renders after its query loads.
  useEffect(() => {
    if (hash === "") return;
    const timer = window.setInterval(() => {
      const target = document.getElementById(hash.slice(1));
      if (!target) return;
      window.clearInterval(timer);
      target.scrollIntoView({ block: "center" });
    }, 50);
    const stop = window.setTimeout(() => window.clearInterval(timer), 3000);
    return () => {
      window.clearInterval(timer);
      window.clearTimeout(stop);
    };
  }, [hash]);
  if (profile === undefined || profile.name === null) return null; // the first-run gate has loaded it
  const named = { ...profile, name: profile.name };

  return (
    <div className="settings">
      <h1 className="settings__title">Settings</h1>
      <div className="settings__column">
        <ProfileSection profile={profile} />
        <AppearanceSection profile={named} />
        <CategoriesSection />
        <LocationsSection />
        <BackupSection timeZone={profile.timezone} />
        <NotificationsSection />
        <GeminiSection />
        <CoachSection />
        <DataSection />
        <AboutSection />
      </div>
    </div>
  );
}
