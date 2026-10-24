// Display formats from docs/PAGES.md 2 and docs/DESIGN.md 12: "16 Oct", "16 Oct 2026", 12-hour
// times, sizes in KB or MB. Dates are shown in the owner's own time zone.

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function pieces(moment: Date, timeZone: string) {
  const date = new Intl.DateTimeFormat("en-GB", { timeZone, day: "numeric", month: "short" });
  const year = new Intl.DateTimeFormat("en-GB", { timeZone, year: "numeric" });
  const time = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return {
    date: date.format(moment),
    year: year.format(moment),
    // Newer ICU puts a narrow no-break space before AM or PM; write it as a plain space.
    time: time.format(moment).replace(/\s/g, " ").replace("AM", "am").replace("PM", "pm"),
  };
}

/** "21 Oct, 10:10 pm", or "21 Oct 2025, 10:10 pm" when the year is not the current one. */
export function formatMoment(iso: string, timeZone: string, now: Date = new Date()): string {
  const moment = new Date(iso);
  const shown = pieces(moment, timeZone);
  const sameYear = shown.year === pieces(now, timeZone).year;
  return `${shown.date}${sameYear ? "" : ` ${shown.year}`}, ${shown.time}`;
}

export type DayPart = "morning" | "afternoon" | "evening" | "night";

/** The greeting word follows the local hour (DESIGN.md 6.7). */
export function dayPart(hour: number): DayPart {
  if (hour >= 5 && hour < 12) return "morning";
  if (hour >= 12 && hour < 17) return "afternoon";
  if (hour >= 17 && hour < 21) return "evening";
  return "night";
}

/** The current hour (0 to 23) in a time zone. */
export function localHour(timeZone: string, now: Date = new Date()): number {
  const hour = new Intl.DateTimeFormat("en-GB", { timeZone, hour: "numeric", hour12: false })
    .formatToParts(now)
    .find((part) => part.type === "hour")?.value;
  return Number(hour) % 24;
}

/**
 * A calendar date (an expiry, YYYY-MM-DD) as "16 Oct", or "14 Mar 2027" in another year. It has
 * no time zone, so it is formatted as the date it names, never shifted.
 */
export function formatDay(day: string, now: Date = new Date()): string {
  const moment = new Date(`${day}T00:00:00Z`);
  const shown = new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    day: "numeric",
    month: "short",
  });
  const sameYear = moment.getUTCFullYear() === now.getFullYear();
  return sameYear ? shown.format(moment) : `${shown.format(moment)} ${moment.getUTCFullYear()}`;
}

/** Today's date (YYYY-MM-DD) in a time zone, for a form's default due date. */
export function localToday(timeZone: string, now: Date = new Date()): string {
  // en-CA writes dates as YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

/** A calendar date moved by whole days (dates only, no time zone). */
export function addDays(day: string, days: number): string {
  const moment = new Date(`${day}T00:00:00Z`);
  moment.setUTCDate(moment.getUTCDate() + days);
  return moment.toISOString().slice(0, 10);
}
