import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Profile } from "../api/endpoints";
import { BrandMark } from "../primitives/BrandMark";
import { NameMenu } from "./NameMenu";

// The floating navigation capsule (DESIGN.md 6.2): the logo and wordmark on the left, the name
// pill on the right. The centre stays empty until pages exist to link to (PAGES.md 1, D-034):
// nothing is shown that does not work. The bell arrives with notifications (Phase 4).

export function NavCapsule({ profile }: { profile: Profile & { name: string } }) {
  // Past a few pixels of scroll the capsule shrinks a little (transform only, DESIGN.md 4.8).
  const [compact, setCompact] = useState(false);
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
        <div className="nav__end">
          <NameMenu profile={profile} />
        </div>
      </nav>
    </header>
  );
}
