import { Outlet } from "react-router-dom";
import { useProfile } from "../api/queries";
import { BackupBanner } from "./BackupBanner";
import { NavCapsule } from "./NavCapsule";

// The frame around every page after first run: skip link, nav capsule, backup banner, content.

export function AppShell() {
  const profile = useProfile();
  const data = profile.data;
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {data && data.name !== null ? <NavCapsule profile={{ ...data, name: data.name }} /> : null}
      <BackupBanner />
      <main id="main" className="page" tabIndex={-1}>
        <Outlet />
      </main>
    </>
  );
}
