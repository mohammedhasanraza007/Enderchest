import { useState } from "react";

// The camera shutter (DESIGN.md 9, D-124): a cream button inside a ring in `--ring-arc` that
// fills while the capture completes (taking the frame, then the upload or check the page runs,
// shown by `busy`). The ring moves by stroke-dashoffset only and is decorative; the button says
// it is busy. Under reduced motion the ring shows its state without sweeping.

const RADIUS = 41;
const FULL = 2 * Math.PI * RADIUS;

interface ShutterProps {
  label: string;
  /** The page is working on the last photo (upload or check); the ring stays filled. */
  busy: boolean;
  /** Takes the photo; resolves when the frame is in hand. */
  onShoot: () => Promise<void>;
}

export function Shutter({ label, busy, onShoot }: ShutterProps) {
  const [taking, setTaking] = useState(false);
  const filling = taking || busy;
  return (
    <div className="shutter-wrap">
      <svg className="shutter__ring" viewBox="0 0 88 88" aria-hidden="true" focusable="false">
        <circle className="shutter__track" cx="44" cy="44" r={RADIUS} />
        <circle
          className={`shutter__fill${filling ? " shutter__fill--on" : ""}`}
          cx="44"
          cy="44"
          r={RADIUS}
          strokeDasharray={`${FULL.toFixed(2)} ${FULL.toFixed(2)}`}
          transform="rotate(-90 44 44)"
          style={{ strokeDashoffset: filling ? FULL * 0.08 : FULL }}
        />
      </svg>
      <button
        type="button"
        className="shutter"
        aria-label={label}
        aria-busy={filling}
        disabled={filling}
        onClick={() => {
          setTaking(true);
          void onShoot().finally(() => setTaking(false));
        }}
      />
    </div>
  );
}
