import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import type { Profile } from "../api/endpoints";
import { BrandMark } from "../primitives/BrandMark";
import { LiveBadge } from "../primitives/LiveBadge";
import { useCameraLive } from "./CameraLive";
import { NameMenu } from "./NameMenu";

// The floating navigation capsule (DESIGN.md 6.2): the logo and wordmark on the left, the pages
// that work in the centre (after Phase 2: Inventory and Camera, PAGES.md 1, D-034), the name pill
// on the right. The LIVE badge sits on Camera only while a stream runs. The bell arrives with
// notifications (Phase 4).

const PAGES = [
  { to: "/inventory", label: "Inventory" },
  { to: "/camera", label: "Camera" },
];

function navClass({ isActive }: { isActive: boolean }): string {
  return ["nav__item", isActive ? "is-active" : ""].filter(Boolean).join(" ");
}

export function NavCapsule({ profile }: { profile: Profile & { name: string } }) {
  // Past a few pixels of scroll the capsule shrinks a little (transform only, DESIGN.md 4.8).
  const [compact, setCompact] = useState(false);
  const { live } = useCameraLive();
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
          {PAGES.map((page) => (
            <li key={page.to}>
              <NavLink to={page.to} className={navClass}>
                {page.label}
                {page.to === "/camera" && live ? <LiveBadge /> : null}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="nav__end">
          <NameMenu profile={profile} />
        </div>
      </nav>
    </header>
  );
}
