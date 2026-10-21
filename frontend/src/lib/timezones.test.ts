import { describe, expect, it } from "vitest";
import { currentZoneName, timeZoneOptions } from "./timezones";

describe("currentZoneName", () => {
  it("gives the current name of a zone a browser still reports by its old name", () => {
    expect(currentZoneName("Asia/Calcutta")).toBe("Asia/Kolkata");
    expect(currentZoneName("Europe/Kiev")).toBe("Europe/Kyiv");
  });
  it("leaves every other zone alone", () => {
    expect(currentZoneName("Asia/Kolkata")).toBe("Asia/Kolkata");
    expect(currentZoneName("UTC")).toBe("UTC");
  });
});

describe("timeZoneOptions", () => {
  it("always offers UTC and the zone in use, once each, sorted", () => {
    const options = timeZoneOptions("Asia/Kolkata");
    const values = options.map((option) => option.value);
    expect(values).toContain("UTC");
    expect(values.filter((value) => value === "Asia/Kolkata")).toHaveLength(1);
    expect(values).toEqual([...values].sort((a, b) => a.localeCompare(b)));
  });
  it("never offers an old name next to its current one", () => {
    const values = timeZoneOptions("Asia/Calcutta").map((option) => option.value);
    expect(values).not.toContain("Asia/Calcutta");
    expect(values).toContain("Asia/Kolkata");
  });
  it("writes a readable label", () => {
    const label = timeZoneOptions("America/New_York").find((o) => o.value === "America/New_York");
    expect(label?.label).toBe("America/New York");
  });
});
