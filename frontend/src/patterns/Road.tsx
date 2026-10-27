import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { Road as RoadData, RoadEvent } from "../api/endpoints";
import {
  dayPosition,
  entryWords,
  eventLabel,
  eventSummary,
  roadDays,
  tickLabel,
  tickShown,
} from "../lib/dashboard";
import { formatDay } from "../lib/format";
import { formatRupees } from "../lib/money";
import { tokenMs, truckShift } from "../lib/motion";
import { Dialog } from "../primitives/Overlay";

// The road (DESIGN.md 6.11): a full-bleed bar with a dashed centre line, a tick per day from
// today, a notch per day with something on it, the truck parked at the next job (D-110) and, on
// the dashboard, the savings pill on today when a saving was confirmed today (D-116).
// One component for the dashboard (14 days) and the Tasks page (30 days, D-103). Each day with
// events is a button: hover or focus shows what is on it, a click opens the day. The events are
// an ordered list, so a screen reader hears the road as a list (DESIGN.md 14).

interface RoadProps {
  road: RoadData;
  title: string;
  /** What the empty road says, for example "No tasks or expiries in the next 14 days." */
  emptyText: string;
  /** The dashboard's confirmed savings; the pill shows only on the day of the latest one, which
   * must be today (D-116: never on a future date). */
  savings?: { month_paise: number; pill_date: string | null } | null;
  /** Changes when the truck should make one short delivery (a streak milestone, D-129). */
  delivery?: number;
}

export function Road({ road, title, emptyText, savings, delivery = 0 }: RoadProps) {
  const [open, setOpen] = useState<RoadEvent | null>(null);
  const titleId = useId();
  const days = roadDays(road.start, road.end);
  const at = (day: string) => `${(dayPosition(days.indexOf(day), days.length) * 100).toFixed(3)}%`;
  const truckEvent = road.events.find((event) => event.date === road.truck_date);
  // Parked on the first two days, the truck stands under the title: give the title headroom.
  const truckAtStart = days.indexOf(road.truck_date) <= 1;
  const pill = savings && savings.pill_date === road.start ? savings.month_paise : null;
  const moving = useMoving(road.truck_date, delivery);

  return (
    <section
      className={`road${truckAtStart ? " road--truck-start" : ""}${pill !== null ? " road--pill" : ""}`}
      aria-labelledby={titleId}
    >
      <h2 id={titleId} className="road__title">
        {title}
      </h2>
      <div className="road__bar" aria-hidden="true" />
      <div className="road__track">
        <div
          className={`road__lane${moving ? " road__lane--moving" : ""}`}
          style={{ transform: truckShift(dayPosition(days.indexOf(road.truck_date), days.length)) }}
          aria-hidden="true"
        >
          <div
            key={delivery}
            className={`road__drive${delivery > 0 ? " road__drive--deliver" : ""}`}
          >
            <Truck />
          </div>
        </div>
        {pill !== null ? (
          <Link
            to="/savings"
            className={`road__pill${truckAtStart ? " road__pill--lifted" : ""}${
              road.truck_date === road.start ? " road__pill--on-truck" : ""
            }`}
            style={{ left: at(road.start) }}
          >
            {formatRupees(pill)} saved
          </Link>
        ) : null}
        {road.events.length === 0 ? (
          <p className="road__empty">{emptyText}</p>
        ) : (
          <ol className="road__events">
            {road.events.map((event) => {
              const summary = eventSummary(event, formatDay(event.date));
              return (
                <li key={event.date} className="road__event" style={{ left: at(event.date) }}>
                  <button
                    type="button"
                    className="road__notch"
                    aria-label={`${summary}. Open the day`}
                    onClick={() => setOpen(event)}
                  >
                    <span className="road__tip" aria-hidden="true">
                      {summary}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        )}
        <ol className="road__ticks" aria-hidden="true">
          {days.map((day, index) => (
            <li
              key={day}
              className={`road__tick${index === 0 ? " road__tick--today" : ""}`}
              style={{ left: at(day) }}
            >
              <span className="road__mark" />
              <span className="road__day">
                {tickShown(index, day, days.length, road.truck_date)
                  ? tickLabel(day, index === 0)
                  : ""}
              </span>
              {day === road.truck_date && truckEvent ? (
                <span className="road__label">{eventLabel(truckEvent)}</span>
              ) : null}
            </li>
          ))}
        </ol>
      </div>
      <Dialog
        open={open !== null}
        onClose={() => setOpen(null)}
        title={open ? formatDay(open.date) : ""}
      >
        <ul className="road__day-list">
          {open?.entries.map((entry) => (
            <li key={`${entry.kind}-${entry.task_id ?? entry.public_id}`}>
              <Link
                to={entry.kind === "task" ? "/tasks" : `/items/${entry.public_id}`}
                onClick={() => setOpen(null)}
              >
                {entryWords(entry)}
              </Link>
            </li>
          ))}
        </ul>
      </Dialog>
    </section>
  );
}

/** True for one scene's length after the truck's day changes or a delivery starts: the wheels
 * turn only while it moves (DESIGN.md 10.3). */
function useMoving(truckDate: string, delivery: number): boolean {
  const [moving, setMoving] = useState(false);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const ms = tokenMs("--dur-scene");
    if (ms === 0) return;
    setMoving(true);
    const timer = window.setTimeout(() => setMoving(false), ms);
    return () => window.clearTimeout(timer);
  }, [truckDate, delivery]);
  return moving;
}

/** A flat delivery truck (DESIGN.md 6.11): clay box, darker cab, cream window, dark wheels. */
export function Truck() {
  return (
    <svg
      className="road__truck"
      viewBox="0 0 75 42"
      width="75"
      height="42"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="1" y="4" width="48" height="28" rx="3" fill="var(--truck-body)" />
      <path
        d="M51 12h11.5a3 3 0 0 1 2.6 1.5l6.4 10.6a3 3 0 0 1 .5 1.6V32H51z"
        fill="var(--truck-cab)"
      />
      <path d="M55 15h7l4.6 7.6H55z" fill="var(--truck-window)" />
      <rect x="1" y="30" width="72" height="3" rx="1.5" fill="var(--truck-cab)" />
      {[15, 61].map((x) => (
        <g key={x} className="road__wheel">
          <circle cx={x} cy="35" r="6" fill="var(--truck-ink)" />
          <circle cx={x} cy="35" r="2.2" fill="var(--truck-body)" />
          <rect x={x - 0.6} y="30.5" width="1.2" height="2.6" rx="0.6" fill="var(--truck-body)" />
        </g>
      ))}
    </svg>
  );
}
