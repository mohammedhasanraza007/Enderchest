import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import type { Profile } from "../api/endpoints";
import { BrandMark } from "../primitives/BrandMark";
import { LiveBadge } from "../primitives/LiveBadge";
import { useCameraLive } from "./CameraLive";
import { NameMenu } from "./NameMenu";

// The floating navigation capsule (DESIGN.md 6.2): the logo and wordmark on the left, the pages
// that work in the centre (after Phase 2: Inventory and Camera, PAGES.md 1, D-034), the name pill
// on the right. The LIVE badge sits on Camera only while a stream runs. The bell arrives with
// notifications (Phase 4).

// Each tab also stands for the pages reached from it, so exactly one tab is lit (DESIGN.md 6.3).
const PAGES = [
  { to: "/inventory", label: "Inventory", section: ["/items/", "/labels", "/trash"] },
  { to: "/camera", label: "Camera", section: ["/add"] },
];

/** "page" on the tab's own page, "true" on a page inside its section, else nothing. */
function current(pathname: string, page: (typeof PAGES)[number]): "page" | "true" | undefined {
  if (pathname === page.to) return "page";
  return page.section.some((start) => pathname.startsWith(start)) ? "true" : undefined;
}

export function NavCapsule({ profile }: { profile: Profile & { name: string } }) {
  // Past a few pixels of scroll the capsule shrinks a little (transform only, DESIGN.md 4.8).
  const [compact, setCompact] = useState(false);
  const { live } = useCameraLive();
  const { pathname } = useLocation();
  useEffect(() => {
    const onScroll = () => setCompact(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={["nav", compact ? "nav--compact" : ""].filter(Boolean).join(" ")}>
      <nav className="nav__capsule" aria-label="Main">
        <Link to="/" className="nav__brand" aria-label="Enderchest home">
          <BrandMark size={32} decorative />
          <span className="nav__wordmark">Enderchest</span>
        </Link>
        <ul className="nav__items">
          {PAGES.map((page) => {
            const here = current(pathname, page);
            return (
              <li key={page.to}>
                <Link
                  to={page.to}
                  className={["nav__item", here ? "is-active" : ""].filter(Boolean).join(" ")}
                  aria-current={here}
                >
                  {page.label}
                  {page.to === "/camera" && live ? <LiveBadge /> : null}
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="nav__end">
          <NameMenu profile={profile} />
        </div>
      </nav>
    </header>
  );
}
