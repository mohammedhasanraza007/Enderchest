import { describe, expect, it } from "vitest";
import {
  arcOffset,
  crossedMilestone,
  improvedRings,
  streakWords,
  tween,
  truckShift,
} from "./motion";

const ring = (value: number | null) => ({ value, num: 0, den: 0 });
const rings = (d: number | null, l: number | null, f: number | null, o: number | null) => ({
  documented: ring(d),
  located: ring(l),
  fresh: ring(f),
  on_time: ring(o),
});

describe("ring geometry", () => {
  it("hides the part of a full-circle dash that is past the value", () => {
    const circumference = 2 * Math.PI * 100;
    expect(arcOffset(82, 100)).toBeCloseTo(circumference * 0.18, 3);
    expect(arcOffset(100, 100)).toBeCloseTo(0, 6);
    expect(arcOffset(null, 100)).toBeCloseTo(circumference, 6);
  });
});

describe("count-up", () => {
  it("starts at the old value, ends exactly at the new one and eases out", () => {
    expect(tween(82, 86, 0)).toBe(82);
    expect(tween(82, 86, 1)).toBe(86);
    expect(tween(0, 100, 0.5)).toBeGreaterThan(50);
    expect(tween(141, 142, 0.999)).toBe(142);
  });
});

describe("win moments (D-129)", () => {
  it("names only the rings whose value went up", () => {
    expect(improvedRings(rings(80, 90, 70, 50), rings(80, 91, 70, 75))).toEqual([
      "located",
      "on_time",
    ]);
    expect(improvedRings(rings(80, 90, 70, null), rings(79, 90, 70, 100))).toEqual([]);
    expect(improvedRings(null, rings(80, 90, 70, 50))).toEqual([]);
  });

  it("calls a streak milestone only when 7, 30 or 100 is reached", () => {
    expect(crossedMilestone(6, 7)).toBe(true);
    expect(crossedMilestone(29, 30)).toBe(true);
    expect(crossedMilestone(7, 7)).toBe(false);
    expect(crossedMilestone(null, 7)).toBe(false);
    expect(crossedMilestone(8, 9)).toBe(false);
  });
});

describe("streak words (D-127)", () => {
  it("speaks only from two days and never about a broken streak", () => {
    expect(streakWords(null)).toBeNull();
    expect(streakWords({ days: 0 })).toBeNull();
    expect(streakWords({ days: 1 })).toBeNull();
    expect(streakWords({ days: 2 })).toBe("2 days in a row");
  });
});

describe("truck lane", () => {
  it("moves the full-width lane by the day's position on the road", () => {
    expect(truckShift(0.5 / 14)).toBe("translateX(3.571%)");
    expect(truckShift(13.5 / 14)).toBe("translateX(96.429%)");
  });
});
