import { useState } from "react";
import { Link } from "react-router-dom";
import type { Dashboard, RingName } from "../api/endpoints";
import { RING_ORDER, RING_RADII, arcDash, itemsWord, ringsLabel } from "../lib/dashboard";

// The health rings (DESIGN.md 6.8): an outer hairline, four tracks with their arcs (Documented,
// Located, Fresh, On time, outer to inner), an inner hairline and the score in the middle. The
// arcs start at 12 o'clock, run clockwise and their length equals each value exactly. A ring
// that does not apply is an empty track. Static in Phase 5; the sweep is Phase 8 motion.

const SIZE = 400;
const CENTRE = SIZE / 2;
const STROKE = 12;

interface HealthRingsProps {
  board: Pick<Dashboard, "score" | "rings" | "item_count">;
  /** Opens the breakdown sheet on a ring (the one pointed at, else the outer one). */
  onOpen: (ring: RingName) => void;
}

export function HealthRings({ board, onOpen }: HealthRingsProps) {
  const [lit, setLit] = useState<RingName | null>(null);
  const empty = board.item_count === 0;

  return (
    <div className="rings">
      <button
        type="button"
        className="rings__button"
        aria-label={`${ringsLabel(board)}. Show what counts`}
        onClick={() => onOpen(lit ?? "documented")}
        onBlur={() => setLit(null)}
      >
        <svg
          className="rings__svg"
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          aria-hidden="true"
          onPointerLeave={() => setLit(null)}
        >
          <defs>
            <filter id="ring-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="5" />
            </filter>
          </defs>
          <circle className="rings__face" cx={CENTRE} cy={CENTRE} r={199} />
          {RING_ORDER.map((ring) => {
            const radius = RING_RADII[ring];
            const value = board.rings[ring].value;
            const dimmed = lit !== null && lit !== ring;
            return (
              <g
                key={ring}
                className={`rings__ring${dimmed ? " rings__ring--dim" : ""}`}
                data-ring={ring}
                onPointerEnter={() => setLit(ring)}
              >
                <circle className="rings__track" cx={CENTRE} cy={CENTRE} r={radius} />
                <circle className="rings__edge" cx={CENTRE} cy={CENTRE} r={radius + STROKE / 2} />
                <circle className="rings__edge" cx={CENTRE} cy={CENTRE} r={radius - STROKE / 2} />
                {value !== null && value > 0 ? (
                  <>
                    <circle
                      className="rings__glow"
                      cx={CENTRE}
                      cy={CENTRE}
                      r={radius}
                      strokeDasharray={arcDash(value, radius)}
                      transform={`rotate(-90 ${CENTRE} ${CENTRE})`}
                      filter="url(#ring-glow)"
                    />
                    <circle
                      className="rings__arc"
                      cx={CENTRE}
                      cy={CENTRE}
                      r={radius}
                      strokeDasharray={arcDash(value, radius)}
                      transform={`rotate(-90 ${CENTRE} ${CENTRE})`}
                    />
                  </>
                ) : null}
              </g>
            );
          })}
          <circle className="rings__inner" cx={CENTRE} cy={CENTRE} r={112} />
        </svg>
      </button>
      <div className="rings__centre">
        <p className="rings__score">{board.score ?? "—"}</p>
        {empty ? (
          <Link className="rings__label rings__add" to="/camera?mode=add">
            Add your first item
          </Link>
        ) : (
          <>
            <p className="rings__label">Inventory health</p>
            <p className="rings__count">• {itemsWord(board.item_count)}</p>
          </>
        )}
      </div>
    </div>
  );
}
