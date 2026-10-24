import { Outlet } from "react-router-dom";
import { useProfile } from "../api/queries";
import { BackupBanner } from "./BackupBanner";
import { NotificationsLive } from "./Bell";
import { NavCapsule } from "./NavCapsule";

// The frame around every page after first run: skip link, nav capsule, backup banner, content,
// and the reminder poll that keeps the bell, the tab title and browser notifications current.

export function AppShell() {
  const profile = useProfile();
  const data = profile.data;
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {data && data.name !== null ? <NavCapsule profile={{ ...data, name: data.name }} /> : null}
      {data && data.name !== null ? <NotificationsLive /> : null}
      <BackupBanner />
      <main id="main" className="page" tabIndex={-1}>
        <Outlet />
      </main>
    </>
  );
}
