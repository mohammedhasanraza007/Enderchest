// The LIVE badge (DESIGN.md 6.4) on the Camera nav item. It may only be shown while a camera
// stream is actually running (useCamera sets that state).

export function LiveBadge() {
  return (
    <span className="live-badge">
      <span className="live-badge__dot" aria-hidden="true" />
      LIVE
    </span>
  );
}
