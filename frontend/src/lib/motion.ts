import type { Dashboard, RingName } from "../api/endpoints";
import { RING_ORDER } from "./dashboard";

// Pure helpers and small browser checks for the motion system (DESIGN.md 10, D-128, D-129).
// Motion only shows what the server's numbers already say; it never invents a value.

type Rings = Dashboard["rings"];

/** True when the owner asked the system for less motion: every animation shows its end at once. */
export function reducedMotion(): boolean {
  return (
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** A motion token's length in milliseconds (0 under reduced motion, where tokens are 0 ms). */
export function tokenMs(name: string): number {
  if (typeof window === "undefined") return 0;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const value = parseFloat(raw);
  if (Number.isNaN(value)) return 0;
  return raw.endsWith("ms") ? value : value * 1000;
}

/** The ring arc is a full-circle dash; the offset hides the part past the value (6.8). */
export function arcOffset(value: number | null, radius: number): number {
  const circumference = 2 * Math.PI * radius;
  return circumference * (1 - (value ?? 0) / 100);
}

/** A number on its way from `from` to `to` at progress `t` (0 to 1), easing out. */
export function tween(from: number, to: number, t: number): number {
  if (t >= 1) return to;
  const eased = 1 - Math.pow(1 - Math.max(0, t), 3);
  return Math.round(from + (to - from) * eased);
}

/** The rings whose value went up since the last answer: each pulses once (10.4). */
export function improvedRings(before: Rings | null, after: Rings): RingName[] {
  if (before === null) return [];
  return RING_ORDER.filter((ring) => {
    const was = before[ring].value;
    const now = after[ring].value;
    return was !== null && now !== null && now > was;
  });
}

const MILESTONES = [7, 30, 100];

/** A streak milestone was just reached (D-129): the truck makes one short delivery. */
export function crossedMilestone(before: number | null, after: number): boolean {
  if (before === null) return false;
  return MILESTONES.some((mark) => before < mark && after >= mark);
}

/** "N days in a row" from two days; nothing otherwise, so a break is never pointed out (D-127). */
export function streakWords(streak: Dashboard["streak"]): string | null {
  if (streak === null || streak.days < 2) return null;
  return `${streak.days} days in a row`;
}

/** The truck's lane spans the road, so a percentage of its own width is a place on the road. */
export function truckShift(position: number): string {
  return `translateX(${(position * 100).toFixed(3)}%)`;
}

const ENTRANCE_KEY = "enderchest.entrance";

/** The dashboard entrance plays once per browser tab session (D-129); storage may be blocked. */
export function entranceDue(): boolean {
  try {
    if (window.sessionStorage.getItem(ENTRANCE_KEY) !== null) return false;
    window.sessionStorage.setItem(ENTRANCE_KEY, "seen");
    return true;
  } catch {
    return false;
  }
}
