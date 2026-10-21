// The LIVE badge (DESIGN.md 6.4). It exists now so the nav is complete, and stays unused until
// the camera page (Phase 2): it may only be shown while a camera stream is actually running.

export function LiveBadge() {
  return (
    <span className="live-badge">
      <span className="live-badge__dot" aria-hidden="true" />
      LIVE
    </span>
  );
}
