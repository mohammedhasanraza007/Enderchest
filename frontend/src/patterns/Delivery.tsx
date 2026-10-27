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
    const from = `${window.innerWidth / 2 - TRUCK.width / 2}px, ${window.innerHeight - 120}px`;
    const to = `${brand.left + brand.width / 2 - TRUCK.width / 2}px, ${brand.top + brand.height / 2 - TRUCK.height / 2}px`;
    const drive = car.animate(
      [
        { transform: `translate(${from})`, opacity: 0 },
        { transform: `translate(${from})`, opacity: 1, offset: 0.12 },
        { transform: `translate(${from})`, opacity: 1, offset: 0.38 },
        { transform: `translate(${to}) scale(0.45)`, opacity: 1, offset: 0.9 },
        { transform: `translate(${to}) scale(0.4)`, opacity: 0 },
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
    drive.onfinish = () => setTrip(0);
    return () => {
      INPUTS.forEach((name) => window.removeEventListener(name, finish));
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
