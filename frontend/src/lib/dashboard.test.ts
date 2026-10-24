import { describe, expect, it } from "vitest";
import type { RoadEvent } from "../api/endpoints";
import {
  arcDash,
  dayPosition,
  eventLabel,
  eventSummary,
  greetingWord,
  itemsWord,
  ringsLabel,
  roadDays,
  tickLabel,
} from "./dashboard";

const ring = (value: number | null, num = 0, den = 0) => ({ value, num, den });

describe("rings", () => {
  it("draws an arc whose length is exactly the value", () => {
    const [length, circumference] = arcDash(82, 100).split(" ").map(Number);
    expect(length! / circumference!).toBeCloseTo(0.82, 4);
    expect(arcDash(null, 100).startsWith("0.00 ")).toBe(true);
  });

  it("names the rings with their real values", () => {
    const rings = {
      documented: ring(79),
      located: ring(87),
      fresh: ring(96),
      on_time: ring(null),
    };
    expect(ringsLabel({ score: 82, rings })).toBe(
      "Inventory health 82 out of 100. Documented 79, Located 87, Fresh 96, On time not applicable",
    );
    expect(ringsLabel({ score: null, rings })).toMatch(/^Inventory health not scored yet\./);
  });

  it("says the greeting and the count in sentence case", () => {
    expect(greetingWord("evening")).toBe("Good evening,");
    expect(itemsWord(1)).toBe("1 item");
    expect(itemsWord(142)).toBe("142 items");
  });
});

describe("road", () => {
  it("lists every day from today to the end, across a month", () => {
    const days = roadDays("2026-10-16", "2026-10-29");
    expect(days).toHaveLength(14);
    expect(roadDays("2026-10-30", "2026-11-02")).toEqual([
      "2026-10-30",
      "2026-10-31",
      "2026-11-01",
      "2026-11-02",
    ]);
  });

  it("shows the month on the first tick and on the 1st", () => {
    expect(tickLabel("2026-10-16", true)).toBe("16 Oct");
    expect(tickLabel("2026-10-17", false)).toBe("17");
    expect(tickLabel("2026-11-01", false)).toBe("1 Nov");
  });

  it("names a busy day after its task and counts the rest", () => {
    const event: RoadEvent = {
      date: "2026-10-18",
      kind: "mixed",
      label: "Pantry Refill",
      count: 2,
      entries: [
        { kind: "task", label: "Pantry Refill", public_id: null, task_id: 1 },
        { kind: "expiry", label: "Greek Yogurt", public_id: "ENDR-AAAAAAAA", task_id: null },
      ],
    };
    expect(eventLabel(event)).toBe("Pantry Refill +1");
    expect(eventSummary(event, "18 Oct")).toBe(
      "18 Oct: Pantry Refill is due, Greek Yogurt expires",
    );
    expect(eventLabel({ ...event, count: 1 })).toBe("Pantry Refill");
  });

  it("places each day in the middle of its column", () => {
    expect(dayPosition(0, 14)).toBeCloseTo(0.5 / 14);
    expect(dayPosition(13, 14)).toBeCloseTo(13.5 / 14);
  });
});
