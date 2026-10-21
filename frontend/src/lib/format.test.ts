import { describe, expect, it } from "vitest";
import { dayPart, formatBytes, formatMoment, localHour } from "./format";

describe("formatBytes", () => {
  it("rounds to KB below a megabyte and never says 0 KB", () => {
    expect(formatBytes(45056)).toBe("44 KB");
    expect(formatBytes(1)).toBe("1 KB");
  });
  it("uses one decimal in MB", () => {
    expect(formatBytes(41996288)).toBe("40.1 MB");
  });
});

describe("formatMoment", () => {
  const now = new Date("2026-10-21T12:00:00Z");
  it("shows day, month and a 12-hour time in the owner's time zone", () => {
    // 16:36 UTC is 22:06 in Kolkata
    expect(formatMoment("2026-10-21T16:36:00Z", "Asia/Kolkata", now)).toBe("21 Oct, 10:06 pm");
  });
  it("adds the year when it is not the current one", () => {
    expect(formatMoment("2025-03-14T09:05:00Z", "UTC", now)).toBe("14 Mar 2025, 9:05 am");
  });
  it("uses the owner's zone to decide the date, not UTC", () => {
    expect(formatMoment("2026-10-21T20:00:00Z", "Asia/Kolkata", now)).toBe("22 Oct, 1:30 am");
  });
});

describe("dayPart", () => {
  it("follows the local hour", () => {
    expect(dayPart(5)).toBe("morning");
    expect(dayPart(11)).toBe("morning");
    expect(dayPart(12)).toBe("afternoon");
    expect(dayPart(17)).toBe("evening");
    expect(dayPart(21)).toBe("night");
    expect(dayPart(4)).toBe("night");
  });
});

describe("localHour", () => {
  it("reads the hour in the given zone", () => {
    expect(localHour("Asia/Kolkata", new Date("2026-10-21T16:36:00Z"))).toBe(22);
    expect(localHour("UTC", new Date("2026-10-21T00:10:00Z"))).toBe(0);
  });
});
