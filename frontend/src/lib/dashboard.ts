import type { Dashboard, RingName, RoadEvent } from "../api/endpoints";
import { addDays } from "./format";

// Pure helpers for the dashboard (PAGES.md P-12, DESIGN.md 6.7 to 6.11). Every number comes from
// the server; these only turn it into geometry and words.

export const RING_ORDER: RingName[] = ["documented", "located", "fresh", "on_time"];

export const RING_WORDS: Record<RingName, { name: string; rule: string }> = {
  documented: {
    name: "Documented",
    rule: "Active items with a photo and a printed label (or no label needed).",
  },
  located: { name: "Located", rule: "Active items with a place." },
  fresh: {
    name: "Fresh",
    rule: "Active items not past their date. No expiry counts; a date not set does not.",
  },
  on_time: { name: "On time", rule: "Switched-on tasks that are not overdue." },
};

/** Radii of the four rings, outer to inner (DESIGN.md 6.8, at the reference's 400 px). */
export const RING_RADII: Record<RingName, number> = {
  documented: 180,
  located: 164,
  fresh: 148,
  on_time: 132,
};

/** The arc's dash pattern: its length equals the value exactly (DESIGN.md 6.8). */
export function arcDash(value: number | null, radius: number): string {
  const circumference = 2 * Math.PI * radius;
  const length = ((value ?? 0) / 100) * circumference;
  return `${length.toFixed(2)} ${circumference.toFixed(2)}`;
}

/** "Good evening," from the server's greeting part. */
export function greetingWord(part: Dashboard["greeting"]["part"]): string {
  return `Good ${part},`;
}

/** "1 item", "142 items" (sentence case, D-033). */
export function itemsWord(count: number): string {
  return count === 1 ? "1 item" : `${count} items`;
}

/** The rings' accessible name with the real values (DESIGN.md 6.8). */
export function ringsLabel(board: Pick<Dashboard, "score" | "rings">): string {
  const parts = RING_ORDER.map((ring) => {
    const value = board.rings[ring].value;
    return `${RING_WORDS[ring].name} ${value === null ? "not applicable" : value}`;
  });
  const score = board.score === null ? "not scored yet" : `${board.score} out of 100`;
  return `Inventory health ${score}. ${parts.join(", ")}`;
}

/** Every day of the road from `start` to `end`, both included. */
export function roadDays(start: string, end: string): string[] {
  const days = [start];
  while (days[days.length - 1]! < end) days.push(addDays(days[days.length - 1]!, 1));
  return days;
}

const MONTH = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", month: "short" });

/** The tick under a day: "16 Oct" on the first day and on the 1st of a month, else "17". */
export function tickLabel(day: string, first: boolean): string {
  const moment = new Date(`${day}T00:00:00Z`);
  const number = String(moment.getUTCDate());
  return first || moment.getUTCDate() === 1 ? `${number} ${MONTH.format(moment)}` : number;
}

/**
 * Whether a tick shows its date. Up to 14 days every tick does; a longer road (Tasks, 30 days)
 * names every other day, the 1st of a month and the truck's day, so the numbers do not collide.
 */
export function tickShown(index: number, day: string, days: number, truckDate: string): boolean {
  return days <= 14 || index % 2 === 0 || day.endsWith("-01") || day === truckDate;
}

/** The label under the truck's day: "Pantry Refill", or "Pantry Refill +1" for a busy day. */
export function eventLabel(event: RoadEvent): string {
  return event.count > 1 ? `${event.label} +${event.count - 1}` : event.label;
}

/** What one entry of a day is, in words: "Pantry Refill (task)", "Oat Milk expires". */
export function entryWords(entry: RoadEvent["entries"][number]): string {
  return entry.kind === "task" ? `${entry.label} is due` : `${entry.label} expires`;
}

/** A day's accessible description: "18 Oct: Pantry Refill is due, Greek Yogurt expires". */
export function eventSummary(event: RoadEvent, dayText: string): string {
  return `${dayText}: ${event.entries.map(entryWords).join(", ")}`;
}

/** Where a day sits along the road, as a share of its width (the middle of its column). */
export function dayPosition(index: number, days: number): number {
  return (index + 0.5) / days;
}
