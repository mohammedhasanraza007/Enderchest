import { useEffect, useRef } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useProfile } from "../api/queries";
import { pageArrival } from "../lib/motion";
import { BackupBanner } from "./BackupBanner";
import { DeliveryLayer } from "./Delivery";
import { NotificationsLive } from "./Bell";
import { NavCapsule } from "./NavCapsule";

// The frame around every page after first run: skip link, nav capsule, backup banner, content,
// and the reminder poll that keeps the bell, the tab title and browser notifications current.
// A route change fades the content in with a 6 px lift (DESIGN.md 10, D-128): the Web Animations
// API on the main region, so nothing remounts and input is never blocked.

export function AppShell() {
  const profile = useProfile();
  const data = profile.data;
  const main = usePageArrival();
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {data && data.name !== null ? <NavCapsule profile={{ ...data, name: data.name }} /> : null}
      {data && data.name !== null ? <NotificationsLive /> : null}
      <BackupBanner />
      <main id="main" ref={main} className="page" tabIndex={-1}>
        <Outlet />
      </main>
      <DeliveryLayer />
    </>
  );
}

/** Plays the arrival on the main region when the path changes (not on the first page). */
function usePageArrival() {
  const ref = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const animation = ref.current ? pageArrival(ref.current) : null;
    return () => animation?.cancel();
  }, [pathname]);
  return ref;
}
