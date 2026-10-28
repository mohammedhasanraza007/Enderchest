import { useEffect, useRef, useState } from "react";
import { DELIVERY_EVENT, reducedMotion } from "../lib/motion";
import { Truck } from "./Road";

// The save delivery (DESIGN.md 10.3, D-130, D-138): after a new item is saved, a box drops from
// under the nav onto the truck, the truck turns on the spot, climbs up a dashed trail (a small
// star marks the lift-off) to the brand mark in the nav and shrinks into it. The beats follow the
// owner's delivery video, compressed to under 1.2 s. Transform, opacity and stroke-dashoffset
// only (Web Animations API), pointer-events none, any key, click, wheel or touch finishes it at
// once. Nothing plays under reduced motion.

const DELIVERY_MS = 1150;
const TRUCK = { width: 75, height: 42 };
const INPUTS = ["keydown", "pointerdown", "wheel", "touchstart"] as const;
// Beats as fractions of DELIVERY_MS: the box lands, the truck turns, lifts off, arrives.
const LANDED = 0.3;
const TURNED = 0.46;
const ARRIVED = 0.84;

type Point = { x: number; y: number };

export function DeliveryLayer() {
  const [trip, setTrip] = useState(0);
  const vehicle = useRef<HTMLDivElement>(null);
  const parcel = useRef<HTMLDivElement>(null);
  const trail = useRef<SVGLineElement>(null);
  const star = useRef<SVGPathElement>(null);

  useEffect(() => {
    const start = () => {
      if (!reducedMotion()) setTrip((count) => count + 1);
    };
    window.addEventListener(DELIVERY_EVENT, start);
    return () => window.removeEventListener(DELIVERY_EVENT, start);
  }, []);

  useEffect(() => {
    const car = vehicle.current;
    const box = parcel.current;
    const line = trail.current;
    const mark = star.current;
    const brand = document.querySelector(".nav__brand")?.getBoundingClientRect();
    if (trip === 0 || !car || !box || !line || !mark) return;
    if (!brand) {
      setTrip(0);
      return;
    }
    // Start on the road's own truck when the dashboard shows one (owner's storyboard and video);
    // else at the bottom centre of the window. The flying copy is a .road__truck too: skip it.
    const parked = [...document.querySelectorAll(".road__truck")]
      .find((truck) => !truck.closest(".delivery"))
      ?.getBoundingClientRect();
    const start: Point = parked?.width
      ? { x: parked.left, y: parked.top }
      : { x: window.innerWidth / 2 - TRUCK.width / 2, y: window.innerHeight - 120 };
    const end: Point = {
      x: brand.left + brand.width / 2 - TRUCK.width / 2,
      y: brand.top + brand.height / 2 - TRUCK.height / 2,
    };
    // The box falls from just under the nav, as in the video, not from a few pixels above.
    const fall = Math.max(56, start.y - brand.bottom);
    const left = end.x < start.x;
    const angle = (Math.atan2(end.y - start.y, Math.abs(end.x - start.x)) * 180) / Math.PI;
    const face = left ? "scaleX(-1)" : "";
    const tilt = `rotate(${(left ? -angle : angle).toFixed(1)}deg)`;
    const mid = { x: start.x + (end.x - start.x) * 0.45, y: start.y + (end.y - start.y) * 0.6 };
    const at = (p: Point) => `translate(${p.x}px, ${p.y}px)`;

    // The trail runs between the truck's centres at lift-off and arrival.
    const centre = (p: Point) => ({ x: p.x + TRUCK.width / 2, y: p.y + TRUCK.height / 2 });
    const from = centre(start);
    const to = centre(end);
    line.setAttribute("x1", String(from.x));
    line.setAttribute("y1", String(from.y));
    line.setAttribute("x2", String(to.x));
    line.setAttribute("y2", String(to.y));
    mark.setAttribute("transform", `translate(${from.x} ${start.y + TRUCK.height})`);

    // Easing sits on each keyframe (the segment after it), so the beats land on their offsets; an
    // easing on the whole animation would warp every offset.
    const timing = { duration: DELIVERY_MS, fill: "both" as const };
    const smooth = "cubic-bezier(0.65, 0, 0.35, 1)";
    // The turn is a yaw: the truck narrows to an edge and opens up facing the other way.
    const drive = car.animate(
      [
        { transform: at(start), opacity: 0 },
        { transform: at(start), opacity: 1, offset: 0.06 },
        { transform: at(start), opacity: 1, offset: LANDED, easing: smooth },
        {
          transform: `${at(start)} scaleX(0.15)`,
          opacity: 1,
          offset: (LANDED + TURNED) / 2,
          easing: smooth,
        },
        { transform: `${at(start)} ${face}`, opacity: 1, offset: TURNED, easing: "ease-in" },
        {
          transform: `${at(mid)} ${face} ${tilt} scale(0.8)`,
          opacity: 1,
          offset: 0.66,
          easing: "ease-out",
        },
        { transform: `${at(end)} ${face} scale(0.5)`, opacity: 1, offset: ARRIVED, easing: smooth },
        { transform: `${at(end)} ${face} scale(0.05)`, opacity: 0 },
      ],
      timing,
    );
    const drop = box.animate(
      [
        { transform: `translateY(-${fall}px)`, opacity: 0 },
        {
          transform: `translateY(-${fall}px)`,
          opacity: 1,
          offset: 0.04,
          easing: "cubic-bezier(0.22, 1, 0.36, 1)",
        },
        { transform: "translateY(0)", opacity: 1, offset: LANDED },
        { transform: "translateY(0)", opacity: 1 },
      ],
      timing,
    );
    // The dashes appear behind the climb and creep toward the brand mark.
    const draw = line.animate(
      [
        { opacity: 0, strokeDashoffset: 0, offset: 0 },
        { opacity: 0, strokeDashoffset: 0, offset: TURNED },
        { opacity: 0.7, strokeDashoffset: -20, offset: ARRIVED },
        { opacity: 0, strokeDashoffset: -30 },
      ],
      timing,
    );
    const glint = mark.animate(
      [
        { opacity: 0, offset: 0 },
        { opacity: 0, offset: TURNED - 0.04 },
        { opacity: 0.8, offset: TURNED + 0.06 },
        { opacity: 0 },
      ],
      timing,
    );
    const all = [drive, drop, draw, glint];
    const finish = () => all.forEach((one) => one.finish());
    INPUTS.forEach((name) => window.addEventListener(name, finish, { passive: true }));
    document.body.classList.add("delivering");
    drive.onfinish = () => setTrip(0);
    return () => {
      INPUTS.forEach((name) => window.removeEventListener(name, finish));
      document.body.classList.remove("delivering");
      all.forEach((one) => one.cancel());
    };
  }, [trip]);

  if (trip === 0) return null;
  return (
    <div className="delivery" aria-hidden="true">
      <svg className="delivery__sky" width="100%" height="100%">
        <line ref={trail} className="delivery__trail" />
        <path ref={star} className="delivery__star" d="M0-9 2 -2 9 0 2 2 0 9-2 2-9 0-2-2z" />
      </svg>
      <div ref={vehicle} className="delivery__vehicle">
        <div ref={parcel} className="delivery__parcel" />
        <Truck />
      </div>
    </div>
  );
}
