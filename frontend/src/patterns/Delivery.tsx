import { useEffect, useRef, useState } from "react";
import { DELIVERY_EVENT, reducedMotion } from "../lib/motion";
import { Truck } from "./Road";

// The save delivery (DESIGN.md 10.3, D-130): after a new item is saved, a box drops onto the
// truck at the bottom of the window and the truck drives up to the brand mark in the nav, where
// it fades. Transform and opacity only (Web Animations API), under 1.2 s, pointer-events none,
// any key, click, wheel or touch finishes it at once. Nothing plays under reduced motion.

const DELIVERY_MS = 1100;
const TRUCK = { width: 75, height: 42 };
const INPUTS = ["keydown", "pointerdown", "wheel", "touchstart"] as const;

export function DeliveryLayer() {
  const [trip, setTrip] = useState(0);
  const vehicle = useRef<HTMLDivElement>(null);
  const parcel = useRef<HTMLDivElement>(null);

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
    const brand = document.querySelector(".nav__brand")?.getBoundingClientRect();
    if (trip === 0 || !car || !box) return;
    if (!brand) {
      setTrip(0);
      return;
    }
    // Start on the road's own truck when the dashboard shows one (owner's storyboard video,
    // docs/design/delivery-storyboard.jpg); else at the bottom centre of the window.
    const parked = document.querySelector(".road__truck")?.getBoundingClientRect();
    const start = parked
      ? { x: parked.left, y: parked.top }
      : { x: window.innerWidth / 2 - TRUCK.width / 2, y: window.innerHeight - 120 };
    const end = {
      x: brand.left + brand.width / 2 - TRUCK.width / 2,
      y: brand.top + brand.height / 2 - TRUCK.height / 2,
    };
    // The truck turns to face the brand mark and tilts along its path, as in the storyboard.
    const left = end.x < start.x;
    const angle = (Math.atan2(end.y - start.y, Math.abs(end.x - start.x)) * 180) / Math.PI;
    const face = left ? "scaleX(-1)" : "";
    const tilt = `rotate(${(left ? -angle : angle).toFixed(1)}deg)`;
    const mid = { x: start.x + (end.x - start.x) * 0.45, y: start.y + (end.y - start.y) * 0.6 };
    const at = (p: { x: number; y: number }) => `translate(${p.x}px, ${p.y}px)`;
    const drive = car.animate(
      [
        { transform: `${at(start)}`, opacity: 0 },
        { transform: `${at(start)}`, opacity: 1, offset: 0.1 },
        { transform: `${at(start)}`, opacity: 1, offset: 0.36 },
        { transform: `${at(mid)} ${face} ${tilt} scale(0.8)`, opacity: 1, offset: 0.66 },
        { transform: `${at(end)} ${face} scale(0.45)`, opacity: 1, offset: 0.9 },
        { transform: `${at(end)} ${face} scale(0.4)`, opacity: 0 },
      ],
      { duration: DELIVERY_MS, easing: "cubic-bezier(0.65, 0, 0.35, 1)", fill: "both" },
    );
    const drop = box.animate(
      [
        { transform: "translateY(-56px)", opacity: 0 },
        { transform: "translateY(-56px)", opacity: 1, offset: 0.12 },
        { transform: "translateY(0)", opacity: 1, offset: 0.34 },
        { transform: "translateY(0)", opacity: 1 },
      ],
      { duration: DELIVERY_MS, easing: "cubic-bezier(0.22, 1, 0.36, 1)", fill: "both" },
    );
    const finish = () => {
      drive.finish();
      drop.finish();
    };
    INPUTS.forEach((name) => window.addEventListener(name, finish, { passive: true }));
    document.body.classList.add("delivering");
    drive.onfinish = () => setTrip(0);
    return () => {
      INPUTS.forEach((name) => window.removeEventListener(name, finish));
      document.body.classList.remove("delivering");
      drive.cancel();
      drop.cancel();
    };
  }, [trip]);

  if (trip === 0) return null;
  return (
    <div className="delivery" aria-hidden="true">
      <div ref={vehicle} className="delivery__vehicle">
        <div ref={parcel} className="delivery__parcel" />
        <Truck />
      </div>
    </div>
  );
}
